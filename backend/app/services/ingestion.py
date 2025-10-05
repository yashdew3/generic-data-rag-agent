# backend/app/services/ingestion.py
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd
import pdfplumber
import math
import re
import logging
import pandas as pd

logger = logging.getLogger(__name__)

# --- helpers ---------------------------------------------------------------

def _row_to_text(row: pd.Series, max_preview_chars: int = 1000) -> str:
    """
    Convert a single pandas row to a compact textual summary.
    Example: "Row 12: Player=Messi | Goals=10 | Assists=5 | Season=2021"
    """
    pieces = []
    for col, val in row.items():
        # convert nan to empty
        if pd.isna(val):
            continue
        text_val = str(val)
        # shorten very long text cells for preview
        if len(text_val) > max_preview_chars:
            text_val = text_val[: max_preview_chars - 3] + "..."
        pieces.append(f"{col}={text_val}")
    return " | ".join(pieces) if pieces else ""

def _chunk_text(text: str, max_words: int = 250) -> List[str]:
    """
    Naive text chunker based on word counts.
    Returns list of chunks where each chunk has ~max_words words or less.
    """
    words = re.split(r"\s+", text.strip())
    if not words:
        return []
    chunks = []
    for i in range(0, len(words), max_words):
        chunk = " ".join(words[i : i + max_words]).strip()
        if chunk:
            chunks.append(chunk)
    return chunks

# --- public functions -----------------------------------------------------

def parse_csv_or_excel(path: Path, file_id: str) -> List[Dict[str, Any]]:
    """
    Parse CSV or Excel file into a list of chunk dicts.
    Each chunk dict: { "id", "text", "meta": {file_name, file_id, row_index, columns, original_row} }
    Supports multi-sheet Excel (sheet name included in metadata).
    """
    path = Path(path)
    logger.info("Parsing CSV/Excel: %s", path)
    rows_out = []
    suffix = path.suffix.lower()

    if suffix in [".xls", ".xlsx", ".xlsm", ".xlsb"]:
        # read all sheets
        xls = pd.read_excel(path, sheet_name=None, engine="openpyxl")
        for sheet_name, df in xls.items():
            if df.empty:
                continue
            # ensure columns are strings
            df.columns = [str(c) for c in df.columns]
            for idx, row in df.iterrows():
                text = _row_to_text(row)
                if not text:
                    continue
                chunk_id = f"{file_id}::sheet={sheet_name}::row={idx}"
                meta = {
                    "file_name": path.name,
                    "file_id": file_id,
                    "sheet": sheet_name,
                    "row_index": int(idx),
                    "columns": list(df.columns),
                    "original_row": row.to_dict(),
                }
                rows_out.append({"id": chunk_id, "text": text, "meta": meta})
    else:
        # assume CSV or text-like
        df = pd.read_csv(path)
        if df.empty:
            return rows_out
        df.columns = [str(c) for c in df.columns]
        for idx, row in df.iterrows():
            text = _row_to_text(row)
            if not text:
                continue
            chunk_id = f"{file_id}::row={idx}"
            meta = {
                "file_name": path.name,
                "file_id": file_id,
                "row_index": int(idx),
                "columns": list(df.columns),
                "original_row": row.to_dict(),
            }
            rows_out.append({"id": chunk_id, "text": text, "meta": meta})

    logger.info("Parsed %d chunks from %s", len(rows_out), path.name)
    return rows_out

def parse_pdf(path: Path, file_id: str) -> List[Dict[str, Any]]:
    """
    Parse PDF: extract table rows and text paragraphs.
    Convert each table row into a chunk and chunk textual paragraphs into multiple chunks.
    """
    path = Path(path)
    logger.info("Parsing PDF: %s", path)
    chunks = []
    with pdfplumber.open(path) as pdf:
        for pageno, page in enumerate(pdf.pages):
            # extract tables (if any)
            try:
                page_tables = page.extract_tables()
            except Exception as exc:
                logger.debug("pdfplumber extract_tables failed on page %s: %s", pageno, exc)
                page_tables = []

            if page_tables:
                for t_idx, table in enumerate(page_tables):
                    # table is list of rows (list)
                    # create DataFrame for nice row handling
                    try:
                        df = pd.DataFrame(table)
                        # try to promote first row as header if it looks like header
                        if df.shape[0] >= 2 and all(isinstance(c, str) for c in df.iloc[0].tolist()):
                            df.columns = df.iloc[0].tolist()
                            df = df.iloc[1:].reset_index(drop=True)
                        else:
                            df.columns = [f"col_{i}" for i in range(df.shape[1])]
                        for idx, row in df.iterrows():
                            text = _row_to_text(row)
                            if not text:
                                continue
                            chunk_id = f"{file_id}::pdf::page={pageno}::table={t_idx}::row={idx}"
                            meta = {
                                "file_name": path.name,
                                "file_id": file_id,
                                "page": int(pageno),
                                "table": int(t_idx),
                                "row_index": int(idx),
                                "columns": list(df.columns),
                                "original_row": row.to_dict(),
                            }
                            chunks.append({"id": chunk_id, "text": text, "meta": meta})
                    except Exception as exc:
                        logger.debug("Failed building DataFrame from table: %s", exc)

            # fallback: extract page text and chunk it
            page_text = page.extract_text() or ""
            if page_text.strip():
                text_chunks = _chunk_text(page_text, max_words=200)
                for c_idx, c in enumerate(text_chunks):
                    chunk_id = f"{file_id}::pdf::page={pageno}::para={c_idx}"
                    meta = {
                        "file_name": path.name,
                        "file_id": file_id,
                        "page": int(pageno),
                        "paragraph_index": int(c_idx),
                    }
                    chunks.append({"id": chunk_id, "text": c, "meta": meta})

    logger.info("Parsed %d chunks from PDF %s", len(chunks), path.name)
    return chunks

def parse_csv_or_excel(path, file_id: str):
    if str(path).endswith(".csv"):
        df = pd.read_csv(path)
        sheets = {"Sheet1": df}
    elif str(path).endswith(".xls"):  # old Excel format
        xls = pd.read_excel(path, sheet_name=None, engine="xlrd")
        sheets = {sheet_name: data for sheet_name, data in xls.items()}
    elif str(path).endswith(".xlsx"):  # new Excel format
        xls = pd.read_excel(path, sheet_name=None, engine="openpyxl")
        sheets = {sheet_name: data for sheet_name, data in xls.items()}
    else:
        raise ValueError(f"Unsupported file type: {path}")

    chunks = []
    for sheet_name, df in sheets.items():
        for i, row in df.iterrows():
            text = " | ".join([f"{col}: {row[col]}" for col in df.columns if pd.notna(row[col])])
            chunks.append(f"[{sheet_name}] {text}")

    return chunks