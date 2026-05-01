import os
import pickle
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# Paths configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORE_DIR = os.path.join(BASE_DIR, "store")

FAISS_PATH = os.path.join(STORE_DIR, "index.faiss")
BM25_PATH = os.path.join(STORE_DIR, "bm25.pkl")
CHUNKS_PATH = os.path.join(STORE_DIR, "chunks.pkl")

# Global state for indexes
faiss_index = None
bm25_model = None
chunks_data = None
embedding_model = None

def _init_retriever():
    """Load the models and indexes into memory on module initialization."""
    global faiss_index, bm25_model, chunks_data, embedding_model
    
    if not os.path.exists(STORE_DIR):
        print(f"Warning: Store directory {STORE_DIR} not found. Indexes not loaded.")
        return
        
    print("Initializing Hybrid Retriever...")
    print("Loading local embedding model (all-MiniLM-L6-v2)...")
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    
    print("Loading FAISS index...")
    if os.path.exists(FAISS_PATH):
        faiss_index = faiss.read_index(FAISS_PATH)
    else:
        print(f"FAISS index not found at {FAISS_PATH}")
    
    print("Loading BM25 index...")
    if os.path.exists(BM25_PATH):
        with open(BM25_PATH, "rb") as f:
            bm25_model = pickle.load(f)
    else:
        print(f"BM25 index not found at {BM25_PATH}")
        
    print("Loading chunks metadata...")
    if os.path.exists(CHUNKS_PATH):
        with open(CHUNKS_PATH, "rb") as f:
            chunks_data = pickle.load(f)
    else:
        print(f"Chunks data not found at {CHUNKS_PATH}")
        
    print("Retriever initialization complete.")

# Initialize upon module import
_init_retriever()

def reciprocal_rank_fusion(dense_indices, sparse_indices, k=60):
    """
    Combine indices using Reciprocal Rank Fusion.
    Score = 1 / (rank + k)
    Returns a list of tuples (chunk_index, rrf_score) sorted by score.
    """
    rrf_scores = {}
    
    # Process dense results (1-indexed rank)
    for rank, idx in enumerate(dense_indices):
        if idx not in rrf_scores:
            rrf_scores[idx] = 0.0
        rrf_scores[idx] += 1.0 / (rank + 1 + k)
        
    # Process sparse results (1-indexed rank)
    for rank, idx in enumerate(sparse_indices):
        if idx not in rrf_scores:
            rrf_scores[idx] = 0.0
        rrf_scores[idx] += 1.0 / (rank + 1 + k)
        
    # Sort by score descending
    sorted_indices = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
    return sorted_indices

def hybrid_search(query: str, top_k: int = 10) -> str:
    """
    Perform a hybrid dense and sparse search for a query and return formatted text.
    """
    if faiss_index is None or bm25_model is None or chunks_data is None:
        return "Error: Indexes not fully loaded. Run data ingestion first."

    # 1. Dense Search
    query_embedding = embedding_model.encode([query])
    query_embedding = np.array(query_embedding).astype("float32")
    
    # Retrieve more than top_k for better fusion (e.g., top 20)
    fetch_k = max(top_k * 4, 20)
    
    # Ensure fetch_k does not exceed index size
    fetch_k = min(fetch_k, faiss_index.ntotal)
    
    if fetch_k == 0:
        return "Error: FAISS index is empty."
        
    dense_dists, dense_indices_batch = faiss_index.search(query_embedding, fetch_k)
    dense_indices = dense_indices_batch[0]
    
    # 2. Sparse Search (BM25)
    tokenized_query = query.lower().split()
    sparse_scores = bm25_model.get_scores(tokenized_query)
    
    # Get top indices for sparse (argsort returns ascending, so take from end)
    num_chunks = len(sparse_scores)
    actual_fetch_k = min(fetch_k, num_chunks)
    sparse_indices = np.argsort(sparse_scores)[-actual_fetch_k:][::-1]
    
    # 3. Combine with RRF
    fused_results = reciprocal_rank_fusion(dense_indices, sparse_indices, k=60)
    
    # Get top_k after fusion
    top_indices = [idx for idx, score in fused_results[:top_k]]
    
    # 4. Format Output
    formatted_docs = []
    for idx in top_indices:
        # Safeguard against invalid indices
        if idx < 0 or idx >= len(chunks_data):
            continue
            
        chunk = chunks_data[idx]
        source = chunk.get("source", "Unknown Source")
        text = chunk.get("text", "")
        
        doc_str = f"Source: {source}\n{text}"
        formatted_docs.append(doc_str)
        
    separator = "\n\n--- DOCUMENT ---\n\n"
    return separator.join(formatted_docs)

if __name__ == "__main__":
    # Simple test execution
    test_query = "What is the HackerRank refund policy?"
    print(f"\n--- Testing hybrid_search for query: '{test_query}' ---")
    results = hybrid_search(test_query, top_k=3)
    print("\nResults:\n")
    print(results)
