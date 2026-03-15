import os
from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from pinecone import Pinecone, ServerlessSpec

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def initialize_pinecone():
    pc = Pinecone(api_key=PINECONE_API_KEY)
    index_name = "dev-productivity"

    if index_name not in pc.list_indexes().names():
        pc.create_index(
            name=index_name,
            dimension=1536,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1")
        )
    return pc, index_name

def load_documents():
    docs_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'documents')
    loader = DirectoryLoader(docs_path, glob="*.txt", loader_cls=TextLoader)
    documents = loader.load()
    print(f"Loaded {len(documents)} documents")
    return documents

def chunk_documents(documents):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100
    )
    chunks = splitter.split_documents(documents)
    print(f"Created {len(chunks)} chunks")
    return chunks

def store_in_pinecone(chunks):
    pc, index_name = initialize_pinecone()
    embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
    index = pc.Index(index_name)

    texts = [chunk.page_content for chunk in chunks]
    metadatas = [chunk.metadata for chunk in chunks]

    embedding_vectors = embeddings.embed_documents(texts)

    vectors = []
    for i, (text, embedding, metadata) in enumerate(zip(texts, embedding_vectors, metadatas)):
        vectors.append({
            "id": f"chunk_{i}",
            "values": embedding,
            "metadata": {"text": text, **metadata}
        })

    index.upsert(vectors=vectors)
    print("Documents stored in Pinecone successfully!")
    return index

def search_similar(query, index, k=3):
    embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
    query_embedding = embeddings.embed_query(query)
    results = index.query(vector=query_embedding, top_k=k, include_metadata=True)
    return results

def build_rag_context(pr_metrics, commit_metrics, health_score):
    pc, index_name = initialize_pinecone()
    index = pc.Index(index_name)

    query = f"""
    Team health score {health_score}.
    PR review time {pr_metrics.get('avg_review_time_hours')} hours.
    Open PRs {pr_metrics.get('open_prs')}.
    """

    results = search_similar(query, index)
    context = "\n\n".join([match.metadata.get("text", "") for match in results.matches])
    return context

if __name__ == "__main__":
    print("Loading documents...")
    documents = load_documents()

    print("Chunking documents...")
    chunks = chunk_documents(documents)

    print("Storing in Pinecone...")
    index = store_in_pinecone(chunks)

    print("\nTesting search...")
    results = search_similar("PR review bottleneck burnout", index)
    print(f"\nFound {len(results.matches)} relevant chunks:")
    for i, match in enumerate(results.matches):
        print(f"\nChunk {i+1}:")
        print(match.metadata.get("text", "")[:200])