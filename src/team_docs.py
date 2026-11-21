"""A team's own incident reports and retrospectives, kept in its own Pinecone namespace.

A team is just a long random id. Whoever has the team's link can add, list and
remove its documents, and analyses run from that link search the team's
documents instead of the samples. Nothing is shared between namespaces.
"""
import re
import secrets
from datetime import datetime, timezone
from io import BytesIO

from langchain_core.documents import Document
from pypdf import PdfReader

from src.rag_pipeline import _embeddings, _index, split_text

TEAM_ID = re.compile(r"^[A-Za-z0-9_-]{22}$")
DOC_ID = re.compile(r"^doc_[a-f0-9]{12}$")
MAX_DOCS = 25
MAX_FILE_BYTES = 2_000_000
MAX_CHARS = 60_000
MIN_CHARS = 40


class TeamDocError(Exception):
    """A problem worth showing the person as-is (too big, empty, unreadable)."""


def new_team_id():
    # 16 random bytes: about 3.4e38 possibilities, so a link can't be guessed.
    return secrets.token_urlsafe(16)


def is_team_id(team):
    return bool(team and TEAM_ID.match(team))


def text_from_file(filename, data):
    if len(data) > MAX_FILE_BYTES:
        raise TeamDocError("That file is over 2 MB. Try a shorter document, or paste just the important part.")
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        try:
            return "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(data)).pages)
        except Exception:
            raise TeamDocError("We couldn't read that PDF. If it's a scanned image, paste the text instead.")
    if name.endswith((".txt", ".md", ".markdown")):
        return data.decode("utf-8", errors="replace")
    raise TeamDocError("Upload a .txt, .md or .pdf file, or paste the text instead.")


def _ids(team, prefix="doc_"):
    ids = []
    for page in _index().list(prefix=prefix, namespace=team):
        ids.extend(getattr(page, "vectors", None) and [v.id for v in page.vectors] or list(page))
    return ids


def list_documents(team):
    """One entry per document: id, title, when it was added, and how many chunks it became."""
    chunks_by_doc = {}
    for vector_id in _ids(team):
        chunks_by_doc.setdefault(vector_id.split("#")[0], []).append(vector_id)
    if not chunks_by_doc:
        return []
    first_chunks = [f"{doc}#0" for doc in chunks_by_doc]
    fetched = _index().fetch(ids=first_chunks, namespace=team).vectors
    docs = []
    for doc, ids in chunks_by_doc.items():
        meta = (fetched.get(f"{doc}#0").metadata if fetched.get(f"{doc}#0") else None) or {}
        docs.append({"id": doc, "title": meta.get("title", "Untitled"), "added": meta.get("added", ""), "chunks": len(ids)})
    return sorted(docs, key=lambda d: d["added"], reverse=True)


def add_document(team, title, text):
    text = (text or "").strip()
    title = (title or "").strip()[:120] or text.splitlines()[0][:120] if text else ""
    if len(text) < MIN_CHARS:
        raise TeamDocError("That document is too short to be useful. Paste the full incident report or retro.")
    if len(text) > MAX_CHARS:
        raise TeamDocError(f"That document is over {MAX_CHARS:,} characters. Split it, or keep the summary and lessons learned.")
    if len(list_documents(team)) >= MAX_DOCS:
        raise TeamDocError(f"A team space can hold {MAX_DOCS} documents. Remove an old one to add another.")

    doc_id = f"doc_{secrets.token_hex(6)}"
    added = datetime.now(timezone.utc).isoformat(timespec="seconds")
    chunks = split_text([Document(page_content=text, metadata={"source": doc_id})])
    texts = [c.page_content for c in chunks]
    vectors = _embeddings().embed_documents(texts)
    _index().upsert(vectors=[{
        "id": f"{doc_id}#{i}",
        "values": v,
        "metadata": {"text": t, "source": doc_id, "title": title, "added": added},
    } for i, (t, v) in enumerate(zip(texts, vectors))], namespace=team)
    return {"id": doc_id, "title": title, "added": added, "chunks": len(texts)}


def delete_document(team, doc_id):
    if not DOC_ID.match(doc_id or ""):
        raise TeamDocError("That document doesn't exist.")
    ids = _ids(team, prefix=f"{doc_id}#")
    if ids:
        _index().delete(ids=ids, namespace=team)
    return len(ids)
