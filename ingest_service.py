"""
ingest_service.py

Shared ingestion logic used by:
- ingest.py
- fastapi_app.py

RAG pipeline:
PyMuPDF text extraction -> sentence-aware chunking
-> MiniLM embeddings -> ChromaDB
"""

import os
import re

import fitz

DOCUMENTS_FOLDER = "documents"
CHROMA_PATH = "./chroma_db"
COLLECTION_NAME = "knowledge_base"

CHUNK_SIZE = 800
OVERLAP_SENTENCES = 2

# -----------------------------------------------------------------
# Lazy singletons
# -----------------------------------------------------------------

_model = None
_client = None


def get_model():
    """
    Load SentenceTransformer only when it is actually needed.
    This prevents PyTorch/Transformers from loading during API startup.
    """
    global _model

    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer("all-MiniLM-L6-v2")

    return _model


def get_client():
    """
    Load ChromaDB only when it is actually needed.
    """
    global _client

    if _client is None:
        import chromadb

        _client = chromadb.PersistentClient(
            path=CHROMA_PATH
        )

    return _client


def get_collection(client=None):
    """
    Get or create the ChromaDB collection.
    """
    client = client or get_client()

    return client.get_or_create_collection(
        name=COLLECTION_NAME
    )


def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap_sentences: int = OVERLAP_SENTENCES
):
    """
    Sentence-aware chunking.
    """
    sentences = re.split(
        r'(?<=[.!?])\s+',
        text
    )

    chunks = []
    current_chunk = []

    for sentence in sentences:
        test_chunk = " ".join(
            current_chunk + [sentence]
        )

        if len(test_chunk) <= chunk_size:
            current_chunk.append(sentence)

        else:
            if current_chunk:
                chunks.append(
                    " ".join(current_chunk)
                )

            current_chunk = (
                current_chunk[-overlap_sentences:]
                + [sentence]
            )

    if current_chunk:
        chunks.append(
            " ".join(current_chunk)
        )

    return chunks


def run_ingestion(
    documents_folder: str = DOCUMENTS_FOLDER,
    collection=None,
    model=None,
    verbose: bool = True
):
    """
    Re-process every PDF:
    PDF -> text extraction -> chunking -> MiniLM embeddings
    -> ChromaDB.
    """

    model = model or get_model()
    collection = collection or get_collection()

    if collection.count() > 0:
        collection.delete(
            ids=collection.get()["ids"]
        )

        if verbose:
            print("Old document data cleared.")

    processed_files = []

    for filename in sorted(
        os.listdir(documents_folder)
    ):
        if not filename.lower().endswith(".pdf"):
            continue

        pdf_path = os.path.join(
            documents_folder,
            filename
        )

        if verbose:
            print(f"\nProcessing: {filename}")

        pdf = fitz.open(pdf_path)

        for page_number, page in enumerate(
            pdf,
            start=1
        ):
            text = page.get_text().strip()

            if verbose:
                print(
                    f"Page {page_number}: "
                    f"{len(text)} characters extracted"
                )

            if not text:
                continue

            chunks = chunk_text(text)

            for chunk_number, chunk in enumerate(
                chunks
            ):
                embedding = model.encode(
                    chunk
                ).tolist()

                chunk_id = (
                    f"{filename}_"
                    f"{page_number}_"
                    f"{chunk_number}"
                )

                collection.add(
                    ids=[chunk_id],
                    documents=[chunk],
                    embeddings=[embedding],
                    metadatas=[{
                        "source": filename,
                        "page": page_number
                    }]
                )

        pdf.close()
        processed_files.append(filename)

    total_chunks = collection.count()

    if verbose:
        print(
            "\nAll documents have been processed!"
        )
        print(
            "Total chunks in database:",
            total_chunks
        )

    return {
        "files_processed": processed_files,
        "total_chunks": total_chunks
    }
