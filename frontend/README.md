# Generic Data RAG Agent - Frontend

A modern React frontend for the Generic Data RAG Agent that allows users to upload documents and chat with their data using AI-powered question answering.

## Features

- **Document Upload**: Support for CSV, XLSX, PDF, and TXT files
- **Interactive Chat**: Ask questions about your uploaded documents
- **Structured Responses**: Get answers with proper citations and confidence scores
- **Document Management**: View, select, and download uploaded documents
- **Responsive Design**: Works on desktop and mobile devices
- **Real-time Updates**: Automatic refresh and live chat updates

## Technology Stack

- **React 18** - Modern React with hooks
- **Vite** - Fast build tool and dev server
- **Tailwind CSS** - Utility-first CSS framework
- **Lucide React** - Beautiful icon library

## Setup Instructions

### Prerequisites

- Node.js 16 or higher
- npm or yarn package manager
- Backend server running on http://127.0.0.1:8000

### Installation

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

4. Open your browser and go to `http://localhost:3000`

### Environment Variables

Create a `.env` file in the frontend directory:

```
VITE_API_BASE=http://127.0.0.1:8000
```

Change the URL if your backend is running on a different host/port.

### Building for Production

To build the frontend for production:

```bash
npm run build
```

The built files will be in the `dist` directory.

## Usage

1. **Upload Documents**: Use the upload form at the top to select and upload your documents
2. **Select Documents**: Choose which documents to search in from the left panel
3. **Ask Questions**: Type questions in the chat window on the right
4. **View Responses**: Get structured answers with citations and confidence scores
5. **Download Files**: Download original files using the download button

## API Integration

The frontend communicates with these backend endpoints:

- `POST /api/files/upload` - Upload and index documents
- `GET /api/files/` - List uploaded documents
- `GET /api/files/download/{file_id}` - Download documents
- `POST /api/chat` - Send chat queries and get structured responses

## Component Structure

- **App.jsx** - Main application component with layout
- **UploadBar** - File upload interface with progress tracking
- **DocumentsList** - Document management with selection
- **ChatWindow** - Interactive chat interface with structured responses

## Styling

The application uses Tailwind CSS for styling with a clean, professional design:

- **Color Scheme**: Indigo primary with slate grays
- **Typography**: Clear hierarchy with proper contrast
- **Layout**: Responsive grid system
- **Components**: Consistent spacing and hover effects