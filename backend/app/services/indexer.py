# backend/app/services/indexer.py

from typing import List, Dict, Any, Optional, Union, Iterable
from sentence_transformers import SentenceTransformer
import chromadb
from pathlib import Path
import logging
from .ingestion import parse_csv_or_excel, parse_pdf
from ..storage import get_file_path
import time
import math
import uuid
import re

logger = logging.getLogger(__name__)

# --- configuration ---------------------------------------------------------
CHROMA_PERSIST_DIR = Path("chroma_db")
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
EMBED_BATCH_SIZE = 128            # reasonable default for CPU; reduce if memory is tight
MAX_WORDS_PER_CHUNK = 250         # split any text longer than this
SENTENCE_TRANSFORMERS_DEVICE = "cpu"  # change if you have GPU; SB uses torch device autodetect

# --- singleton model/client holders ---------------------------------------
_embedding_model: Optional[SentenceTransformer] = None
_chroma_client: Optional[chromadb.PersistentClient] = None


def get_embedding_model() -> SentenceTransformer:
    """Load (once) sentence-transformers model."""
    global _embedding_model
    if _embedding_model is None:
        logger.info("Loading embedding model: %s", EMBEDDING_MODEL_NAME)
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _embedding_model


def get_chroma_client() -> chromadb.PersistentClient:
    """
    Initialize and return singleton chroma PersistentClient.
    Uses directory CHROMA_PERSIST_DIR for persistence.
    """
    global _chroma_client
    if _chroma_client is None:
        CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)
        logger.info("Initializing Chroma PersistentClient at %s", CHROMA_PERSIST_DIR)
        # modern API
        _chroma_client = chromadb.PersistentClient(path=str(CHROMA_PERSIST_DIR))
    return _chroma_client


# --- text utilities --------------------------------------------------------

def _chunk_text(text: str, max_words: int = MAX_WORDS_PER_CHUNK) -> List[str]:
    """Split text into word-based chunks of ~max_words each."""
    words = re.split(r"\s+", text.strip())
    if not words:
        return []
    chunks = []
    for i in range(0, len(words), max_words):
        chunk = " ".join(words[i : i + max_words]).strip()
        if chunk:
            chunks.append(chunk)
    return chunks


