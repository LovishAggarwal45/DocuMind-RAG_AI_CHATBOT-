import requests
import streamlit as st

API_BASE_URL = "http://127.0.0.1:8000"
ALLOWED_TYPES = ["pdf", "docx", "txt"]

st.set_page_config(
    page_title="DocuMind | AI Document Assistant",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

#MainMenu, footer, header {
    visibility: hidden;
}

.block-container {
    max-width: 1100px;
    padding-top: 1.5rem;
}


/* ---------- Top Bar ---------- */

.topbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 2.2rem;
}

.brand {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 4.2rem;
    font-weight: 700;
    letter-spacing: 0.18em;
    line-height: 1;
    color: #111827;
}

.creator {
    font-size: 0.9rem;
    font-weight: 500;
    color: #64748b;
    padding-top: 1rem;
}


/* ---------- Subtitle ---------- */

.subtitle {
    color: #64748b;
    font-size: 1rem;
    margin-top: -1.7rem;
    margin-bottom: 2.4rem;
}


/* ---------- Sidebar ---------- */

section[data-testid="stSidebar"] {
    background: #f8fafc;
    border-right: 1px solid #e2e8f0;
}

section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] h4 {
    color: #1e293b !important;
}


/* ---------- Sidebar Buttons ---------- */

section[data-testid="stSidebar"] .stButton button {
    background: #6366f1;
    color: white !important;
    border: none;
    border-radius: 9px;
    font-weight: 600;
}

section[data-testid="stSidebar"] .stButton button:hover {
    background: #4f46e5;
}


/* ---------- File Badge ---------- */

.file-badge {
    background: white;
    border: 1px solid #e2e8f0;
    color: #334155;
    border-radius: 8px;
    padding: 0.5rem 0.7rem;
    margin-bottom: 0.4rem;
    font-size: 0.85rem;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
}


/* ---------- Chat ---------- */

.stChatMessage {
    border-radius: 12px;
}


/* ---------- Empty State ---------- */

.empty-state {
    text-align: center;
    padding: 4rem 1rem;
    color: #64748b;
}

.empty-state h3 {
    color: #334155;
}


/* ---------- Footer ---------- */

.documind-footer {
    text-align: center;
    color: #94a3b8;
    font-size: 0.78rem;
    margin-top: 4rem;
    padding-top: 1.2rem;
    border-top: 1px solid #e2e8f0;
}

.documind-footer strong {
    color: #475569;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="topbar">
    <div class="brand">DOCUMIND</div>
    <div class="creator">Lovish Aggarwal</div>
</div>

<div class="subtitle">
    AI-powered document intelligence · Ask. Understand. Explore.
</div>
""", unsafe_allow_html=True)

if "user_id" not in st.session_state:

    try:
        res = requests.get(
            f"{API_BASE_URL}/new-session",
            timeout=10
        )

        st.session_state.user_id = res.json()["user_id"]

    except Exception:
        st.session_state.user_id = None


if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


if "uploaded_files_list" not in st.session_state:
    st.session_state.uploaded_files_list = []


with st.sidebar:

    st.markdown("### 📁 Document Library")

    st.caption(
        "Upload PDF, DOCX, or TXT files to build your knowledge base."
    )

    uploaded_files = st.file_uploader(
        "Choose file(s)",
        type=ALLOWED_TYPES,
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    if st.button(
        "📤 Upload & Process",
        use_container_width=True,
        disabled=not uploaded_files
    ):

        with st.spinner(
            "Reading, chunking, and embedding your documents..."
        ):
            try:
                files_payload = [
                    (
                        "files",
                        (f.name, f.getvalue(), f.type)
                    )
                    for f in uploaded_files
                ]

                data = {
                    "user_id": st.session_state.user_id
                }

                res = requests.post(
                    f"{API_BASE_URL}/upload",
                    data=data,
                    files=files_payload,
                    timeout=300
                )

                if res.status_code == 200:

                    result = res.json()

                    st.session_state.uploaded_files_list.extend(
                        result["files_received"]
                    )

                    st.success(
                        f"✅ {result['chunks_stored']} chunks stored successfully."
                    )

                else:

                    st.error(
                        f"❌ {res.json().get('detail', 'Upload failed.')}"
                    )

            except Exception as e:

                st.error(
                    f"❌ Could not reach backend: {e}"
                )


    if st.session_state.uploaded_files_list:

        st.markdown("---")

        st.markdown("#### Indexed Files")

        for fname in st.session_state.uploaded_files_list:

            st.markdown(
                f"""
                <div class="file-badge">
                    📄 {fname}
                </div>
                """,
                unsafe_allow_html=True
            )


    st.markdown("---")

    if st.button(
        "🗑️ Clear Chat",
        use_container_width=True
    ):

        st.session_state.chat_history = []

        st.rerun()


    st.markdown("---")

    st.caption(
        f"Session ID: `{st.session_state.user_id[:8] if st.session_state.user_id else 'offline'}...`"
    )


if not st.session_state.chat_history:

    st.markdown("""
    <div class="empty-state">
        <h3>👋 Welcome to DocuMind</h3>
        <p>
            Upload a document from the sidebar,
            then ask a question below.
        </p>
    </div>
    """, unsafe_allow_html=True)

else:

    for msg in st.session_state.chat_history:

        avatar = (
            "🧑‍💻"
            if msg["role"] == "user"
            else "🧠"
        )

        with st.chat_message(
            msg["role"],
            avatar=avatar
        ):

            st.markdown(msg["content"])


query = st.chat_input(
    "Ask DocuMind about your documents..."
)


if query:

    st.session_state.chat_history.append(
        {
            "role": "user",
            "content": query
        }
    )

    with st.chat_message(
        "user",
        avatar="🧑‍💻"
    ):

        st.markdown(query)


    with st.chat_message(
        "assistant",
        avatar="🧠"
    ):

        with st.spinner("Thinking..."):

            try:

                res = requests.post(
                    f"{API_BASE_URL}/ask",
                    json={
                        "session_id": st.session_state.user_id,
                        "question": query
                    },
                    timeout=120
            )

                if res.status_code == 200:

                    answer = res.json()["answer"]

                else:

                    answer = (
                        f"⚠️ Error: "
                        f"{res.json().get('detail', 'Something went wrong.')}"
                    )

            except Exception as e:

                answer = (
                    f"⚠️ Could not reach backend: {e}"
                )


            st.markdown(answer)

            st.session_state.chat_history.append(
                {
                    "role": "assistant",
                    "content": answer
                }
            )


st.markdown("""
<div class="documind-footer">
    <strong>DocuMind</strong> · AI Document Assistant
    <br>
    Crafted with ❤️ by <strong>Lovish Aggarwal</strong>
</div>
""", unsafe_allow_html=True)