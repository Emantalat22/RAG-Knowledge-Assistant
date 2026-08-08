"""
ingest_service.py

Shared ingestion logic used by:
  - ingest.py        (manual CLI re-indexing, unchanged behavior)
  - fastapi_app.py    (automatic re-indexing right after a PDF is uploaded)

This file does NOT change the RAG approach. It is the exact same logic that
was already in ingest.py (PyMuPDF text extraction -> sentence-aware chunking
-> MiniLM embeddings -> ChromaDB), just moved into a function so it can be
called from more than one place instead of only running as a top-level script.
"""

import os
import re

import fitz
import chromadb
from sentence_transformers import SentenceTransformer

DOCUMENTS_FOLDER = "documents"
CHROMA_PATH = "./chroma_db"
COLLECTION_NAME = "knowledge_base"

CHUNK_SIZE = 800
OVERLAP_SENTENCES = 2

# -----------------------------------------------------------------
# Lazily-created singletons so the (slow-to-load) embedding model and
# the ChromaDB client are only ever created once per process, and can
# be shared between the API's /ask and /upload endpoints.
# -----------------------------------------------------------------

_model = None
_client = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def get_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=CHROMA_PATH)
    return _client


def get_collection(client=None):
    client = client or get_client()
    # get_or_create_collection is used instead of get_collection so the very
    # first run (before anything has ever been ingested) doesn't crash.
    return client.get_or_create_collection(name=COLLECTION_NAME)


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap_sentences: int = OVERLAP_SENTENCES):
    """Sentence-aware chunking -- identical logic to the original ingest.py."""
    sentences = re.split(r'(?<=[.!?])\s+', text)

    chunks = []
    current_chunk = []

    for sentence in sentences:
        test_chunk = " ".join(current_chunk + [sentence])

        if len(test_chunk) <= chunk_size:
            current_chunk.append(sentence)
        else:
            if current_chunk:
                chunks.append(" ".join(current_chunk))
            current_chunk = current_chunk[-overlap_sentences:] + [sentence]

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks


def run_ingestion(documents_folder: str = DOCUMENTS_FOLDER, collection=None, model=None, verbose: bool = True):
    """
    Re-processes every PDF in `documents_folder`:
      PDF -> text extraction (PyMuPDF) -> sentence-aware chunking -> MiniLM
      embeddings -> stored in the ChromaDB `knowledge_base` collection.

    This clears and rebuilds the whole collection, exactly like the original
    ingest.py did, so results stay consistent whether you add one PDF or ten.

    Returns a small summary dict so the API can report back to the frontend.
    """
    model = model or get_model()
    collection = collection or get_collection()

    if collection.count() > 0:
        collection.delete(ids=collection.get()["ids"])
        if verbose:
            print("Old document data cleared.")

    processed_files = []

    for filename in sorted(os.listdir(documents_folder)):
        if not filename.lower().endswith(".pdf"):
            continue

        pdf_path = os.path.join(documents_folder, filename)

        if verbose:
            print(f"\nProcessing: {filename}")

        pdf = fitz.open(pdf_path)

        for page_number, page in enumerate(pdf, start=1):
            text = page.get_text().strip()

            if verbose:
                print(f"Page {page_number}: {len(text)} characters extracted")

            if not text:
                continue

            chunks = chunk_text(text)

            for chunk_number, chunk in enumerate(chunks):
                embedding = model.encode(chunk).tolist()
                chunk_id = f"{filename}_{page_number}_{chunk_number}"

                collection.add(
                    ids=[chunk_id],
                    documents=[chunk],
                    embeddings=[embedding],
                    metadatas=[{
                        "source": filename,
                        "page": page_number
                    }]
                )

        processed_files.append(filename)

    total_chunks = collection.count()

    if verbose:
        print("\nAll documents have been processed!")
        print("Total chunks in database:", total_chunks)

    return {
        "files_processed": processed_files,
        "total_chunks": total_chunks
    }
