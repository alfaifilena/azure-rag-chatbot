import json
import os
import tempfile
import uuid
from typing import List, Optional
from urllib.parse import urlsplit

import chromadb
import psycopg2
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.storage.blob import BlobServiceClient, ContentSettings
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from openai import OpenAI, OpenAIError
from psycopg2.extras import RealDictCursor
from pydantic import BaseModel

from langchain_chroma import Chroma
from langchain_classic.chains import (
    create_history_aware_retriever,
    create_retrieval_chain,
)
from langchain_classic.chains.combine_documents import (
    create_stuff_documents_chain,
)
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter


# =========================
# Environment / Key Vault
# =========================

load_dotenv()

KEY_VAULT_NAME = os.environ.get("KEY_VAULT_NAME")

if not KEY_VAULT_NAME:
    raise RuntimeError("KEY_VAULT_NAME was not found.")

KEY_VAULT_URL = f"https://{KEY_VAULT_NAME}.vault.azure.net"

credential = DefaultAzureCredential()

secret_client = SecretClient(
    vault_url=KEY_VAULT_URL,
    credential=credential,
)


def get_secret(name: str) -> str:
    value = secret_client.get_secret(name).value

    if value is None:
        raise RuntimeError(
            f"Key Vault secret '{name}' has no value."
        )

    return value


# =========================
# Load secrets from Key Vault
# =========================

DB_NAME = get_secret("PROJ-DB-NAME")
DB_USER = get_secret("PROJ-DB-USER")
DB_PASSWORD = get_secret("PROJ-DB-PASSWORD")
DB_HOST = get_secret("PROJ-DB-HOST")
DB_PORT = get_secret("PROJ-DB-PORT")

api_key = get_secret("PROJ-OPENAI-API-KEY")

AZURE_STORAGE_SAS_URL = get_secret(
    "PROJ-AZURE-STORAGE-SAS-URL"
)

AZURE_STORAGE_CONTAINER = get_secret(
    "PROJ-AZURE-STORAGE-CONTAINER"
)

CHROMA_HOST = get_secret(
    "PROJ-CHROMADB-HOST"
)

CHROMA_PORT = int(
    get_secret("PROJ-CHROMADB-PORT")
)


# =========================
# OpenRouter
# =========================

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

DEFAULT_MODEL = (
    "nvidia/nemotron-3-ultra-550b-a55b:free"
)

EMBEDDING_MODEL = (
    "openai/text-embedding-3-small"
)

client = OpenAI(
    base_url=OPENROUTER_BASE_URL,
    api_key=api_key,
)

model = DEFAULT_MODEL


# =========================
# Azure Blob Storage
# =========================

sas_parts = urlsplit(
    AZURE_STORAGE_SAS_URL
)

if (
    not sas_parts.scheme
    or not sas_parts.netloc
    or not sas_parts.query
):
    raise RuntimeError(
        "PROJ-AZURE-STORAGE-SAS-URL must be "
        "a valid Blob service SAS URL."
    )

storage_account_url = (
    f"{sas_parts.scheme}://{sas_parts.netloc}"
)

storage_sas_token = (
    sas_parts.query
)

blob_service_client = (
    BlobServiceClient(
        account_url=storage_account_url,
        credential=storage_sas_token,
    )
)

container_client = (
    blob_service_client
    .get_container_client(
        AZURE_STORAGE_CONTAINER
    )
)


# =========================
# PostgreSQL
# =========================

DB_CONFIG = {
    "dbname": DB_NAME,
    "user": DB_USER,
    "password": DB_PASSWORD,
    "host": DB_HOST,
    "port": DB_PORT,
    "sslmode": "require",
}


def get_db():
    conn = psycopg2.connect(
        **DB_CONFIG
    )

    try:
        yield conn
    finally:
        conn.close()


# =========================
# Chroma
# =========================

def get_chroma_client():
    return chromadb.HttpClient(
        host=CHROMA_HOST,
        port=CHROMA_PORT,
    )


