import uuid
from dotenv import load_dotenv
from langchain_mistralai import ChatMistralAI, MistralAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

import os
import tempfile
from pinecone import Pinecone, ServerlessSpec
from langchain_pinecone import PineconeVectorStore

load_dotenv()

llm_model=ChatMistralAI(model="mistral-small-2603")
embedding_model=MistralAIEmbeddings()

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "documind-index")

# mistral-embed produces 1024-dimensional vectors -> index must match this dimension
EMBED_DIM = 1024

existing_indexes = [index.name for index in pc.list_indexes()]
if INDEX_NAME not in existing_indexes:
    pc.create_index(
        name=INDEX_NAME,
        dimension=EMBED_DIM,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1")
    )

pinecone_index = pc.Index(INDEX_NAME)

def doc_loader(filename):
    if filename.endswith(".pdf"):
        loader=PyPDFLoader(filename)
    elif filename.endswith(".docx"):
        loader=Docx2txtLoader(filename)
    elif filename.endswith(".txt"):
        loader=TextLoader(filename)
    else:
        raise ValueError("Unsupported file type")
    return loader.load()

splitter=RecursiveCharacterTextSplitter(
    chunk_size = 1000,
    chunk_overlap = 200
)

def ingest_documents(files, user_id=None):
    if not user_id:
        raise ValueError("Session ID is required.")

    namespace = f"session_{user_id}"

    all_docs = []
    temp_paths_to_cleanup = []

    for file in files:
        if isinstance(file, str):
            path = file
        else:
            suffix = os.path.splitext(file.filename)[1]

            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=suffix
            ) as tmp:
                tmp.write(file.file.read())
                path = tmp.name

            temp_paths_to_cleanup.append(path)

        all_docs.extend(doc_loader(path))

    for path in temp_paths_to_cleanup:
        try:
            os.remove(path)
        except OSError:
            pass

    chunks = splitter.split_documents(all_docs)

    user_vectorstore = PineconeVectorStore(
        index=pinecone_index,
        embedding=embedding_model,
        namespace=namespace
    )

    user_vectorstore.add_documents(chunks)

    return len(chunks)

prompt = ChatPromptTemplate.from_messages(
    [
        (
        "system",
        """You are DocuMind, an intelligent AI document assistant.
        You operate in two modes:
        1. DOCUMENT MODE
        When document context is provided, use it as the primary source for questions related to the uploaded documents.

        2. GENERAL CHAT MODE
        When no document context is available, answer the user's questions normally using your general knowledge.

        Follow these rules:

        1. DOCUMENT-BASED QUESTIONS
        - Use the provided document context as the primary source.
        - Do not invent information that is not supported by the context.
        - If the document context does not contain enough information, clearly say that the information is not available in the uploaded documents.
        - When source metadata is available, mention the document name and page number.
        - Never fabricate a document name, page number, or source.

        2. GENERAL QUESTIONS
        - If no document context is provided, answer normally using your general knowledge.
        - Do not claim that information came from a document.
        - You can have a normal conversation with the user even when no documents have been uploaded.

        3. CONVERSATION
        - Remember the previous conversation provided in the question.
        - Maintain context naturally between messages.
        - Answer the current question directly.

        4. IDENTITY
        - Your name is DocuMind.
        - If the user asks who you are, identify yourself as DocuMind, an AI document assistant.

        5. ANSWER QUALITY
        - Give accurate, concise and useful answers.
        - Use clear language.
        - Use bullets or headings when useful.
        - Do not unnecessarily repeat the context.
        Now answer the user's question according to these rules."""),
        (
        "human",
        """Context: {context}
        Question: {question}"""
        )
    ]
)

messages={}
parser=StrOutputParser()

def ask_documind(query, user_id="default"):

    if not user_id:
        raise ValueError("Session ID is required.")

    if user_id not in messages:
        messages[user_id] = []

    user_messages = messages[user_id]

    namespace = f"session_{user_id}"

    user_vectorstore = PineconeVectorStore(
        index=pinecone_index,
        embedding=embedding_model,
        namespace=namespace
    )

    retriever = user_vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": 4,
            "fetch_k": 10,
            "lambda_mult": 0.5
        }
    )

    try:
        stats = pinecone_index.describe_index_stats(
            filter=None
        )

        namespace_stats = stats.get("namespaces", {}).get(namespace, {})
        has_documents = namespace_stats.get("vector_count", 0) > 0

    except Exception:
        has_documents = False

    if has_documents:

        retrieved_docs = retriever.invoke(query)

        context = "\n\n".join(
            [
                f"Source: {doc.metadata.get('source', 'Unknown')}\n"
                f"Page: {doc.metadata.get('page', 'Unknown')}\n"
                f"Content: {doc.page_content}"
                for doc in retrieved_docs
            ]
        )

    else:

        context = """No documents have been uploaded in this session.
        Answer the user's question using your general knowledge.
        Do not claim that the answer came from a document."""

    conversation = "\n".join(
        [
            f"{message['role']}: {message['content']}"
            for message in user_messages
        ]
    )

    seq = prompt | llm_model | parser

    response = seq.invoke(
        {
            "context": context,
            "question": f"""
Previous conversation:
{conversation}

Current question:
{query}
"""
        }
    )

    user_messages.append(
        {
            "role": "human",
            "content": query
        }
    )

    user_messages.append(
        {
            "role": "ai",
            "content": response
        }
    )

    return response