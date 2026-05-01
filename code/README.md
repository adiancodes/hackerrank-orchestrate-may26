# HackerRank Orchestrate: Support Triage Agent

## Overview
This repository contains the terminal-based AI support ticket triage agent built for the HackerRank Orchestrate hackathon. It autonomously processes support tickets for HackerRank, Claude, and Visa, accurately routing them to the correct product area or safely escalating high-risk issues to human support.

## Architecture: Hybrid RAG
The agent utilizes a Hybrid Retrieval-Augmented Generation (RAG) architecture to maximize context retrieval accuracy:
- **Dense Search**: Semantic retrieval powered by FAISS and local `all-MiniLM-L6-v2` embeddings, understanding the nuanced meaning behind user queries.
- **Sparse Search**: Keyword-based retrieval powered by BM25, ensuring exact matches for product names and specific terminology.
- **Fusion**: Results from both search methods are combined using Reciprocal Rank Fusion (RRF) to guarantee high recall and precision.

## LLM Integration & Orchestration
- **Model Ecosystem**: Powered by the OpenRouter API running the `openai/gpt-oss-120b:free` model for intelligent text generation.
- **Resiliency & Determinism**: All API calls feature strict 60-second timeouts, two-pass retry loops, and temperature bounds set to `0.0` for maximum consistency.
- **Parsing**: Robust regex extraction pipelines safely map raw JSON responses into the strictly required CSV schema (`status`, `product_area`, `response`, `justification`, `request_type`).

## Safety & Hallucination Prevention
Our architecture emphasizes strict safety constraints:
1. **Two-Step Self-Reflection Layer**: After drafting a response, the LLM runs a second internal "auditor" prompt against its own output. If it detects hallucination, lack of grounding, or invalid mappings, it automatically overrides the ticket status to `escalated`.
2. **Graceful Fallbacks**: Top-level `try/except` blocks ensure that no unexpected network timeout or generation error ever crashes the orchestrator, gracefully degrading to a safe `escalated` / `invalid` state.
3. **Strict Categorization**: Enforces strict schema validations across a precise 4-category request type logic (`bug`, `feature_request`, `invalid`, `product_issue`).

---

## Setup & Installation

### Prerequisites
- Python 3.10+
- An OpenRouter account and API Key.

### 1. Install Dependencies
Install all required packages from `requirements.txt`:
```bash
pip install -r code/requirements.txt
```

### 2. Configure Environment Variables
Create a `.env` file in the root of the project (alongside `AGENTS.md`) and add your OpenRouter API key:
```env
OPENROUTER_API_KEY="your_openrouter_api_key_here"
```

### 3. Initialize the Vector Databases (Data Ingestion)
The first time you run the application, you must pre-compute the dense FAISS and sparse BM25 indexes. Run:
```bash
python code/ingest.py
```
This will parse the markdown files in `data/`, chunk the text, embed it using local `sentence-transformers`, and store the resulting indexes locally in `code/store/`.

### 4. Run the Triage Agent
To start evaluating support tickets, run the main orchestrator loop:
```bash
python code/main.py
```
This will:
1. Read the tickets from `support_tickets/support_tickets.csv` (or fallback to the sample CSV).
2. Process each ticket individually through the hybrid RAG pipeline and OpenRouter LLM.
3. Provide a real-time progress bar with status tracking.
4. Output the strictly structured results to `support_tickets/output.csv`.
