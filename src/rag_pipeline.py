import os
from functools import lru_cache

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pinecone import Pinecone, ServerlessSpec

from src.observability import retriever

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

INDEX_NAME = "dev-productivity"
DOCS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "documents")
# Pinned on purpose: query vectors must come from the same model the index was built with,
# and the library's default could change in a future release.
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002")


@lru_cache(maxsize=1)
def _embeddings():
    return OpenAIEmbeddings(model=EMBEDDING_MODEL, openai_api_key=os.getenv("OPENAI_API_KEY"))


@lru_cache(maxsize=1)
def _index():
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    if INDEX_NAME not in pc.list_indexes().names():
        # Creating an empty index here would silently give every report zero history.
        raise RuntimeError(f"Pinecone index '{INDEX_NAME}' is missing. Run: python -m src.rag_pipeline")
    return pc.Index(INDEX_NAME)


def _title_for(path, text):
    # The first line of each document is its title, e.g. "INCIDENT REPORT - MARCH 2024".
    first = text.strip().splitlines()[0] if text.strip() else os.path.basename(path)
    return first.title()


def build_index():
    """Loads documents/*.txt, splits them and stores them in Pinecone. Run once after adding documents."""
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    if INDEX_NAME not in pc.list_indexes().names():
        pc.create_index(name=INDEX_NAME, dimension=1536, metric="cosine",
                        spec=ServerlessSpec(cloud="aws", region="us-east-1"))
    index = pc.Index(INDEX_NAME)

    # Plain file reading: langchain-community's loaders were only used for this and the
    # package is being retired.
    documents = []
    for name in sorted(os.listdir(DOCS_PATH)):
        if name.endswith(".txt"):
            path = os.path.join(DOCS_PATH, name)
            with open(path, encoding="utf-8") as f:
                documents.append(Document(page_content=f.read(), metadata={"source": path}))
    chunks = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100).split_documents(documents)
    titles = {d.metadata["source"]: _title_for(d.metadata["source"], d.page_content) for d in documents}

    texts = [c.page_content for c in chunks]
    vectors = _embeddings().embed_documents(texts)
    # documents/ is the source of truth, so clear old chunks (including the first
    # version's "chunk_0" style ids) instead of leaving duplicates behind.
    try:
        index.delete(delete_all=True)
    except Exception:
        pass  # a brand-new index has nothing to delete
    index.upsert(vectors=[{
        "id": f"{os.path.basename(c.metadata['source'])}#{i}",
        "values": v,
        "metadata": {"text": t, "source": os.path.basename(c.metadata["source"]), "title": titles[c.metadata["source"]]},
    } for i, (c, t, v) in enumerate(zip(chunks, texts, vectors))])
    print(f"Stored {len(chunks)} chunks from {len(documents)} documents in Pinecone")


@retriever
def retrieve_history(signals, k=4):
    """Finds the past incidents and retros most like this week's signals.

    Returns one entry per source document (best-matching chunk), each with a match score,
    so the report can cite "[1] Payments outage report, 89% match".
    """
    query = " ".join(signals) if signals else "Healthy team, fast reviews, balanced workload."
    results = _index().query(vector=_embeddings().embed_query(query), top_k=k, include_metadata=True)

    by_source = {}
    for match in results.matches:
        meta = match.metadata or {}
        source = os.path.basename(meta.get("source") or match.id.split("#")[0])
        if source not in by_source:
            by_source[source] = {
                "title": meta.get("title") or _title_for(source, meta.get("text", "")),
                "source": source,
                "text": meta.get("text", ""),
                "match": round(match.score * 100),
            }
        else:
            by_source[source]["text"] += "\n" + meta.get("text", "")
    return list(by_source.values())


if __name__ == "__main__":
    build_index()
    for doc in retrieve_history(["One reviewer handles most reviews and PRs wait over 48 hours."]):
        print(f"{doc['match']}%  {doc['title']}")
