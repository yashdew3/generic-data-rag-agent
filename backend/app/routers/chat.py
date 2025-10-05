# backend/app/routers/chat.py
from fastapi import APIRouter, HTTPException
from ..models import ChatRequest, ChatResponse, StructuredAnswer, Citation
from ..services.retriever import answer_query_structured
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    Chat endpoint using Gemini-backed structured retriever QA.
    - req.query: the user question
    - req.top_k: number of retrieved chunks (default 5)
    - req.file_ids: optional list of file_ids (to limit search)
    
    Returns structured response with answer, citations, and metadata.
    """
    try:
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
        
        response = ChatResponse(
            structured_answer=structured_answer,
            sources=result["sources"],
            gemini_used=result["gemini_used"],
            latency_s=result["latency_s"],
            query=result["query"]
        )
        
        # Clean success logging
        logger.info(f"Chat query processed - Gemini: {result['gemini_used']}, Citations: {len(citations)}, Time: {result['latency_s']:.2f}s")
        return response
        
    except Exception as exc:
        logger.error(f"Chat endpoint error: {type(exc).__name__}")
        raise HTTPException(status_code=500, detail="Internal server error")
