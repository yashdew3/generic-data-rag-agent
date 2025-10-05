# backend/app/services/retriever.py
"""
Retriever + Gemini QA chain.

- Queries Chroma collections (by file_id or across all collections).
- Builds a compact prompt containing retrieved snippets + source labels.
- Calls Google Gemini (via the Google GenAI SDK) to generate the final answer.
- Graceful fallback: if Gemini API key or SDK is not available, returns a safe concatenation
  of retrieved snippets (so you can validate retrieval without calling the API).
"""

import os
import time
import logging
from typing import List, Dict, Any, Optional

from ..services.indexer import get_chroma_client  # uses chroma PersistentClient
from ..core.config import settings
# NOTE: get_embedding_model is NOT needed here; indexing already produced embeddings.

logger = logging.getLogger(__name__)

# configurable via settings
GEMINI_API_KEY = settings.GEMINI_API_KEY
GEMINI_MODEL = settings.GEMINI_MODEL
GEMINI_MAX_CONTEXT_CHARS = settings.GEMINI_MAX_CONTEXT_CHARS
DEFAULT_TOP_K = settings.RETRIEVER_TOP_K

# try to import Google GenAI SDK (official client)
try:
    import google.generativeai as genai
    _GENAI_AVAILABLE = True
except Exception:
    genai = None  # type: ignore
    _GENAI_AVAILABLE = False

# ---------- Chroma retrieval utilities ------------------------------------

def _list_all_collections(client) -> List[str]:
    """
    Return list of collection names. Different chroma versions return list objects differently,
    so be defensive.
    """
    try:
        cols = client.list_collections()
        names: List[str] = []
        for c in cols:
            if isinstance(c, dict) and "name" in c:
                names.append(c["name"])
            elif hasattr(c, "name"):
                names.append(c.name)
            else:
                names.append(str(c))
        return names
    except Exception as exc:
        logger.exception("Failed to list chroma collections: %s", exc)
        return []

def _query_collection(client, collection_name: str, query: str, top_k: int) -> List[Dict[str, Any]]:
    """
    Query a single Chroma collection. Returns a list of result dicts:
      { id, document, metadata, distance, collection }
    """
    try:
        coll = client.get_collection(collection_name)
    except Exception as exc:
        logger.debug("Collection %s not found: %s", collection_name, exc)
        return []

    try:
        # Query with include parameters that are supported by the current ChromaDB version
        qres = coll.query(query_texts=[query], n_results=top_k, include=["documents", "metadatas", "distances"])
        
        # Extract results - note that ids are always returned by ChromaDB even if not in include
        docs = qres.get("documents", [[]])[0]
        metas = qres.get("metadatas", [[]])[0]
        dists = qres.get("distances", [[]])[0]
        
        # Try to get ids if available in response
        ids = qres.get("ids", [None] * len(docs))
        if isinstance(ids, list) and len(ids) > 0 and isinstance(ids[0], list):
            ids = ids[0]
        
        out = []
        for i in range(len(docs)):
            out.append({
                "id": ids[i] if i < len(ids) else f"doc_{i}",
                "document": docs[i],
                "metadata": metas[i] if i < len(metas) else {},
                "distance": dists[i] if i < len(dists) else None,
                "collection": collection_name,
            })
        return out
    except Exception as exc:
        logger.exception("Chroma query failed for %s: %s", collection_name, exc)
        return []

