# Offline Ollama RAG Agent

A fully **offline** retrieval-augmented generation (RAG) agent powered by [Ollama](https://ollama.com). Use the **local web chatbot** to drag-and-drop files and ask questions, or use the CLI. Answers include **inline `[N]` citations** plus **verbatim source excerpts**.

## Features

- **Local web chatbot**: drag-and-drop upload, chat UI, runs at `http://127.0.0.1:7860`
- **Offline**: embeddings and chat run locally via Ollama; vectors stored in a local ChromaDB index
- **Broad file support**: plain text (`.md`, `.py`, `.json`, `.csv`, code, logs, …), **PDF** (`.pdf`), and **Word** (`.docx`)
- **Inline references**: answers use `[1]`, `[2]`, … tied to retrieved passages
- **Exact quotes**: the model is instructed to copy substrings verbatim; each answer appends a **Source excerpts** section with the full retrieved text for every citation used

## Prerequisites

1. [Ollama](https://ollama.com/download) installed and running
2. Pull the embedding and chat models (defaults shown):

```bash
ollama pull nomic-embed-text
ollama pull llama3.2
```

3. Python 3.10+

## Setup

```bash
cd RAG-Agent
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env` if you use different models or ports.

## Usage

### Web chatbot (recommended)

Start the UI:

```bash
python -m src serve
```

On Windows, double-click `run_chatbot.bat` instead.

Then open **http://127.0.0.1:7860** in your browser:

1. **Choose models** in the sidebar — embedding model (for indexing) and chat model (for answers), populated from `ollama list`
2. **Drag and drop** files into the upload area (PDF, DOCX, text, code, etc.)
3. Click **Add to knowledge base**
4. Ask questions in the chat panel — answers cite your documents with `[N]` references and quoted excerpts

Use **Refresh model list** after running `ollama pull` to load newly installed models.

Options in the sidebar:

- **Replace entire knowledge base** — re-index from scratch instead of appending
- **Clear knowledge base** — wipe the vector index (optionally delete saved uploads)

### CLI

#### 1. Index your documents

```bash
python -m src ingest ./documents
```

Re-index from scratch:

```bash
python -m src ingest ./documents --reset
```

You can also pass a single file path.

#### 2. Ask a question

```bash
python -m src ask "What is the refund policy?"
```

Show retrieval debug table:

```bash
python -m src ask "Summarize the API" --show-passages
```

#### 3. Terminal chat

```bash
python -m src chat
```

#### 4. Check status

```bash
python -m src status
```

## How citations work

1. Your question retrieves the top-*k* text chunks (default 6).
2. Each chunk is labeled `[1]`, `[2]`, … with file name and line range.
3. The LLM answers using only those passages and cites with `[N]`.
4. Quoted phrases in the answer must be **exact substrings** of the cited passage.
5. The answer body uses only `[N]` markers (no inline quotes). A **Reference quotes** section below lists the relevant source sentence(s) for each citation.

Example answer shape:

```markdown
The warranty lasts 90 days [1]. The docs state "returns are accepted within 30 days of purchase" [2].

---

## Source excerpts (verbatim)

**[1]** `policy.txt:L12-18`
...
```

## Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama API |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | Embeddings |
| `OLLAMA_CHAT_MODEL` | `llama3.2` | Answer generation |
| `CHROMA_PATH` | `./index` | Vector store directory |
| `CHUNK_SIZE` | `800` | Characters per chunk (approx.) |
| `CHUNK_OVERLAP` | `120` | Overlap between chunks |
| `TOP_K` | `6` | Passages retrieved per query |
| `APP_HOST` | `127.0.0.1` | Web UI bind address |
| `APP_PORT` | `7860` | Web UI port |
| `UPLOADS_DIR` | `./uploads` | Saved copies of uploaded files |

## Project layout

```
RAG-Agent/
├── config.py
├── documents/          # Example corpus
├── docs/
│   ├── RAG_Agent_Team_Tutorial.md   # Team tutorial (edit this)
│   └── RAG_Agent_Team_Tutorial.pdf  # Generated PDF to share
├── index/              # ChromaDB (auto-created)
├── scripts/
│   └── generate_tutorial_pdf.py
└── src/
    ├── agent.py
    ├── app.py
    ├── cli.py
    ├── documents.py
    ├── ingest_service.py
    ├── retrieve.py
    └── store.py
```

## Team tutorial (PDF)

A beginner-friendly guide for teammates new to RAG, including a full **code walkthrough**:

1. Edit the source: `docs/RAG_Agent_Team_Tutorial.md`
2. Generate the PDF:

```bash
python scripts/generate_tutorial_pdf.py
```

Or double-click **`generate_tutorial_pdf.bat`** — output: `docs/RAG_Agent_Team_Tutorial.pdf`

Share that PDF with your team.

## Notes

- **PDF** text is extracted per page (`--- Page N ---` markers appear in the index for citation context).
- **DOCX** includes paragraph text and table rows (cells joined with ` | `).
- Legacy **`.doc`** (Word 97–2003) is not supported; save as `.docx` or export to PDF first.
- Other binary files (images, etc.) are still skipped.
- Changing the embedding model after indexing requires re-ingesting (`--reset`).
- Quote validation prints warnings when the model paraphrases inside quotes; the appendix still shows the canonical source text.