def _normalize_to_chunk_dicts(
    raw: Union[str, Dict[str, Any], Iterable[Union[str, Dict[str, Any]]]],
    file_id: str,
    default_meta: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Normalize ingestion output into List[{"id","text","meta"}].

    Accepts:
    - a single string -> split into chunks
    - a list of strings -> each becomes a chunk
    - a list of dicts -> expects each dict to contain 'text' or similar; will attempt to locate text
    - a single dict -> wrapped as list (and normalized)
    """
    default_meta = default_meta or {}
    out: List[Dict[str, Any]] = []

    # Helper to extract text from a dict item
    def _extract_text_from_dict(d: Dict[str, Any]) -> str:
        # common keys that might hold the textual content
        for key in ("text", "content", "document", "row_text", "chunk", "excerpt"):
            v = d.get(key)
            if isinstance(v, str) and v.strip():
                return v.strip()
        # fallback: attempt to stringify certain fields (like original_row)
        if "original_row" in d and isinstance(d["original_row"], (dict, list)):
            try:
                # Make a compact representation
                kvs = []
                if isinstance(d["original_row"], dict):
                    for k, val in d["original_row"].items():
                        if val is None:
                            continue
                        kvs.append(f"{k}={val}")
                else:
                    kvs = [str(x) for x in d["original_row"]]
                return " | ".join(kvs)
            except Exception:
                pass
        # last resort: join all string values in dict
        pieces = []
        for v in d.values():
            if isinstance(v, str) and v.strip():
                pieces.append(v.strip())
        if pieces:
            return " | ".join(pieces)
        # no suitable text: stringify the dict (shortened)
        return str(d)

    # Normalize single string
    if isinstance(raw, str):
        chunks = _chunk_text(raw, max_words=MAX_WORDS_PER_CHUNK)
        for idx, t in enumerate(chunks):
            out.append({"id": f"{file_id}::txt::{idx}", "text": t, "meta": {**default_meta}})
        return out

    # Normalize single dict
    if isinstance(raw, dict):
        text = _extract_text_from_dict(raw)
        chunks = _chunk_text(text, max_words=MAX_WORDS_PER_CHUNK)
        for idx, t in enumerate(chunks):
            meta = raw.get("meta", {}) if isinstance(raw.get("meta", {}), dict) else {}
            # merge default_meta but let raw meta override
            merged_meta = {**default_meta, **meta}
            out.append({"id": raw.get("id", f"{file_id}::item::{idx}"), "text": t, "meta": merged_meta})
        return out

    # Assume iterable (list/tuple)
    if hasattr(raw, "__iter__"):
        for i, item in enumerate(raw):
            # str element
            if isinstance(item, str):
                chunks = _chunk_text(item, max_words=MAX_WORDS_PER_CHUNK)
                for idx, t in enumerate(chunks):
                    out.append({"id": f"{file_id}::list::{i}::{idx}", "text": t, "meta": dict(default_meta)})
                continue

            # dict element
            if isinstance(item, dict):
                text = _extract_text_from_dict(item)
                chunks = _chunk_text(text, max_words=MAX_WORDS_PER_CHUNK)
                for idx, t in enumerate(chunks):
                    meta = item.get("meta", {}) if isinstance(item.get("meta", {}), dict) else {}
                    merged_meta = {**default_meta, **meta}
                    # prefer existing id if present
                    chunk_id = item.get("id", f"{file_id}::list::{i}::{idx}")
                    out.append({"id": chunk_id, "text": t, "meta": merged_meta})
                continue

            # other types: stringify
            txt = str(item)
            chunks = _chunk_text(txt, max_words=MAX_WORDS_PER_CHUNK)
            for idx, t in enumerate(chunks):
                out.append({"id": f"{file_id}::list::{i}::{idx}", "text": t, "meta": dict(default_meta)})

        return out

    # If nothing matched, return empty
    return out


# --- indexing functions ---------------------------------------------------

def _batch_iterable(iterable: List[Any], batch_size: int) -> Iterable[List[Any]]:
    """Yield successive batches from the iterable."""
    for i in range(0, len(iterable), batch_size):
        yield iterable[i : i + batch_size]


def index_chunks(chunks: Union[List[Dict[str, Any]], str], collection_name: str):
    """
    Accept various chunk shapes (list[dict], list[str], or single str).
    Normalizes and indexes into Chroma.
    """
    if not chunks:
        logger.info("index_chunks: no chunks to index for %s", collection_name)
        return

    # If user passed a list/dict/str of chunks, normalize to list-of-dicts
    normalized = _normalize_to_chunk_dicts(chunks, file_id=collection_name, default_meta={"collection": collection_name})
    if not normalized:
        logger.info("index_chunks: normalization resulted in 0 chunks for %s", collection_name)
        return

    client = get_chroma_client()

    # create or get collection. Use try/except defensive approach for different Chroma versions.
    try:
        coll = client.get_collection(collection_name)
    except Exception:
        try:
            coll = client.create_collection(collection_name)
        except Exception as exc:
            logger.exception("Failed to create/get chroma collection %s: %s", collection_name, exc)
            raise

    texts = [c["text"] for c in normalized]
    ids = [c.get("id", str(uuid.uuid4())) for c in normalized]
    metadatas = [c.get("meta", {}) for c in normalized]

    # embed in batches to avoid memory spikes
    model = get_embedding_model()
    logger.info("Embedding %d chunks for collection %s (batch_size=%d)", len(texts), collection_name, EMBED_BATCH_SIZE)

    all_embeddings = []
    for batch_idx, batch in enumerate(_batch_iterable(texts, EMBED_BATCH_SIZE)):
        logger.info("Embedding batch %d (%d items)", batch_idx + 1, len(batch))
        emb = model.encode(batch, show_progress_bar=False, convert_to_numpy=True)
        # emb: numpy array shape (n, dim)
        all_embeddings.extend(emb.tolist())

    # final length check
    if len(all_embeddings) != len(texts):
        logger.warning("Embedding length mismatch: got %d embeddings for %d texts", len(all_embeddings), len(texts))

    # add to Chroma. Some Chroma versions expect numpy arrays or lists.
    try:
        logger.info("Adding %d embeddings to Chroma collection %s", len(all_embeddings), collection_name)
        coll.add(ids=ids, documents=texts, metadatas=metadatas, embeddings=all_embeddings)
        # persist if supported by client
        try:
            client.persist()
        except Exception:
            # some clients persist automatically or don't implement persist
            pass
    except Exception as exc:
        logger.exception("Failed to add embeddings to chroma collection %s: %s", collection_name, exc)
        raise

    logger.info("Indexed %d chunks into collection %s", len(ids), collection_name)


# --- top-level file processing --------------------------------------------

def process_and_index_file(file_id: str):
    """
    Locate the uploaded file given file_id, parse it into chunks via ingestion
    helpers and index into a Chroma collection named after file_id.
    This function is safe to call in FastAPI BackgroundTasks.
    """
    logger.info("Start processing file_id=%s", file_id)
    path = get_file_path(file_id)
    if path is None:
        logger.error("process_and_index_file: file not found for id=%s", file_id)
        return

    suffix = path.suffix.lower()
    start_ts = time.time()
    try:
        # call ingestion based on suffix; the ingestion functions can return:
        # - list[dict], list[str], dict, or str
        if suffix in [".csv", ".txt"]:
            raw_chunks = parse_csv_or_excel(path, file_id)
        elif suffix in [".xls", ".xlsx", ".xlsm", ".xlsb"]:
            raw_chunks = parse_csv_or_excel(path, file_id)
        elif suffix == ".pdf":
            raw_chunks = parse_pdf(path, file_id)
        else:
            # fallback: try csv/excel then raw text
            try:
                raw_chunks = parse_csv_or_excel(path, file_id)
            except Exception:
                raw_text = path.read_text(encoding="utf-8", errors="ignore")
                raw_chunks = raw_text

        # defensive: ensure normalized shape and index
        index_chunks(raw_chunks, collection_name=file_id)
        elapsed = time.time() - start_ts
        logger.info("Finished indexing file_id=%s; elapsed=%.2fs", file_id, elapsed)
    except Exception as exc:
        logger.exception("Error while processing/indexing file %s: %s", path, exc)


def delete_file_from_index(file_id: str):
    """
    Delete a file's collection from the Chroma vector index.
    This removes all chunks that were indexed for the given file_id.
    """
    try:
        client = get_chroma_client()
        
        # Check if collection exists
        try:
            collection = client.get_collection(file_id)
            logger.info(f"Found collection {file_id}, deleting...")
            
            # Delete the entire collection
            client.delete_collection(file_id)
            logger.info(f"Successfully deleted collection {file_id} from vector index")
            
            # Persist changes if supported
            try:
                client.persist()
            except Exception:
                # Some clients persist automatically
                pass
                
        except Exception as e:
            # Collection might not exist, which is fine
            logger.info(f"Collection {file_id} not found in index (may not have been indexed yet): {e}")
            
    except Exception as e:
        logger.error(f"Error deleting file {file_id} from index: {e}")
        raise


# --- end of file ----------------------------------------------------------