def retrieve_top_k(query: str, top_k: int = DEFAULT_TOP_K, file_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Retrieve top_k results across the provided file_ids (chroma collections).
    If file_ids is None, search across all collections.
    Returns deduplicated results sorted by distance (ascending).
    """
    client = get_chroma_client()
    target_collections = file_ids or _list_all_collections(client)
    logger.debug("Searching %d collections for top_k=%d", len(target_collections), top_k)

    all_results: List[Dict[str, Any]] = []
    for coll_name in target_collections:
        try:
            res = _query_collection(client, coll_name, query, top_k)
            for r in res:
                if r.get("distance") is None:
                    r["distance"] = float("inf")
                all_results.append(r)
        except Exception as exc:
            logger.debug("Error querying collection %s: %s", coll_name, exc)

    # sort & dedupe
    all_results.sort(key=lambda x: x.get("distance", float("inf")))
    seen = set()
    deduped: List[Dict[str, Any]] = []
    for r in all_results:
        key = (r.get("collection"), r.get("id"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)
        if len(deduped) >= top_k:
            break

    logger.debug("retrieve_top_k returning %d docs", len(deduped))
    return deduped

# ---------- prompt construction -------------------------------------------

def _build_structured_prompt(query: str, retrieved: List[Dict[str, Any]], max_chars: int = GEMINI_MAX_CONTEXT_CHARS) -> str:
    """
    Build a structured prompt for JSON response with proper citations.
    """
    system_instruction = """You are a data analysis assistant. Respond ONLY with valid JSON.

REQUIRED JSON FORMAT (no extra text):
{
  "answer": "Complete answer based on the provided data",
  "citations": [
    {
      "file_id": "exact_file_id_from_source",
      "file_name": "exact_filename_from_source",
      "anchors": "specific_location_info",
      "snippet": "relevant_text_under_100_chars",
      "confidence": 0.95
    }
  ]
}

RULES:
- Answer must be informative and complete
- Include citations for every fact mentioned
- Use exact file_id and file_name from SOURCE entries
- Keep snippets under 100 characters
- Confidence: 0.0-1.0 based on relevance
- If no data matches query: empty citations array
- Output must be valid JSON only"""

    # Build context with structured source information
    ctx_parts = []
    total = 0
    for r in retrieved:
        doc = r.get("document") or ""
        meta = r.get("metadata") or {}
        file_id = r.get("collection", "unknown")
        file_name = meta.get("file_name", file_id)
        
        # Collect anchor information
        anchors = []
        for k in ("sheet", "row_index", "page", "paragraph_index"):
            if k in meta:
                anchors.append(f"{k}={meta[k]}")
        anchor_text = ", ".join(anchors) if anchors else ""
        
        # Format: SOURCE[file_id|file_name|anchors]: content
        piece = f"SOURCE[{file_id}|{file_name}|{anchor_text}]: {doc}"
        if total + len(piece) > max_chars:
            break
        ctx_parts.append(piece)
        total += len(piece)

    context = "\n\n".join(ctx_parts) if ctx_parts else "No relevant data available."
    prompt = f"{system_instruction}\n\nCONTEXT:\n{context}\n\nQUESTION: {query}\n\nProvide your response as valid JSON:"
    return prompt

# ---------- Gemini call ---------------------------------------------------

def _configure_genai():
    """
    Configure genai client if available and set API key.
    """
    if not _GENAI_AVAILABLE:
        raise RuntimeError("Google GenAI SDK (google-generativeai) is not installed.")
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not configured")
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        return genai
    except Exception as exc:
        logger.exception("Failed to configure genai client: %s", exc)
        raise

def call_gemini_structured(prompt: str, model: str = GEMINI_MODEL, max_output_tokens: int = 1024, temperature: float = 0.0) -> Dict[str, Any]:
    """
    Call Gemini via the Google GenAI SDK, returning structured JSON output.
    Robust JSON parsing with multiple fallback strategies.
    """
    if not _GENAI_AVAILABLE:
        raise RuntimeError("Google GenAI SDK not installed; install google-generativeai package.")

    _configure_genai()

    try:
        # Create the model with JSON response format
        model_instance = genai.GenerativeModel(
            model,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=max_output_tokens,
                temperature=temperature,
                response_mime_type="application/json"
            )
        )
        
        # Generate structured content
        response = model_instance.generate_content(prompt)
        response_text = response.text.strip()
        
        # Multiple JSON parsing strategies
        return _parse_json_response(response_text)
        
    except Exception as exc:
        logger.debug(f"Gemini structured call failed: {exc}")  # Reduced to debug level
        raise

def _parse_json_response(text: str) -> Dict[str, Any]:
    """
    Robust JSON parsing with multiple fallback strategies.
    """
    import json
    import re
    
    # Strategy 1: Direct parsing
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Strategy 2: Remove markdown code blocks
    cleaned_text = text
    if cleaned_text.startswith('```json'):
        cleaned_text = cleaned_text[7:]
    elif cleaned_text.startswith('```'):
        cleaned_text = cleaned_text[3:]
    
    if cleaned_text.endswith('```'):
        cleaned_text = cleaned_text[:-3]
    
    try:
        return json.loads(cleaned_text.strip())
    except json.JSONDecodeError:
        pass
    
    # Strategy 3: Extract JSON from mixed content
    json_pattern = r'\{.*\}'
    json_match = re.search(json_pattern, text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    
    # Strategy 4: Fix common JSON issues
    try:
        # Fix unterminated strings by finding the last complete JSON object
        fixed_text = _fix_unterminated_json(text)
        return json.loads(fixed_text)
    except json.JSONDecodeError:
        pass
    
    # Strategy 5: Create minimal valid JSON from content
    return _create_fallback_json(text)

def _fix_unterminated_json(text: str) -> str:
    """
    Attempt to fix unterminated JSON strings.
    """
    # Find the last properly closed brace
    brace_count = 0
    last_valid_pos = -1
    
    for i, char in enumerate(text):
        if char == '{':
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0:
                last_valid_pos = i + 1
    
    if last_valid_pos > 0:
        return text[:last_valid_pos]
    
    return text

def _create_fallback_json(text: str) -> Dict[str, Any]:
    """
    Create a valid JSON response when parsing fails completely.
    """
    # Try to extract answer content
    answer = text[:500] + "..." if len(text) > 500 else text
    
    return {
        "answer": f"I can provide information based on the data, though there was a formatting issue with the structured response: {answer}",
        "citations": []
    }

# ---------- public QA function --------------------------------------------

def answer_query_structured(query: str, top_k: int = DEFAULT_TOP_K, file_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    High-level structured QA function with proper citations.
    Returns:
      {
        "structured_answer": {
          "answer": str,
          "citations": [ {file_id, file_name, anchors, snippet, confidence} ]
        },
        "sources": [ {collection, id, metadata, document, distance} ],
        "gemini_used": bool,
        "latency_s": float,
        "query": str
      }
    """
    start = time.time()
    retrieved = retrieve_top_k(query, top_k=top_k, file_ids=file_ids)
    prompt = _build_structured_prompt(query, retrieved)

    gemini_used = False
    structured_answer = None
    
    # Attempt to call Gemini for structured response
    try:
        if GEMINI_API_KEY and _GENAI_AVAILABLE:
            gemini_used = True
            structured_answer = call_gemini_structured(prompt, model=GEMINI_MODEL)
        else:
            logger.debug("Gemini SDK or API key not configured; using fallback.")
    except Exception as exc:
        logger.debug(f"Gemini structured call failed, using fallback: {type(exc).__name__}")
        gemini_used = False
        structured_answer = None

    # Fallback: create structured response from retrieved docs
    if not structured_answer:
        if retrieved:
            citations = []
            answer_parts = []
            
            for r in retrieved:
                meta = r.get("metadata", {})
                file_id = r.get("collection", "unknown")
                file_name = meta.get("file_name", file_id)
                
                # Build anchors
                anchors = []
                for k in ("sheet", "row_index", "page", "paragraph_index"):
                    if k in meta:
                        anchors.append(f"{k}={meta[k]}")
                anchor_text = ", ".join(anchors) if anchors else ""
                
                # Add citation
                citations.append({
                    "file_id": file_id,
                    "file_name": file_name,
                    "anchors": anchor_text,
                    "snippet": r.get("document", "")[:200] + "..." if len(r.get("document", "")) > 200 else r.get("document", ""),
                    "confidence": 1.0 - (r.get("distance", 0) / 2.0) if r.get("distance") is not None else 0.5
                })
                
                answer_parts.append(f"According to {file_name}: {r.get('document', '')[:150]}...")

            structured_answer = {
                "answer": "Based on the retrieved documents:\n\n" + "\n\n".join(answer_parts[:3]),
                "citations": citations[:5]  # Limit citations
            }
        else:
            structured_answer = {
                "answer": "No relevant data found to answer the question.",
                "citations": []
            }

    elapsed = time.time() - start
    return {
        "structured_answer": structured_answer,
        "sources": retrieved,
        "gemini_used": gemini_used,
        "latency_s": elapsed,
        "query": query
    }

# Backward compatibility function
def answer_query(query: str, top_k: int = DEFAULT_TOP_K, file_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Legacy function for backward compatibility.
    """
    result = answer_query_structured(query, top_k, file_ids)
    return {
        "answer": result["structured_answer"]["answer"],
        "sources": result["sources"],
        "gemini_used": result["gemini_used"],
        "latency_s": result["latency_s"]
    }
