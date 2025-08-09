from __future__ import annotations

import os
import json
from typing import List, Dict, Tuple
import faiss
import numpy as np
from docx import Document
from pypdf import PdfReader

from app.core.config import get_settings
from app.core.embeddings import embed_texts


_SOURCES_CACHE: List[Dict] | None = None


def _load_sources_list(ref_dir: str) -> List[Dict]:
    global _SOURCES_CACHE
    if _SOURCES_CACHE is not None:
        return _SOURCES_CACHE
    sources_path = os.path.join(ref_dir, "sources.json")
    if os.path.exists(sources_path):
        try:
            with open(sources_path, "r", encoding="utf-8") as f:
                _SOURCES_CACHE = json.load(f)
                return _SOURCES_CACHE
        except Exception:
            pass
    _SOURCES_CACHE = []
    return _SOURCES_CACHE


def _infer_source_url(path: str) -> str | None:
    # Try to map a local reference file to its original source URL using sources.json
    ref_dir = get_settings().references_dir
    sources = _load_sources_list(ref_dir)
    base = os.path.basename(path)
    name_no_ext, ext = os.path.splitext(base)
    # Heuristics: match by URL basename or by name stem for html→txt conversions
    for item in sources:
        url = item.get("url", "")
        if not url:
            continue
        url_base = os.path.basename(url.split("?")[0]).replace("%20", "_")
        if url_base and (url_base == base or url_base == name_no_ext or url_base.startswith(name_no_ext)):
            return url
    return None


def _read_txt(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def _read_docx(path: str) -> str:
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs)


def _is_pdf(path: str) -> bool:
    try:
        with open(path, "rb") as f:
            head = f.read(5)
            return head == b"%PDF-"
    except Exception:
        return False


def _read_pdf(path: str) -> str:
    if not _is_pdf(path):
        return ""
    reader = PdfReader(path)
    parts: List[str] = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception:
            continue
    return "\n".join(parts)


def _tokenize_words(text: str) -> List[str]:
    return text.split()


def _chunk_text(text: str, max_tokens: int, overlap: int) -> List[str]:
    words = _tokenize_words(text)
    if not words:
        return []
    chunks: List[str] = []
    start = 0
    while start < len(words):
        end = min(start + max_tokens, len(words))
        chunk = " ".join(words[start:end]).strip()
        if chunk:
            chunks.append(chunk)
        if end == len(words):
            break
        start = max(0, end - overlap)
    return chunks


def load_reference_files(ref_dir: str) -> List[Tuple[str, str]]:
    items: List[Tuple[str, str]] = []
    for root, _, files in os.walk(ref_dir):
        for name in files:
            path = os.path.join(root, name)
            ext = os.path.splitext(name)[1].lower()
            try:
                if ext in {".txt"}:
                    text = _read_txt(path)
                elif ext in {".docx"}:
                    text = _read_docx(path)
                elif ext in {".pdf"}:
                    text = _read_pdf(path)
                else:
                    continue
                if text.strip():
                    items.append((path, text))
            except Exception:
                continue
    return items


def build_faiss_index(chunks: List[str]) -> faiss.IndexFlatIP:
    vectors = embed_texts(chunks)
    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)
    return index


def ingest_references() -> None:
    settings = get_settings()
    os.makedirs(settings.faiss_index_dir, exist_ok=True)

    items = load_reference_files(settings.references_dir)
    max_tokens = settings.max_chunk_tokens
    overlap = settings.chunk_overlap

    chunks: List[str] = []
    meta: List[Dict] = []
    for path, text in items:
        parts = _chunk_text(text, max_tokens=max_tokens, overlap=overlap)
        for i, part in enumerate(parts):
            chunks.append(part)
            meta.append({
                "source_path": path,
                "chunk_index": i,
                # Store human-friendly title and source URL if available
                "title": os.path.basename(path),
                "source_url": _infer_source_url(path),
            })

    if not chunks:
        raise RuntimeError("No reference chunks produced. Ensure references/ has .txt, .pdf, or .docx files.")

    vectors = embed_texts(chunks)
    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)

    faiss.write_index(index, os.path.join(settings.faiss_index_dir, "index.faiss"))
    np.save(os.path.join(settings.faiss_index_dir, "embeddings.npy"), vectors)
    with open(os.path.join(settings.faiss_index_dir, "chunks.json"), "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    with open(os.path.join(settings.faiss_index_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"Indexed {len(chunks)} chunks → {settings.faiss_index_dir}")


if __name__ == "__main__":
    ingest_references()
