# RAG Agent Beginner Guide

## What this project does

This is a local **Retrieval-Augmented Generation (RAG)** agent built with:
- **Ollama** for local AI models
- **ChromaDB** for storing vector embeddings on disk
- A **web UI** for drag-and-drop ingestion and chat
- A **CLI** for indexing and asking questions

It lets you ask questions about your own documents and returns answers based on text in source passages with inline citations like `[1]`.

## Core concepts

### 1. RAG in simple terms

RAG means:
- **Retrieve** relevant document pieces for a question
- **Augment** the model prompt with those pieces
- **Generate** an answer based only on the retrieved text

This reduces hallucinations compared to asking a plain LLM without document context.

### 2. Why embeddings matter

Documents are split into chunks and converted into numeric vectors called **embeddings**. When you ask a question, the question is also embedded and the system finds chunks whose vectors are most similar.

### 3. Two model roles

This project uses two different Ollama models:
- **Embedding model**: converts text into vectors for search
- **Chat model**: writes the answer using retrieved passages

They are separate because search and answer quality need different capabilities.

### 4. Citation workflow

When you ask a question:
- Top `k` chunks are retrieved from the index
- Each chunk is labeled `[1]`, `[2]`, ...
- The LLM is asked to answer using only those chunks
- The answer includes citations and a source appendix with verbatim text

## Installation checklist

1. Install Python 3.10+
2. Install Ollama and start it
3. Pull required models:
   ```bash
   ollama pull nomic-embed-text
   ollama pull llama3.2
   ```
4. Set up the project:
   ```bash
   cd RAG-Agent
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   copy .env.example .env
   ```
5. Edit `.env` if you need custom ports, models, or paths.

## Running the web UI

Start the local web chatbot:
```bash
python -m src serve
```
Or double-click `run_chatbot.bat` on Windows.

Open:

`http://127.0.0.1:7860`

### Web UI flow

1. Choose an **embedding model** and a **chat model** from the sidebar
2. Drag files into the upload area
3. Click **Add to knowledge base**
4. Ask a question in the chat box

### Important web UI controls

- **Replace entire knowledge base**: re-build the index from scratch
- **Clear knowledge base**: delete the current index
- **Also delete saved uploads**: remove uploaded files from `uploads/`
- **Refresh model list**: reload Ollama models after pulling new ones

## Using the CLI

### Index documents

```bash
python -m src ingest .\documents
```

Rebuild the index from scratch:

```bash
python -m src ingest .\documents --reset
```

### Ask a question

```bash
python -m src ask "What is the refund policy?"
```

Show retrieved passages:

```bash
python -m src ask "Summarize the API" --show-passages
```

### Terminal chat

```bash
python -m src chat
```

### Check status

```bash
python -m src status
```

## Supported files

The project can index:
- Plain text and markup: `.txt`, `.md`, `.json`, `.csv`, `.py`, etc.
- PDF files: `.pdf`
- Word documents: `.docx`

Not supported:
- Scanned image PDFs without OCR
- Legacy `.doc` files

## How indexing works

- Documents are read and normalized
- Text is split into overlapping chunks (~800 characters, 120 overlap)
- Chunks are stored in ChromaDB with metadata:
  - source path
  - line range
  - chunk index
- Embeddings are produced by Ollama via ChromaDB

## How retrieval works

- A user query is sent to the index
- The top `k` most similar chunks are returned
- Each chunk is formatted with a citation label and location
- The chat model receives only those passages

## How answers are generated

The agent uses a strict prompt that demands:
- inline citations like `[1]`
- no invented facts
- no paraphrased quotes inside quotation marks
- short direct answers

After the model replies, the code verifies quoted text and appends a source appendix showing the quoted source sentences.

## Important file roles

- `config.py` — project settings and defaults
- `src/documents.py` — file reading and chunking
- `src/store.py` — ChromaDB collection and embeddings
- `src/retrieve.py` — query retrieval
- `src/agent.py` — prompt construction and answer formatting
- `src/ingest_service.py` — upload persistence and indexing orchestration
- `src/app.py` — Gradio web interface
- `src/cli.py` — terminal commands
- `src/ollama_models.py` — Ollama model discovery

## Best practices

- Keep the knowledge base organized by file type or topic
- Use the same embedding model for indexing and retrieval
- Re-index when documents change or when switching embedding models
- Ask specific questions for better results
- Verify citations by reading the appended source quotes

## Quick start summary

```bash
ollama pull nomic-embed-text
ollama pull llama3.2
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python -m src serve
```

Then open `http://127.0.0.1:7860` and upload files.

---

*This beginner guide is designed to help your team understand and use the local RAG Agent implementation in this repository.*
