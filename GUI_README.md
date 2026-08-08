# RAG Knowledge Assistant — GUI Integration

This adds a professional web GUI on top of your existing RAG backend.
**Your RAG pipeline (PDF → text extraction → chunking → embeddings → ChromaDB
→ retrieval → Ollama generation) was not rewritten.** The chunking algorithm,
embedding model, retrieval logic, distance threshold, and prompt in
`fastapi_app.py` are byte-for-byte the same as what you already had.

## What was inspected

- **Entry point / API layer:** `fastapi_app.py` — you already had a FastAPI
  app with `/upload`, `/ask`, and `/documents`. This was the natural
  connection point for a GUI, so it's used as-is rather than duplicated.
- **PDF processing:** `ingest.py` — PyMuPDF (`fitz`) text extraction per
  page, sentence-aware chunking (800 chars, 2-sentence overlap), MiniLM
  embeddings, stored in a persistent ChromaDB collection called
  `knowledge_base`, run as a standalone script.
- **Question handling:** `/ask` in `fastapi_app.py` — embeds the question,
  queries Chroma for the 5 nearest chunks, filters by distance ≤ 1.5, builds
  a context-only prompt, and calls `ollama.chat` with `llama3.2:3b`.
- **Not touched:** `rag.py` (your terminal chat loop), `upload_api.py` (an
  earlier Flask prototype), `pdf_reader.py`, `rag_embeddings.py`, and all the
  `*_test.py` scripts. Nothing was deleted.

## What was added or changed, and why

| File | Change | Why |
|---|---|---|
| `ingest_service.py` | **New.** The extraction/chunking/embedding code from `ingest.py`, moved into a reusable `run_ingestion()` function. | So the API can trigger the *same* indexing code after an upload, instead of you having to run `ingest.py` by hand every time. |
| `ingest.py` | **Simplified.** Now just calls `ingest_service.run_ingestion()`. | Keeps `python ingest.py` working exactly as before, with zero duplicated logic. |
| `fastapi_app.py` | **Modified.** Added CORS (so a browser page can call it), switched `get_collection` → `get_or_create_collection` (so it doesn't crash on a completely fresh setup), `/upload` now automatically re-indexes after saving the file, added `/reindex` and `/health`. | The GUI needs CORS to call the API from a file/URL on a different origin, and needs uploaded PDFs to become searchable immediately without a manual script run. The `/ask` retrieval + prompt + generation code is untouched. |
| `frontend/` | **New.** `index.html`, `style.css`, `app.js`, `config.js`. | The GUI itself. Talks to your backend over HTTP; generates nothing on its own. |
| `fastapi_app.py` also now **serves** `frontend/` | **Modified.** Added a `StaticFiles` mount at `/`. | So one process (`python fastapi_app.py`) runs the whole app — backend and frontend joined together at `http://127.0.0.1:8000`. No separate frontend server needed. |
| `requirements.txt` | **New.** | Convenience — matches what's already in your `venv`. |

**Not changed:** `rag.py`, `upload_api.py`, `pdf_reader.py`,
`rag_embeddings.py`, all `*_test.py` files, and the RAG logic itself
(chunk size, overlap, embedding model, `n_results`, `MAX_DISTANCE`, the
prompt template, the LLM model name).

`upload_api.py` (the Flask prototype on port 5001) is left in place but the
GUI does **not** use it — it only talks to `fastapi_app.py`, since that's
the one file that already had upload + ask + documents together.

## Final folder structure

```
RAG-Knowledge-Assistant/
├── fastapi_app.py          (modified)  ← run this to start the backend
├── ingest_service.py       (new)       ← shared ingestion logic
├── ingest.py                (modified)  ← manual CLI re-index, unchanged behavior
├── requirements.txt         (new)
├── GUI_README.md            (new, this file)
├── rag.py                                (untouched — terminal chat loop)
├── upload_api.py                         (untouched — old Flask prototype)
├── pdf_reader.py                         (untouched)
├── rag_embeddings.py                     (untouched)
├── chroma_test.py / embedding_test.py / ollama_test.py /
│   retrieval_test.py / similarity_test.py (untouched)
├── documents/                            (your PDFs live here)
├── chroma_db/                            (your vector DB, unchanged path)
└── frontend/                (new, served automatically by fastapi_app.py)
    ├── index.html
    ├── style.css
    ├── app.js
    └── config.js            ← auto-detects the backend URL; edit only if needed
```

## Install dependencies

From the project root (where `fastapi_app.py` lives):

```bash
python -m venv venv          # skip if you're reusing your existing venv
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate

pip install -r requirements.txt
```

You also need [Ollama](https://ollama.com) installed and running locally with
the model your `/ask` endpoint calls:

```bash
ollama pull llama3.2:3b
ollama serve      # if it isn't already running as a background service
```

## Run it — one command, one URL

The backend now serves the frontend directly, so the two pieces are joined
into a single process:

```bash
python fastapi_app.py
```

Then open **`http://127.0.0.1:8000`** in your browser. That's the whole
app — GUI and API together, one process, one port.

- `http://127.0.0.1:8000/` — the GUI itself
- `http://127.0.0.1:8000/health` — quick check that the backend is up
- `http://127.0.0.1:8000/docs` — interactive API docs (Swagger UI)

`frontend/config.js` auto-detects this and points the GUI at whatever
origin it was loaded from, so no URL editing is needed for this normal way
of running it.

### Alternative: running the frontend on its own

You generally don't need this — the section above is the intended way to
run it now. But if you ever want the frontend served from somewhere else
while the API stays on `:8000` (e.g. a separate static host, or just
serving straight off disk):

```bash
cd frontend
python -m http.server 5500
```
Open `http://127.0.0.1:5500`. Since that's a different origin than the
API, `config.js` automatically falls back to `http://127.0.0.1:8000` — or
hardcode a different `API_BASE_URL` there if your backend runs elsewhere.

## Testing the full PDF → question → answer workflow

1. Start Ollama (`ollama serve`, if not already running).
2. Start the backend: `python fastapi_app.py`. Confirm the status pill in
   the top-right of the GUI says **"Backend connected."**
3. Drag a PDF onto the dropzone (or click it to browse). You'll see
   "Uploading and indexing…", then the file appears under **Indexed
   documents** with a chunk count.
4. Type a question about the PDF's content into the chat box and press
   Enter (or click send).
5. You should see a typing indicator, then the answer appear, with a
   **Sources** strip underneath listing the filename and page number(s) the
   answer was grounded in.
6. Try a question that isn't answerable from the PDF — you should get
   *"I couldn't find that information in the document."* with no sources.
7. Try asking a question with the backend stopped — you should get a clear
   inline error message instead of the UI silently failing.
8. Use **Re-index documents** any time you drop new PDFs directly into the
   `documents/` folder outside the GUI. Use **Clear conversation** to reset
   the chat (this only clears the on-screen chat history, not your indexed
   documents).

## Changes you might want to make to your existing RAG code

None are required — the GUI works with what you have. Two optional
follow-ups if you want to take it further later:

- **Multiple documents at once:** right now `/upload` re-indexes *all* PDFs
  in `documents/` together (same behavior as running `ingest.py`), so
  answers can be sourced from any previously uploaded PDF, not just the
  latest one. If you'd rather scope questions to a single active document,
  that would mean adding a `source` filter to the `collection.query(...)`
  call in `/ask`.
- **Startup cost:** the embedding model and Ollama call happen on first
  request; the first question after starting the backend will be a bit
  slower than the rest.