def get_embeddings():
    return OpenAIEmbeddings(
        model=EMBEDDING_MODEL,
        api_key=api_key,
        base_url=OPENROUTER_BASE_URL,
        check_embedding_ctx_length=False,
    )


# =========================
# FastAPI
# =========================

app = FastAPI()


# =========================
# Models
# =========================

class ChatRequest(BaseModel):
    messages: List[dict]


class SaveChatRequest(BaseModel):
    chat_id: str
    chat_name: str
    messages: List[dict]

    pdf_name: Optional[str] = None
    pdf_path: Optional[str] = None
    pdf_uuid: Optional[str] = None


class DeleteChatRequest(BaseModel):
    chat_id: str


class RAGChatRequest(BaseModel):
    messages: List[dict]
    pdf_uuid: str


# =========================
# Health Check
# =========================

@app.get("/health/")
def health():
    return {
        "status": "ok",
        "config_source": "azure-key-vault",
    }


# =========================
# Normal Chat
# =========================

@app.post("/chat/")
async def chat(
    request: ChatRequest
):
    try:
        stream = (
            client.chat.completions.create(
                model=model,
                messages=request.messages,
                stream=True,
            )
        )

        def stream_response():
            for chunk in stream:
                if not chunk.choices:
                    continue

                delta = (
                    chunk
                    .choices[0]
                    .delta
                    .content
                )

                if delta:
                    yield delta

        return StreamingResponse(
            stream_response(),
            media_type="text/plain",
        )

    except OpenAIError as e:
        raise HTTPException(
            status_code=502,
            detail=str(e),
        )


# =========================
# Upload PDF
# =========================

@app.post("/upload_pdf/")
async def upload_pdf(
    file: UploadFile = File(...)
):
    if (
        not file.filename
        or not file.filename
        .lower()
        .endswith(".pdf")
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Only PDF files are supported."
            ),
        )

    pdf_uuid = str(
        uuid.uuid4()
    )

    blob_name = (
        f"pdfs/{pdf_uuid}.pdf"
    )

    try:
        file_content = (
            await file.read()
        )

        blob_client = (
            container_client
            .get_blob_client(
                blob_name
            )
        )

        blob_client.upload_blob(
            file_content,
            overwrite=True,
            content_settings=(
                ContentSettings(
                    content_type=(
                        "application/pdf"
                    )
                )
            ),
        )

        return {
            "message": (
                "PDF uploaded successfully"
            ),
            "pdf_name": file.filename,
            "pdf_path": blob_name,
            "pdf_uuid": pdf_uuid,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=(
                "PDF upload failed: "
                f"{str(e)}"
            ),
        )


# =========================
# Save Chat
# =========================

