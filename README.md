# Generic Data RAG Agent 🤖📊

[![FastAPI](https://img.shields.io/badge/FastAPI-0.95+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.2+-blue.svg)](https://reactjs.org/)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A powerful **Retrieval-Augmented Generation (RAG)** system that allows users to upload various data formats and interact with them through natural language queries. Built with modern technologies and designed for scalability and ease of use.

![Dashboard](.\frontend\Dashboard.png)

## 🚀 Features

- **📄 Multi-Format Support**: Upload and process CSV, Excel, PDF, and text files
- **🧠 Intelligent Retrieval**: Uses sentence transformers for semantic search
- **💬 Natural Language Chat**: Query your data using conversational AI powered by Google Gemini
- **📊 Vector Database**: ChromaDB for efficient similarity search and retrieval
- **🔄 Real-time Processing**: Instant file processing and indexing
- **📈 Chat History**: Persistent conversation history with context awareness
- **🎨 Modern UI**: Clean, responsive interface built with React and Tailwind CSS
- **⚡ Fast API**: High-performance backend with FastAPI and async processing

## 🏗️ Architecture

```
┌────────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React Frontend   │────│   FastAPI       │────│   ChromaDB      │
│   (Vite + Tailwind)│    │   Backend       │    │   Vector Store  │
└────────────────────┘    └─────────────────┘    └─────────────────┘
                                  │
                          ┌─────────────────┐
                          │   Google Gemini │
                          │   AI Model      │
                          └─────────────────┘
```

### Core Components

- **Frontend**: React 18 with Vite, Tailwind CSS, and Lucide React icons
- **Backend**: FastAPI with async support, CORS middleware, and structured routing
- **AI Model**: Google Gemini 2.5 Flash for natural language processing
- **Embeddings**: Sentence Transformers for semantic understanding
- **Vector Database**: ChromaDB for efficient similarity search
- **File Processing**: Support for multiple formats with automatic text extraction

## 🛠️ Tech Stack

### Backend
- **FastAPI** - Modern, fast web framework for building APIs
- **Google Generative AI** - Gemini 2.5 Flash model integration  
- **ChromaDB** - Vector database for embeddings and similarity search
- **Sentence Transformers** - State-of-the-art sentence embeddings
- **Pandas** - Data manipulation and analysis
- **PDFPlumber** - PDF text extraction
- **OpenPyXL** - Excel file processing

### Frontend  
- **React 18** - Modern React with hooks and functional components
- **Vite** - Fast build tool and development server
- **Tailwind CSS** - Utility-first CSS framework
- **Lucide React** - Beautiful, customizable icons

## 🗂️ Project Structure

```
generic-data-rag-agent/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   └── config.py          # Configuration settings
│   │   ├── routers/
│   │   │   ├── chat.py            # Chat endpoints
│   │   │   ├── files.py           # File management endpoints  
│   │   │   └── history.py         # History endpoints
│   │   ├── services/
│   │   │   ├── indexer.py         # Document indexing
│   │   │   ├── ingestion.py       # File processing
│   │   │   ├── retriever.py       # Vector search
│   │   │   └── history.py         # Chat history management
│   │   ├── main.py                # FastAPI application
│   │   ├── models.py              # Pydantic models
│   │   └── storage.py             # File storage utilities
│   ├── chroma_db/                 # Vector database storage
│   ├── uploads/                   # Uploaded files storage
│   ├── requirements.txt           # Python dependencies
│   └── start_server.py           # Server startup script
├── frontend/
│   ├── src/
│   │   ├── App.jsx               # Main React component
│   │   ├── main.jsx              # React entry point
│   │   └── index.css             # Tailwind styles
│   ├── index.html                # HTML template
│   ├── package.json              # Node.js dependencies
│   ├── tailwind.config.js        # Tailwind configuration
│   └── vite.config.js           # Vite configuration
├── start-backend.bat             # Windows backend starter
├── start-frontend.bat            # Windows frontend starter
└── README.md                     # This file
```


## 📋 Prerequisites

- **Python 3.8+**
- **Node.js 16+**
- **Google Gemini API Key** ([Get it here](https://makersuite.google.com/app/apikey))

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/yashdew3/generic-data-rag-agent.git
cd generic-data-rag-agent
```

### 2. Backend Setup
```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env
```

### 3. Environment Configuration
Create a `.env` file in the backend directory:
```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
FRONTEND_ORIGIN=http://localhost:5173
```

### 4. Frontend Setup
```bash
# Navigate to frontend directory (new terminal)
cd frontend

# Install dependencies
npm install
```

### 5. Start the Application

#### Option 1: Using Batch Files (Windows)
```bash
# Start backend (from root directory)
start-backend.bat

# Start frontend (from root directory)  
start-frontend.bat
```

#### Option 2: Manual Start
```bash
# Terminal 1 - Backend
cd backend
python start_server.py

# Terminal 2 - Frontend  
cd frontend
npm run dev
```

### 6. Access the Application
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 📖 Usage Guide

### 1. Upload Files
- Click the **"Choose Files"** button
- Select CSV, Excel, PDF, or text files
- Files are automatically processed and indexed

### 2. Chat with Your Data
- Type natural language questions about your uploaded data
- Examples:
  - "What are the main trends in this dataset?"
  - "Summarize the key findings from the uploaded report"
  - "Show me insights about sales performance"

### 3. View Chat History
- Access previous conversations
- Context is maintained across sessions

## 🔧 API Endpoints

### File Management
- `POST /files/upload` - Upload and process files
- `GET /files/list` - List uploaded files
- `DELETE /files/{file_id}` - Delete a file

### Chat System
- `POST /chat/message` - Send a chat message
- `GET /chat/history/{session_id}` - Get chat history

### History Management
- `GET /history/sessions` - List all chat sessions
- `DELETE /history/sessions/{session_id}` - Delete a session


## 🧪 Testing

### Backend Tests
```bash
cd backend
python test_system.py
```

### Frontend Development
```bash
cd frontend
npm run lint    # ESLint checking
npm run build   # Production build
npm run preview # Preview production build
```

## 🔒 Security Features

- **CORS Protection**: Configurable origin restrictions
- **File Validation**: Secure file type checking
- **API Key Management**: Environment-based configuration
- **Input Sanitization**: Secure data processing


## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the [issues page](https://github.com/yashdew3/generic-data-rag-agent/issues) (if you have one) or open a new issue to discuss changes. Pull requests are also appreciated.

## 📝 License

This project is licensed under the MIT License © Yash Dewangan

## Let's Connect
Feel free to connect or suggest improvements!
- Built by **Yash Dewangan**
- 🐙Github: [YashDewangan](https://github.com/yashdew3)
- 📧Email: [yashdew06@gmail.com](mailto:yashdew06@gmail.com)
- 🔗Linkedin: [YashDewangan](https://www.linkedin.com/in/yash-dewangan/)

---

**Built with ❤️ for intelligent data interaction**

*This project demonstrates modern RAG architecture with production-ready code quality and comprehensive documentation.*