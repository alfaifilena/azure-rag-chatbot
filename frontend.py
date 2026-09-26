import os
import uuid

import requests
import streamlit as st


# =========================
# Page Configuration
# =========================

st.title("Chatbot (frontend + backend)")

BACKEND_URL = os.environ.get(
    "BACKEND_URL",
    "http://127.0.0.1:9000",
)

LOAD_CHAT_URL = f"{BACKEND_URL}/load_chat/"
SAVE_CHAT_URL = f"{BACKEND_URL}/save_chat/"
DELETE_CHAT_URL = f"{BACKEND_URL}/delete_chat/"
UPLOAD_PDF_URL = f"{BACKEND_URL}/upload_pdf/"
CHAT_URL = f"{BACKEND_URL}/chat/"
RAG_CHAT_URL = f"{BACKEND_URL}/rag_chat/"


# =========================
# Session State
# =========================

if "history_chats" not in st.session_state:
    st.session_state["history_chats"] = []

if "current_chat" not in st.session_state:
    st.session_state["current_chat"] = None

if "chat_names" not in st.session_state:
    st.session_state["chat_names"] = {}

if "chats_loaded" not in st.session_state:
    st.session_state["chats_loaded"] = False


# =========================
# Save Chat
# =========================

def save_chat_to_db(
    chat_id,
    chat_name,
    messages,
    pdf_name=None,
    pdf_path=None,
    pdf_uuid=None,
):
    try:
        response = requests.post(
            SAVE_CHAT_URL,
            json={
                "chat_id": chat_id,
                "chat_name": chat_name,
                "messages": messages,
                "pdf_name": pdf_name,
                "pdf_path": pdf_path,
                "pdf_uuid": pdf_uuid,
            },
            timeout=60,
        )

        response.raise_for_status()

    except requests.RequestException as error:
        st.error(f"Could not save chat: {error}")


# =========================
# Load Chats
# =========================

def load_chats_from_db():

    try:
        response = requests.get(
            LOAD_CHAT_URL,
            timeout=60,
        )

        response.raise_for_status()

    except requests.RequestException as error:
        st.error(
            f"Could not reach the backend: {error}"
        )
        return

    for record in response.json():

        chat_id = record["id"]

        st.session_state["history_chats"].append(
            {
                "id": chat_id,
                "messages": record["messages"],
                "pdf_name": record.get("pdf_name"),
                "pdf_path": record.get("pdf_path"),
                "pdf_uuid": record.get("pdf_uuid"),
            }
        )

        st.session_state["chat_names"][chat_id] = (
            record["chat_name"]
        )


# =========================
# Load Saved Chats Once
# =========================

if not st.session_state["chats_loaded"]:

    load_chats_from_db()

    st.session_state["chats_loaded"] = True


# =========================
# Create Normal Chat
# =========================

def create_chat(chat_name):

    new_chat_id = str(uuid.uuid4())

    new_chat = {
        "id": new_chat_id,
        "messages": [],
        "pdf_name": None,
        "pdf_path": None,
        "pdf_uuid": None,
    }

    st.session_state["history_chats"].insert(
        0,
        new_chat,
    )

    st.session_state["chat_names"][new_chat_id] = (
        chat_name
    )

    st.session_state["current_chat"] = new_chat_id

    # Save empty chat
    save_chat_to_db(
        new_chat_id,
        chat_name,
        [],
        None,
        None,
        None,
    )


# =========================
# Create Chat With PDF
# =========================

def create_chat_with_pdf(
    chat_name,
    uploaded_pdf,
):

    with st.spinner(
        "Uploading and processing document, please wait..."
    ):

        files = {
            "file": (
                uploaded_pdf.name,
                uploaded_pdf.getvalue(),
                "application/pdf",
            )
        }

        try:

            response = requests.post(
                UPLOAD_PDF_URL,
                files=files,
                timeout=300,
            )

            response.raise_for_status()

        except requests.RequestException as error:

            st.error(
                f"Failed to upload PDF: {error}"
            )

            return

        pdf_path = response.json()["pdf_path"]
        pdf_uuid = response.json()["pdf_uuid"]

        new_chat_id = str(uuid.uuid4())

        new_chat = {
            "id": new_chat_id,
            "messages": [],
            "pdf_name": uploaded_pdf.name,
            "pdf_path": pdf_path,
            "pdf_uuid": pdf_uuid,
        }

        st.session_state["history_chats"].insert(
            0,
            new_chat,
        )

        st.session_state["chat_names"][new_chat_id] = (
            chat_name
        )

        st.session_state["current_chat"] = (
            new_chat_id
        )

        save_chat_to_db(
            new_chat_id,
            chat_name,
            [],
            uploaded_pdf.name,
            pdf_path,
            pdf_uuid,
        )

        st.success(
            "PDF uploaded and chat created."
        )


# =========================
# Select Chat
# =========================

def select_chat(chat_id):

    st.session_state["current_chat"] = chat_id


# =========================
# Delete Chat
# =========================