@app.post("/save_chat/")
async def save_chat(
    request: SaveChatRequest,
    db: psycopg2.extensions.connection = (
        Depends(get_db)
    ),
):
    chat_blob_name = (
        f"chat_logs/"
        f"{request.chat_id}.json"
    )

    try:
        chat_blob = (
            container_client
            .get_blob_client(
                chat_blob_name
            )
        )

        chat_blob.upload_blob(
            json.dumps(
                request.messages,
                ensure_ascii=False,
                indent=4,
            ).encode("utf-8"),
            overwrite=True,
            content_settings=(
                ContentSettings(
                    content_type=(
                        "application/json"
                    )
                )
            ),
        )

        with db.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO advanced_chats
                (
                    id,
                    name,
                    file_path,
                    last_update,
                    pdf_name,
                    pdf_path,
                    pdf_uuid
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    CURRENT_TIMESTAMP,
                    %s,
                    %s,
                    %s
                )
                ON CONFLICT (id)
                DO UPDATE SET
                    name = EXCLUDED.name,
                    file_path = EXCLUDED.file_path,
                    last_update = CURRENT_TIMESTAMP,
                    pdf_name = EXCLUDED.pdf_name,
                    pdf_path = EXCLUDED.pdf_path,
                    pdf_uuid = EXCLUDED.pdf_uuid
                """,
                (
                    request.chat_id,
                    request.chat_name,
                    chat_blob_name,
                    request.pdf_name,
                    request.pdf_path,
                    request.pdf_uuid,
                ),
            )

        db.commit()

        return {
            "message": (
                "Chat saved successfully"
            )
        }

    except Exception as e:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Error: {str(e)}",
        )


# =========================
# Load Chats
# =========================

@app.get("/load_chat/")
async def load_chat(
    db: psycopg2.extensions.connection = (
        Depends(get_db)
    ),
):
    try:
        with db.cursor(
            cursor_factory=RealDictCursor
        ) as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    name,
                    file_path,
                    pdf_name,
                    pdf_path,
                    pdf_uuid
                FROM advanced_chats
                ORDER BY last_update DESC
                """
            )

            rows = (
                cursor.fetchall()
            )

        records = []

        for row in rows:
            try:
                chat_blob = (
                    container_client
                    .get_blob_client(
                        row["file_path"]
                    )
                )

                messages = json.loads(
                    chat_blob
                    .download_blob()
                    .readall()
                    .decode("utf-8")
                )

            except Exception:
                messages = []

            records.append(
                {
                    "id": row["id"],
                    "chat_name": (
                        row["name"]
                    ),
                    "messages": messages,
                    "pdf_name": (
                        row["pdf_name"]
                    ),
                    "pdf_path": (
                        row["pdf_path"]
                    ),
                    "pdf_uuid": (
                        row["pdf_uuid"]
                    ),
                }
            )

        return records

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error: {str(e)}",
        )


# =========================
# Delete Chat
# =========================

