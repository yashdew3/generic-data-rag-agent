# backend/app/routers/history.py
"""
Conversation history API endpoints.
"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional
from ..models import (
    ConversationHistory, 
    CreateConversationResponse, 
    ConversationSummary,
    ChatWithHistoryRequest,
    ChatResponse
)
from ..services.history import history_manager
from ..services.retriever import answer_query_structured
from ..models import StructuredAnswer, Citation
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/conversations", response_model=CreateConversationResponse)
async def create_conversation():
    """Create a new conversation"""
    try:
        conversation_id = history_manager.create_conversation()
        conversation = history_manager.get_conversation(conversation_id)
        
        return CreateConversationResponse(
            conversation_id=conversation_id,
            created_at=conversation.created_at
        )
    except Exception as exc:
        logger.exception("Error creating conversation: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/conversations", response_model=List[ConversationSummary])
async def list_conversations(limit: int = 50):
    """List recent conversations"""
    try:
        conversations = history_manager.list_conversations(limit=limit)
        return [ConversationSummary(**conv) for conv in conversations]
    except Exception as exc:
        logger.exception("Error listing conversations: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/conversations/{conversation_id}", response_model=ConversationHistory)
async def get_conversation(conversation_id: str):
    """Get full conversation history"""
    try:
        conversation = history_manager.get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return conversation
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error retrieving conversation: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation"""
    try:
        success = history_manager.delete_conversation(conversation_id)
        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return {"message": "Conversation deleted successfully"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error deleting conversation: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

@router.post("/chat-with-history", response_model=ChatResponse)
async def chat_with_history(req: ChatWithHistoryRequest):
    """
    Chat endpoint that automatically manages conversation history.
    Creates a new conversation if conversation_id is not provided.
    """
    try:
        # Get structured answer
        result = answer_query_structured(req.query, top_k=req.top_k or 5, file_ids=req.file_ids)
        
        # Convert to proper Pydantic models
        structured_answer_data = result["structured_answer"]
        citations = [
            Citation(
                file_id=cit["file_id"],
                file_name=cit["file_name"],
                anchors=cit.get("anchors"),
                snippet=cit.get("snippet"),
                confidence=cit.get("confidence")
            )
            for cit in structured_answer_data.get("citations", [])
        ]
        
        structured_answer = StructuredAnswer(
            answer=structured_answer_data["answer"],
            citations=citations
        )
        
        chat_response = ChatResponse(
            structured_answer=structured_answer,
            sources=result["sources"],
            gemini_used=result["gemini_used"],
            latency_s=result["latency_s"],
            query=result["query"]
        )
        
        # Handle conversation history
        conversation_id = req.conversation_id
        if not conversation_id:
            conversation_id = history_manager.create_conversation()
            chat_response.conversation_id = conversation_id  # Add conversation_id to response
        
        # Add turn to conversation history
        history_manager.add_turn(conversation_id, req.query, chat_response)
        
        return chat_response
        
    except Exception as exc:
        logger.exception("Chat with history endpoint error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))