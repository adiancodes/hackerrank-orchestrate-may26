import os
import glob
import pickle
import numpy as np
import faiss
from rank_bm25 import BM25Okapi
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "data"))
STORE_DIR = os.path.join(BASE_DIR, "store")
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

# Initialize Local Embedding Model
print("Loading local embedding model (all-MiniLM-L6-v2)...")
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

def load_documents(data_dir):
    """Recursively load all text/markdown files from the data directory."""
    documents = []
    if not os.path.exists(data_dir):
        print(f"Data directory {data_dir} does not exist.")
        return documents

    for root, _, files in os.walk(data_dir):
        for file in files:
            if file.endswith('.md') or file.endswith('.txt') or file.endswith('.csv'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        if content.strip():
                            documents.append({"content": content, "source": file_path})
                except Exception as e:
                    print(f"Failed to read {file_path}: {e}")
    return documents

def main():
    print("Starting Data Ingestion...")
    if not os.path.exists(STORE_DIR):
        os.makedirs(STORE_DIR)
        print(f"Created store directory at {STORE_DIR}")

    # 1. Load documents
    print(f"Loading documents from {DATA_DIR}...")
    documents = load_documents(DATA_DIR)
    print(f"Loaded {len(documents)} documents.")

    if not documents:
        return

    # 2. Chunk documents
    print(f"Chunking documents (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", " ", ""]
    )
    
    chunks = []
    for doc in documents:
        splits = text_splitter.split_text(doc["content"])
        for split in splits:
            chunks.append({"text": split, "source": doc["source"]})
            
    print(f"Created {len(chunks)} chunks.")

    # 3. Generate Dense Embeddings (LOCALLY) & Build FAISS Index
    print("Generating dense embeddings locally via sentence-transformers...")
    texts = [chunk["text"] for chunk in chunks]
    
    # This will run locally and blazingly fast
    embeddings = embedding_model.encode(texts, show_progress_bar=True)
    embeddings = np.array(embeddings).astype("float32")
    
    print("Building FAISS index...")
    dimension = embeddings.shape[1]
    faiss_index = faiss.IndexFlatL2(dimension)
    faiss_index.add(embeddings)
    
    faiss_index_path = os.path.join(STORE_DIR, "index.faiss")
    faiss.write_index(faiss_index, faiss_index_path)
    print(f"Saved FAISS index to {faiss_index_path}")

    # 4. Build Sparse Index (BM25)
    print("Building BM25 index...")
    tokenized_corpus = [text.lower().split() for text in texts]
    bm25 = BM25Okapi(tokenized_corpus)
    
    bm25_path = os.path.join(STORE_DIR, "bm25.pkl")
    with open(bm25_path, "wb") as f:
        pickle.dump(bm25, f)
    print(f"Saved BM25 index to {bm25_path}")
    
    # 5. Save chunk metadata
    metadata_path = os.path.join(STORE_DIR, "chunks.pkl")
    with open(metadata_path, "wb") as f:
        pickle.dump(chunks, f)
    print(f"Saved chunk metadata to {metadata_path}")
    
    print("Data Ingestion complete! All indexes are saved in code/store/")

if __name__ == "__main__":
    main()