@app.post("/delete_chat/")
async def delete_chat(
    request: DeleteChatRequest,
    db: psycopg2.extensions.connection = (
        Depends(get_db)
    ),
):
    try:
        with db.cursor(
            cursor_factory=RealDictCursor
        ) as cursor:
            cursor.execute(
                """
                SELECT
                    file_path,
                    pdf_path,
                    pdf_uuid
                FROM advanced_chats
                WHERE id = %s
                """,
                (
                    request.chat_id,
                ),
            )

            row = (
                cursor.fetchone()
            )

        if not row:
            raise HTTPException(
                status_code=404,
                detail="Chat not found",
            )

        with db.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM advanced_chats
                WHERE id = %s
                """,
                (
                    request.chat_id,
                ),
            )

        db.commit()

        if row["file_path"]:
            try:
                container_client.delete_blob(
                    row["file_path"],
                    delete_snapshots="include",
                )
            except Exception:
                pass

        if row["pdf_path"]:
            try:
                container_client.delete_blob(
                    row["pdf_path"],
                    delete_snapshots="include",
                )
            except Exception:
                pass

        if row["pdf_uuid"]:
            try:
                get_chroma_client() \
                    .delete_collection(
                        name=(
                            f"pdf_"
                            f"{row['pdf_uuid']}"
                        )
                    )
            except Exception:
                pass

        return {
            "message": (
                "Chat deleted successfully"
            )
        }

    except HTTPException:
        raise

    except Exception as e:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Error: {str(e)}",
        )


# =========================
# RAG
# =========================

def create_vector_store(
    pdf_uuid: str,
):
    chroma = (
        get_chroma_client()
    )

    collection_name = (
        f"pdf_{pdf_uuid}"
    )

    collection = (
        chroma
        .get_or_create_collection(
            name=collection_name
        )
    )

    vector_store = Chroma(
        client=chroma,
        collection_name=(
            collection_name
        ),
        embedding_function=(
            get_embeddings()
        ),
    )

    if collection.count() > 0:
        return vector_store

    pdf_blob_name = (
        f"pdfs/{pdf_uuid}.pdf"
    )

    try:
        pdf_bytes = (
            container_client
            .get_blob_client(
                pdf_blob_name
            )
            .download_blob()
            .readall()
        )

    except Exception as e:
        raise FileNotFoundError(
            "PDF could not be "
            "downloaded from Azure "
            f"Blob Storage: {e}"
        )

    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            suffix=".pdf",
            delete=False,
        ) as temp_file:
            temp_file.write(
                pdf_bytes
            )

            temp_path = (
                temp_file.name
            )

        loader = (
            PyPDFLoader(
                temp_path
            )
        )

        documents = (
            loader.load()
        )

        text_splitter = (
            RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
            )
        )

        chunks = (
            text_splitter
            .split_documents(
                documents
            )
        )

        vector_store.add_documents(
            chunks
        )

        return vector_store

    finally:
        if (
            temp_path
            and os.path.exists(
                temp_path
            )
        ):
            os.remove(
                temp_path
            )


# =========================
# RAG Chat
# =========================

@app.post("/rag_chat/")
async def rag_chat(
    request: RAGChatRequest
):
    try:
        if not request.messages:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Messages cannot "
                    "be empty."
                ),
            )

        vector_store = (
            create_vector_store(
                request.pdf_uuid
            )
        )

        retriever = (
            vector_store
            .as_retriever(
                search_kwargs={
                    "k": 4
                }
            )
        )

        llm = ChatOpenAI(
            model=DEFAULT_MODEL,
            temperature=0,
            api_key=api_key,
            base_url=(
                OPENROUTER_BASE_URL
            ),
        )

        contextualize_q_prompt = (
            ChatPromptTemplate
            .from_messages(
                [
                    (
                        "system",
                        "Given a chat "
                        "history and the "
                        "latest user "
                        "question, rewrite "
                        "the question so "
                        "it can be "
                        "understood without "
                        "the chat history.",
                    ),
                    MessagesPlaceholder(
                        "chat_history"
                    ),
                    (
                        "human",
                        "{input}",
                    ),
                ]
            )
        )

        history_aware_retriever = (
            create_history_aware_retriever(
                llm,
                retriever,
                contextualize_q_prompt,
            )
        )

        qa_prompt = (
            ChatPromptTemplate
            .from_messages(
                [
                    (
                        "system",
                        "You are an "
                        "assistant answering "
                        "questions about "
                        "the uploaded "
                        "document. Use only "
                        "the provided "
                        "context to answer. "
                        "If the answer is "
                        "not in the "
                        "document, say that "
                        "you cannot find it "
                        "in the document."
                        "\n\nContext:\n"
                        "{context}",
                    ),
                    MessagesPlaceholder(
                        "chat_history"
                    ),
                    (
                        "human",
                        "{input}",
                    ),
                ]
            )
        )

        question_answer_chain = (
            create_stuff_documents_chain(
                llm,
                qa_prompt,
            )
        )

        rag_chain = (
            create_retrieval_chain(
                history_aware_retriever,
                question_answer_chain,
            )
        )

        chat_history = []

        for message in (
            request.messages[:-1]
        ):
            if (
                message["role"]
                == "user"
            ):
                chat_history.append(
                    HumanMessage(
                        content=(
                            message[
                                "content"
                            ]
                        )
                    )
                )

            elif (
                message["role"]
                == "assistant"
            ):
                chat_history.append(
                    AIMessage(
                        content=(
                            message[
                                "content"
                            ]
                        )
                    )
                )

        latest_message = (
            request.messages[-1][
                "content"
            ]
        )

        result = (
            rag_chain.invoke(
                {
                    "input": (
                        latest_message
                    ),
                    "chat_history": (
                        chat_history
                    ),
                }
            )
        )

        answer = (
            result["answer"]
        )

        def stream_answer():
            yield answer

        return StreamingResponse(
            stream_answer(),
            media_type="text/plain",
        )

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=(
                f"RAG error: {str(e)}"
            ),
        )
