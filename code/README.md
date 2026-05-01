# HackerRank Orchestrate: Support Triage Agent

## Overview
This repository contains the terminal-based AI support ticket triage agent built for the HackerRank Orchestrate hackathon. It autonomously processes support tickets for HackerRank, Claude, and Visa, accurately routing them to the correct product area or safely escalating high-risk issues to human support.

## Architecture: Hybrid RAG
The agent utilizes a Hybrid Retrieval-Augmented Generation (RAG) architecture to maximize context retrieval accuracy:
- **Dense Search**: Semantic retrieval powered by FAISS, understanding the nuanced meaning behind user queries.
- **Sparse Search**: Keyword-based retrieval powered by BM25, ensuring exact matches for product names and specific terminology.
- **Fusion**: Results from both search methods are combined using Reciprocal Rank Fusion (RRF) to guarantee high recall and precision.

## The Local Pivot
To strictly adhere to the "no external internet calls" constraint for data ingestion, and to ensure the evaluation loop never crashes due to heavy local model downloads or API rate limits, we execute a **Local Pivot**:
- We use the highly optimized, lightweight `all-MiniLM-L6-v2` model from `sentence-transformers` running entirely locally for dense embeddings.
- This guarantees blazingly fast indexing and retrieval without relying on cloud embedding APIs, ensuring 100% reliability during evaluation.

## Safety & Hallucination Prevention
Our architecture emphasizes strict safety and determinism:
1. **Pydantic Structured Outputs**: The Gemini API natively enforces output validation against a strict Pydantic schema. This guarantees that every output row perfectly matches the required CSV column definitions (`status`, `product_area`, `response`, `justification`, `request_type`).
2. **Two-Step Self-Reflection Layer**: After drafting a response, the LLM runs a second internal "auditor" prompt against its own output. If it detects any hallucination, lack of grounding, or wrong-company assumption, it automatically overrides the ticket status to `escalated`.
3. **Graceful Fallbacks**: Top-level `try/except` blocks ensure that no unexpected network timeout or generation error ever crashes the orchestrator.

## Quick Start
1. Install the required dependencies:
   ```bash
   pip install -r code/requirements.txt
   ```
2. Configure your environment: Create a `.env` file in the root directory and add your key: `GEMINI_API_KEY="your_api_key_here"`
3. Pre-compute the hybrid indexes (only needs to be run once):
   ```bash
   python code/ingest.py
   ```
4. Run the evaluation loop:
   ```bash
   python code/main.py
   ```