def delete_chat():

    chat_id = st.session_state["current_chat"]

    if not chat_id:
        return

    try:

        response = requests.post(
            DELETE_CHAT_URL,
            json={
                "chat_id": chat_id
            },
            timeout=60,
        )

        response.raise_for_status()

    except requests.RequestException as error:

        st.error(
            f"Could not delete chat: {error}"
        )

        return

    # Remove from session state
    st.session_state["history_chats"] = [
        chat
        for chat in st.session_state["history_chats"]
        if chat["id"] != chat_id
    ]

    st.session_state["chat_names"].pop(
        chat_id,
        None,
    )

    # Select another chat if available
    if st.session_state["history_chats"]:

        st.session_state["current_chat"] = (
            st.session_state["history_chats"][0]["id"]
        )

    else:

        st.session_state["current_chat"] = None


# =========================
# Sidebar
# =========================

with st.sidebar:

    st.title("Chat Management")

    # Chat name
    chat_name = st.text_input(
        "Enter Chat Name:",
        key="new_chat_name",
    )

    # PDF uploader
    uploaded_pdf = st.file_uploader(
        "Upload PDF",
        type="pdf",
        key="pdf_uploader",
    )

    # =========================
    # Create Normal Chat
    # =========================

    if st.button("Create New Chat"):

        if chat_name.strip():

            create_chat(
                chat_name.strip()
            )

            st.rerun()

        else:

            st.warning(
                "Chat name cannot be empty."
            )

    # =========================
    # Create PDF Chat
    # =========================

    if st.button("Create New Chat with PDF"):

        if not uploaded_pdf:

            st.warning(
                "Please upload a PDF file before creating the chat."
            )

        elif chat_name.strip():

            create_chat_with_pdf(
                chat_name.strip(),
                uploaded_pdf,
            )

            st.rerun()

        else:

            st.warning(
                "Chat name cannot be empty."
            )

    # =========================
    # Display Existing Chats
    # =========================

    if st.session_state["history_chats"]:

        chat_options = {
            chat["id"]:
            st.session_state["chat_names"][chat["id"]]
            for chat in st.session_state["history_chats"]
        }

        selected_chat = st.radio(
            "Select Chat",
            options=list(chat_options.keys()),
            format_func=lambda x: chat_options[x],
            key="chat_selector",
            on_change=lambda: select_chat(
                st.session_state.chat_selector
            ),
        )

        st.session_state["current_chat"] = (
            selected_chat
        )

        # Delete button
        if st.button("Delete Chat"):

            delete_chat()

            st.rerun()


# =========================
# Get Current Chat
# =========================

current_chat = None

if st.session_state["current_chat"]:

    for chat in st.session_state["history_chats"]:

        if (
            chat["id"]
            == st.session_state["current_chat"]
        ):

            current_chat = chat

            break


# =========================
# Display Current Chat
# =========================

if current_chat:

    # Show associated PDF
    if current_chat.get("pdf_name"):

        st.caption(
            f"📄 Associated with: "
            f"{current_chat['pdf_name']}"
        )

    # Display messages
    for message in current_chat["messages"]:

        with st.chat_message(
            message["role"]
        ):

            st.markdown(
                message["content"]
            )


# =========================
# Chat Input
# =========================

if current_chat:

    if prompt := st.chat_input(
        "Your Message:"
    ):

        # =========================
        # Add User Message
        # =========================

        current_chat["messages"].append(
            {
                "role": "user",
                "content": prompt,
            }
        )

        with st.chat_message("user"):

            st.markdown(prompt)

        # =========================
        # Assistant Response
        # =========================

        with st.chat_message("assistant"):

            payload = {
                "messages": [
                    {
                        "role": message["role"],
                        "content": message["content"],
                    }
                    for message
                    in current_chat["messages"]
                ]
            }

            # =========================
            # Choose Endpoint
            # =========================

            if current_chat.get("pdf_uuid"):

                payload["pdf_uuid"] = (
                    current_chat["pdf_uuid"]
                )

                chat_target_url = RAG_CHAT_URL

            else:

                chat_target_url = CHAT_URL

            # =========================
            # Stream Response
            # =========================

            def get_stream_response():

                with requests.post(
                    chat_target_url,
                    json=payload,
                    stream=True,
                    timeout=300,
                ) as response:

                    response.raise_for_status()

                    for chunk in response.iter_content(
                        chunk_size=None
                    ):

                        if chunk:

                            yield chunk.decode(
                                "utf-8"
                            )

            try:

                response = st.write_stream(
                    get_stream_response
                )

            except requests.RequestException as error:

                st.error(
                    f"Backend request failed: {error}"
                )

                # Remove user message
                current_chat["messages"].pop()

            else:

                # =========================
                # Save Assistant Response
                # =========================

                current_chat["messages"].append(
                    {
                        "role": "assistant",
                        "content": response,
                    }
                )

                # =========================
                # Save Complete Conversation
                # =========================

                chat_id = current_chat["id"]

                chat_name = st.session_state[
                    "chat_names"
                ][chat_id]

                save_chat_to_db(
                    chat_id,
                    chat_name,
                    current_chat["messages"],
                    current_chat.get("pdf_name"),
                    current_chat.get("pdf_path"),
                    current_chat.get("pdf_uuid"),
                )

else:

    st.info(
        "Create a new chat from the sidebar to get started."
    )