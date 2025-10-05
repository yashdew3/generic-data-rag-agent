import React, { useEffect, useState, useRef } from "react";
import { Upload, FileText, MessageCircle, RefreshCw, Download, Send, X, AlertCircle, Trash2 } from "lucide-react";

const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

function bytesToSize(bytes) {
  if (!bytes) return "0 B";
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${parseFloat((bytes / Math.pow(1024, i)).toFixed(2))} ${sizes[i]}`;
}

function UploadBar({ onUploaded }) {
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(null);
  const inputRef = useRef(null);

  async function handleUpload() {
    if (!selectedFiles.length) return;
    setUploading(true);
    setUploadProgress("Preparing files...");
    
    try {
      const fd = new FormData();
      for (const f of selectedFiles) fd.append("files", f);
      
      setUploadProgress("Uploading and indexing...");
      const resp = await fetch(`${API_BASE}/api/files/upload`, {
        method: "POST",
        body: fd,
      });
      
      if (!resp.ok) {
        const errorText = await resp.text();
        throw new Error(`Upload failed: ${resp.status} - ${errorText}`);
      }
      
      const json = await resp.json();
      setSelectedFiles([]);
      if (inputRef.current) inputRef.current.value = null;
      setUploadProgress("Upload completed successfully!");
      
      setTimeout(() => setUploadProgress(null), 2000);
      onUploaded && onUploaded(json.files);
    } catch (err) {
      console.error("Upload error:", err);
      setUploadProgress(`Error: ${err.message}`);
      setTimeout(() => setUploadProgress(null), 5000);
    } finally {
      setUploading(false);
    }
  }

  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files || []);
    const validTypes = ['.csv', '.xlsx', '.xls', '.pdf', '.txt'];
    const validFiles = files.filter(file => {
      const ext = file.name.toLowerCase().substring(file.name.lastIndexOf('.'));
      return validTypes.includes(ext);
    });
    
    if (validFiles.length !== files.length) {
      alert(`Some files were skipped. Only ${validTypes.join(', ')} files are supported.`);
    }
    
    setSelectedFiles(validFiles);
  };

  return (
    <div className="w-full bg-white rounded-lg shadow-sm border">
      <div className="p-6">
        <div className="flex items-center gap-3 mb-4">
          <Upload className="w-6 h-6 text-indigo-600" />
          <h2 className="text-xl font-semibold text-slate-800">Document Upload</h2>
        </div>
        
        <div className="flex items-center gap-4">
          <div className="flex-1">
            <input
              ref={inputRef}
              type="file"
              multiple
              accept=".csv,.xlsx,.xls,.pdf,.txt"
              onChange={handleFileSelect}
              className="block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100 file:cursor-pointer cursor-pointer"
            />
          </div>
          <button
            onClick={handleUpload}
            disabled={uploading || !selectedFiles.length}
            className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
          >
            {uploading ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                Uploading...
              </>
            ) : (
              <>
                <Upload className="w-4 h-4" />
                Upload & Index
              </>
            )}
          </button>
        </div>
        
        {selectedFiles.length > 0 && (
          <div className="mt-4 p-3 bg-slate-50 rounded-lg">
            <div className="text-sm font-medium text-slate-700 mb-2">Selected Files:</div>
            <div className="space-y-1">
              {selectedFiles.map((f) => (
                <div key={f.name} className="flex items-center justify-between text-sm text-slate-600">
                  <span className="font-medium">{f.name}</span>
                  <span className="text-xs text-slate-400">{bytesToSize(f.size)}</span>
                </div>
              ))}
            </div>
          </div>
        )}
        
        {uploadProgress && (
          <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
            <div className="text-sm text-blue-700">{uploadProgress}</div>
          </div>
        )}
      </div>
    </div>
  );
}

function DocumentsList({ files, selectedIds, onToggleSelect, onRefresh, onDeleteFile }) {
  const [deletingFiles, setDeletingFiles] = useState(new Set());
  const allSelected = files.length > 0 && selectedIds.length === files.length;
  const someSelected = selectedIds.length > 0 && selectedIds.length < files.length;

  const handleSelectAll = () => {
    if (allSelected) {
      // Deselect all
      files.forEach(f => {
        if (selectedIds.includes(f.id)) {
          onToggleSelect(f.id);
        }
      });
    } else {
      // Select all not yet selected
      files.forEach(f => {
        if (!selectedIds.includes(f.id)) {
          onToggleSelect(f.id);
        }
      });
    }
  };

  return (
    <div className="h-[70vh] bg-white rounded-lg shadow-sm border flex flex-col">
      <div className="flex items-center justify-between p-4 border-b bg-slate-50 rounded-t-lg">
        <div className="flex items-center gap-2">
          <FileText className="w-5 h-5 text-indigo-600" />
          <h3 className="text-lg font-semibold text-slate-800">Documents</h3>
          {selectedIds.length > 0 && (
            <span className="px-2 py-1 bg-indigo-100 text-indigo-700 text-xs rounded-full">
              {selectedIds.length} selected
            </span>
          )}
        </div>
        <button 
          onClick={onRefresh} 
          className="p-2 text-slate-400 hover:text-slate-600 transition-colors"
          title="Refresh document list"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      <div className="flex-1 overflow-auto">
        {files.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-400 p-8">
            <FileText className="w-16 h-16 mb-4 text-slate-300" />
            <p className="text-lg font-medium mb-2">No documents uploaded</p>
            <p className="text-sm text-center">Upload documents using the form above to get started</p>
          </div>
        ) : (
          <div className="p-4">
            <div className="flex items-center gap-2 mb-4 pb-2 border-b">
              <input
                type="checkbox"
                checked={allSelected}
                ref={input => {
                  if (input) input.indeterminate = someSelected;
                }}
                onChange={handleSelectAll}
                className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
              />
              <span className="text-sm font-medium text-slate-700">
                {allSelected ? "Deselect all" : someSelected ? "Select all" : "Select all"}
              </span>
            </div>
            
            <div className="space-y-2">
              {files.map((f) => (
                <div 
                  key={f.id} 
                  className={`flex items-center gap-3 p-3 rounded-lg border transition-all ${
                    selectedIds.includes(f.id) 
                      ? 'border-indigo-200 bg-indigo-50' 
                      : 'border-slate-200 hover:border-slate-300'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selectedIds.includes(f.id)}
                    onChange={() => onToggleSelect(f.id)}
                    className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                  />
                  
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-slate-800 truncate">{f.original_name}</div>
                    <div className="flex items-center gap-2 mt-1 text-xs text-slate-500">
                      <span>{f.content_type}</span>
                      <span>•</span>
                      <span>{bytesToSize(f.size)}</span>
                      <span>•</span>
                      <span>{new Date(f.uploaded_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-1">
                    <a
                      className="flex items-center gap-1 px-2 py-1 text-sm text-indigo-600 hover:text-indigo-800 hover:bg-indigo-100 rounded transition-colors"
                      href={`${API_BASE}/api/files/download/${f.id}`}
                      target="_blank"
                      rel="noreferrer"
                      title="Download file"
                    >
                      <Download className="w-4 h-4" />
                    </a>
                    <button
                      onClick={async () => {
                        setDeletingFiles(prev => new Set([...prev, f.id]));
                        try {
                          await onDeleteFile(f.id, f.original_name);
                        } finally {
                          setDeletingFiles(prev => {
                            const newSet = new Set(prev);
                            newSet.delete(f.id);
                            return newSet;
                          });
                        }
                      }}
                      disabled={deletingFiles.has(f.id)}
                      className="flex items-center gap-1 px-2 py-1 text-sm text-red-600 hover:text-red-800 hover:bg-red-100 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      title={deletingFiles.has(f.id) ? "Deleting..." : "Delete file"}
                    >
                      {deletingFiles.has(f.id) ? (
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-red-600"></div>
                      ) : (
                        <Trash2 className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function ChatWindow({ selectedFileIds }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [topK, setTopK] = useState(5);
  const scrollRef = useRef(null);

  useEffect(() => {
    // restore history from localStorage
    const h = localStorage.getItem("chat_history");
    if (h) setMessages(JSON.parse(h));
  }, []);

  useEffect(() => {
    localStorage.setItem("chat_history", JSON.stringify(messages));
    // scroll to bottom
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  async function handleSend() {
    const q = input.trim();
    if (!q) return;
    const userMsg = { id: Date.now(), sender: "user", text: q, timestamp: new Date().toISOString() };
    setMessages((m) => [...m, userMsg]);
    setInput("");

    setLoading(true);
    try {
      const payload = { query: q, top_k: topK, file_ids: selectedFileIds.length ? selectedFileIds : undefined };
      const resp = await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!resp.ok) {
        const errorText = await resp.text();
        throw new Error(`Chat request failed: ${resp.status} - ${errorText}`);
      }
      const json = await resp.json();
      
      // Handle structured response
      const botMsg = { 
        id: Date.now() + 1, 
        sender: "bot", 
        text: json.structured_answer?.answer || json.answer || "No answer provided",
        sources: json.sources || [],
        citations: json.structured_answer?.citations || [],
        confidence: json.structured_answer?.confidence_score,
        timestamp: new Date().toISOString(),
        isStructured: !!json.structured_answer
      };
      setMessages((m) => [...m, botMsg]);
    } catch (err) {
      const errMsg = { 
        id: Date.now() + 2, 
        sender: "bot", 
        text: "I apologize, but I encountered an error while processing your request. Please try again.",
        error: err.message,
        timestamp: new Date().toISOString()
      };
      setMessages((m) => [...m, errMsg]);
    } finally {
      setLoading(false);
    }
  }

  function clearChat() {
    setMessages([]);
    localStorage.removeItem("chat_history");
  }

  return (
    <div className="h-[80vh] flex flex-col bg-white rounded-lg shadow-sm border">
      <div className="flex items-center justify-between p-4 border-b bg-slate-50 rounded-t-lg">
        <div className="flex items-center gap-2">
          <MessageCircle className="w-5 h-5 text-indigo-600" />
          <h3 className="text-lg font-semibold text-slate-800">Chat Assistant</h3>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-sm text-slate-600">
            <span>Top-K:</span>
            <input 
              type="number" 
              value={topK} 
              onChange={(e) => setTopK(parseInt(e.target.value || "5"))} 
              className="w-16 border border-slate-300 px-2 py-1 rounded text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500" 
              min="1" 
              max="20"
            />
          </div>
          <button 
            onClick={clearChat}
            className="p-1 text-slate-400 hover:text-slate-600 transition-colors"
            title="Clear chat history"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-slate-400 py-8">
            <MessageCircle className="w-12 h-12 mx-auto mb-3 text-slate-300" />
            <p>Ask a question about your uploaded documents</p>
            <p className="text-sm mt-1">Select documents from the left panel to focus your search</p>
          </div>
        )}
        {messages.map((m) => (
          <div key={m.id} className={`flex ${m.sender === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[80%] ${m.sender === "user" ? "bg-indigo-600 text-white" : "bg-slate-100 text-slate-800"} rounded-lg p-3 shadow-sm`}>
              <div className="whitespace-pre-wrap">{m.text}</div>
              
              {m.error && (
                <div className="mt-2 p-2 bg-red-100 border border-red-200 rounded text-red-700 text-sm flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                  <span className="text-xs opacity-75">{m.error}</span>
                </div>
              )}
              
              {m.confidence && (
                <div className="mt-2 text-xs opacity-75">
                  Confidence: {(m.confidence * 100).toFixed(1)}%
                </div>
              )}
              
              {m.citations && m.citations.length > 0 && (
                <div className="mt-3 pt-2 border-t border-slate-200">
                  <div className="text-xs font-medium text-slate-600 mb-2">Citations:</div>
                  <div className="space-y-1">
                    {m.citations.map((citation, idx) => (
                      <div key={idx} className="text-xs bg-white rounded p-2 border border-slate-200">
                        <div className="font-medium text-slate-700 mb-1">
                          {citation.filename || `Source ${idx + 1}`}
                        </div>
                        <div className="text-slate-600 italic">
                          "{citation.content}"
                        </div>
                        {citation.page_number && (
                          <div className="text-slate-400 mt-1">
                            Page {citation.page_number}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {m.sources && m.sources.length > 0 && !m.citations && (
                <div className="mt-3 pt-2 border-t border-slate-200">
                  <div className="text-xs font-medium text-slate-600 mb-2">Sources:</div>
                  <div className="space-y-1">
                    {m.sources.map((source, idx) => (
                      <div key={idx} className="text-xs">
                        <a 
                          className="text-indigo-600 hover:text-indigo-800 hover:underline" 
                          href={`${API_BASE}/api/files/download/${source.collection}`} 
                          target="_blank" 
                          rel="noreferrer"
                        >
                          {(source.metadata && source.metadata.file_name) || source.collection}
                        </a>
                        {source.metadata && source.metadata.row_index !== undefined && (
                          <span className="ml-2 text-slate-400">(row: {source.metadata.row_index})</span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              <div className="text-xs opacity-50 mt-2">
                {new Date(m.timestamp).toLocaleTimeString()}
              </div>
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-slate-100 rounded-lg p-3 flex items-center gap-2">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-indigo-600"></div>
              <span className="text-sm text-slate-600">Thinking...</span>
            </div>
          </div>
        )}
      </div>

      <div className="p-4 border-t bg-slate-50 rounded-b-lg">
        <div className="flex gap-2">
          <input
            className="flex-1 border border-slate-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
            placeholder={loading ? "Please wait..." : "Ask a question about your documents..."}
            disabled={loading}
          />
          <button 
            onClick={handleSend} 
            disabled={loading || !input.trim()} 
            className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
          >
            <Send className="w-4 h-4" />
            Send
          </button>
        </div>
        {selectedFileIds.length > 0 && (
          <div className="mt-2 text-xs text-slate-500">
            Searching in {selectedFileIds.length} selected document{selectedFileIds.length > 1 ? 's' : ''}
          </div>
        )}
      </div>
    </div>
  );
}

export default function App() {
  const [files, setFiles] = useState([]);
  const [selectedIds, setSelectedIds] = useState([]);
  const [loading, setLoading] = useState(true);

  async function fetchFiles() {
    try {
      setLoading(true);
      const res = await fetch(`${API_BASE}/api/files/`);
      if (!res.ok) throw new Error("Failed to load files");
      const data = await res.json();
      setFiles(data);
    } catch (err) {
      console.error("Error fetching files:", err);
      // Don't show alert on initial load, just log the error
      if (files.length > 0) {
        alert("Could not fetch files: " + err.message);
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchFiles();
  }, []);

  function handleToggleSelect(id) {
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  async function handleDeleteFile(fileId, fileName) {
    // Better confirmation dialog
    const confirmMessage = `⚠️ Delete File Confirmation\n\nAre you sure you want to delete "${fileName}"?\n\nThis will:\n• Remove the file from storage\n• Delete all indexed content\n• Remove it from the vector database\n\nThis action cannot be undone.`;
    
    if (!confirm(confirmMessage)) {
      return;
    }

    // Show loading state
    setLoading(true);
    
    try {
      const response = await fetch(`${API_BASE}/api/files/${fileId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
        throw new Error(errorData.detail || errorData.message || `Delete failed with status ${response.status}`);
      }

      const result = await response.json();

      // Remove from selected IDs if it was selected
      setSelectedIds((prev) => prev.filter((id) => id !== fileId));
      
      // Refresh the file list
      await fetchFiles();
      
      // Success message
      console.log('File deleted successfully:', result.message);
      
      // Optional: Show a success toast instead of alert for better UX
      // For now, using alert but styled differently
      alert(`✅ Success!\n\n"${fileName}" has been deleted successfully.`);
      
    } catch (error) {
      console.error('Delete error:', error);
      alert(`❌ Delete Failed\n\nFailed to delete "${fileName}":\n${error.message}`);
    } finally {
      setLoading(false);
    }
  }

  if (loading && files.length === 0) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto mb-4"></div>
          <p className="text-slate-600">Loading application...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="p-6">
        <div className="max-w-7xl mx-auto space-y-6">
          {/* Header */}
          <div className="text-center">
            <h1 className="text-3xl font-bold text-slate-800 mb-2">Generic Data RAG Agent</h1>
            <p className="text-slate-600">Upload your documents and ask questions about their content</p>
          </div>

          {/* Upload Section */}
          <UploadBar onUploaded={() => fetchFiles()} />

          {/* Main Content Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2">
              <DocumentsList 
                files={files} 
                selectedIds={selectedIds} 
                onToggleSelect={handleToggleSelect} 
                onRefresh={fetchFiles}
                onDeleteFile={handleDeleteFile}
              />
            </div>
            <div className="lg:col-span-1">
              <ChatWindow selectedFileIds={selectedIds} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}