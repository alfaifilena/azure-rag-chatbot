# ☁️ Azure RAG Chatbot

A cloud-based Retrieval-Augmented Generation (RAG) chatbot built and deployed on Microsoft Azure.

The project combines AI-powered chat, PDF-based question answering, cloud storage, vector search, secure secret management, containerization, Infrastructure as Code, and automated CI/CD deployment.

---

## 🚀 Features

- AI-powered chatbot
- PDF upload and processing
- Retrieval-Augmented Generation (RAG)
- Context-aware document question answering
- Vector search using ChromaDB
- Persistent chat history
- Azure PostgreSQL integration
- Azure Blob Storage for PDFs and chat files
- Secure secret management with Azure Key Vault
- Azure Managed Identity
- Docker containerization
- Terraform Infrastructure as Code
- Automated CI/CD with GitHub Actions
- Docker Hub image deployment
- Automatic deployment to Azure VM

---

## 🛠️ Technologies Used

| Category | Technology |
|---|---|
| Programming Language | Python |
| Frontend | Streamlit |
| Backend | FastAPI |
| RAG Framework | LangChain |
| Vector Database | ChromaDB |
| AI Provider | OpenRouter |
| Database | Azure PostgreSQL |
| File Storage | Azure Blob Storage |
| Secret Management | Azure Key Vault |
| Cloud Platform | Microsoft Azure |
| Containers | Docker & Docker Compose |
| Infrastructure as Code | Terraform |
| CI/CD | GitHub Actions |
| Container Registry | Docker Hub |

---

## 🏗️ Architecture

**User**  
↓  
**Streamlit Frontend**  
↓  
**FastAPI Backend**  
↓  
**Azure PostgreSQL / Azure Blob Storage / ChromaDB**  
↓  
**OpenRouter**

The application is hosted on an Azure Virtual Machine and runs using Docker Compose.

Azure Key Vault stores sensitive credentials, while the VM uses Managed Identity to securely access them.

---

## 📄 RAG Workflow

**PDF Upload**  
↓  
**Azure Blob Storage**  
↓  
**Text Extraction**  
↓  
**Text Chunking**  
↓  
**Embeddings**  
↓  
**ChromaDB**  
↓  
**Similarity Search**  
↓  
**Relevant Context**  
↓  
**LLM Response**

The chatbot retrieves relevant content from the uploaded document and uses it as context to generate document-grounded answers.

---

## ⚙️ CI/CD Pipeline

**Developer Push**  
↓  
**GitHub**  
↓  
**GitHub Actions**  
↓  
**Build Docker Images**  
↓  
**Docker Hub**  
↓  
**Azure VM**  
↓  
**Docker Compose Pull**  
↓  
**Application Updated**

Every push to the deployment branch automatically triggers the CI/CD pipeline.

GitHub Actions builds the backend and frontend Docker images, pushes them to Docker Hub, and deploys the latest version to the Azure VM.

---

## 🔐 Security

The project follows secure secret-management practices:

- Azure Key Vault stores application secrets
- Azure Managed Identity is used for Key Vault access
- GitHub Secrets store CI/CD credentials
- PostgreSQL connections use SSL
- Sensitive files are excluded using `.gitignore`
- API keys, passwords, SAS tokens, and private SSH keys are not stored in the source code

---

## 📡 API Endpoints

The FastAPI backend provides:

- `GET /health/`
- `POST /chat/`
- `POST /upload_pdf/`
- `POST /save_chat/`
- `GET /load_chat/`
- `POST /delete_chat/`
- `POST /rag_chat/`

Interactive API documentation is available through Swagger UI.

---

## ☁️ Azure Services

The project uses:

- Azure Virtual Machine
- Azure Virtual Network
- Azure Network Security Group
- Azure Public IP
- Azure Database for PostgreSQL Flexible Server
- Azure Blob Storage
- Azure Key Vault
- Azure Managed Identity

---

## 🌐 Live Application

**Chatbot**  
http://172.200.13.241:8501/

**API Documentation**  
http://172.200.13.241:5000/docs

**Health Check**  
http://172.200.13.241:5000/health/

> The live Azure environment may be stopped when it is not being used for testing or demonstration.

---

## 📌 Project Status

**Completed**

The project includes:

- Cloud deployment
- RAG functionality
- Persistent data storage
- Secure secret management
- Docker containerization
- Terraform Infrastructure as Code
- GitHub Actions CI/CD
- Automated Azure deployment

---

## © License

Copyright © 2026.

All Rights Reserved.

This project is provided for educational and portfolio purposes only. Unauthorized copying, redistribution, modification, or commercial use is not permitted.
