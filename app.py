import uuid
from typing import List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from DocuMind import ingest_documents, ask_documind

ALLOWED_EXTENSIONS = (".pdf", ".docx", ".txt")
class AskRequest(BaseModel):
    session_id: str
    question: str

app = FastAPI(title="DocuMind Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/new-session")
def new_session():
    return {"user_id": str(uuid.uuid4())}

@app.post("/upload")
async def upload(
    user_id: str = Form(...),
    files: List[UploadFile] = File(...)
):
    invalid_files = [
        f.filename for f in files
        if not f.filename.lower().endswith(ALLOWED_EXTENSIONS)
    ]
    if invalid_files:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type(s): {invalid_files}. "
                   f"Only {ALLOWED_EXTENSIONS} are allowed."
        )

    n_chunks = ingest_documents(files, user_id)
    return {
        "status": "success",
        "files_received": [f.filename for f in files],
        "chunks_stored": n_chunks
    }

@app.post("/ask")
def ask(request: AskRequest):
    try:
        answer = ask_documind(
            request.question,
            request.session_id
        )

        return {
            "answer": answer
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )