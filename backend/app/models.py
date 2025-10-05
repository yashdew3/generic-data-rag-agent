# backend/app/models.py
from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime

class FileMeta(BaseModel):
    id: str
    original_name: str
    stored_name: str
    content_type: Optional[str]
    size: int
    uploaded_at: str

class UploadResponse(BaseModel):
    success: bool
    files: List[FileMeta]

class ChatRequest(BaseModel):
    query: str
    top_k: int = 5
    file_ids: Optional[List[str]] = None

class Citation(BaseModel):
    """A single citation from a source document"""
    file_id: str
    file_name: str
    anchors: Optional[str] = None  # e.g., "row_index=15" or "page=3"
    snippet: Optional[str] = None  # The actual text that was cited
    confidence: Optional[float] = None  # Distance/similarity score

class StructuredAnswer(BaseModel):
    """Structured answer from Gemini with proper citations"""
    answer: str
    citations: List[Citation]

class ChatResponse(BaseModel):
    """Response from the chat endpoint with structured answer and metadata"""
    structured_answer: StructuredAnswer
    sources: List[Any]  # Raw retrieved sources for debugging
    gemini_used: bool
    latency_s: float
    query: str  # Echo back the query for frontend convenience
    conversation_id: Optional[str] = None  # Set when using history endpoints

class ConversationTurn(BaseModel):
    """A single turn in a conversation"""
    query: str
    response: ChatResponse
    timestamp: datetime

class ConversationHistory(BaseModel):
    """Complete conversation history"""
    conversation_id: str
    turns: List[ConversationTurn]
    created_at: datetime
    updated_at: datetime

class CreateConversationResponse(BaseModel):
    """Response when creating a new conversation"""
    conversation_id: str
    created_at: datetime

class ConversationSummary(BaseModel):
    """Summary of a conversation for listing"""
    conversation_id: str
    created_at: datetime
    updated_at: datetime
    turn_count: int
    last_query: str

class ChatWithHistoryRequest(BaseModel):
    """Chat request that includes conversation history tracking"""
    query: str
    top_k: int = 5
    file_ids: Optional[List[str]] = None
    conversation_id: Optional[str] = None  # If provided, add to existing conversation
