
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
from google import genai

from ingest_service import get_model, get_client, get_collection, run_ingestion, DOCUMENTS_FOLDER
from dotenv import load_dotenv
load_dotenv()
app = FastAPI(title="RAG Knowledge Assistant")

# -----------------------------
# CORS
# -----------------------------
# Allows the frontend (served from a different origin, e.g. a local static
# file server or a dev server on another port) to call this API. Wide open
# for local development -- restrict allow_origins to your real frontend
# URL before deploying anywhere public.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs(DOCUMENTS_FOLDER, exist_ok=True)

# -----------------------------
# Load RAG components
# -----------------------------
# Same embedding model + ChromaDB collection as before. Loaded once at
# startup and reused by /upload, /ask and /reindex so there is only ever
# one client/collection instance talking to the database.

model = get_model()
client = get_client()
collection = get_collection(client)

MAX_DISTANCE = 1.5

LLM_MODEL = "gemini-2.5-flash"
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


# -----------------------------
# Health check
# -----------------------------

@app.get("/health")
def health_check():
    try:
        chunk_count = collection.count()
        return {
            "status": "ok",
            "chunks_indexed": chunk_count
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


# -----------------------------
# Upload PDF
# -----------------------------

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):

    try:
        if not file.filename:
            return {
                "error": "No file selected"
            }

        if not file.filename.lower().endswith(".pdf"):
            return {
                "error": "Only PDF files are allowed"
            }

        file_path = os.path.join(
            DOCUMENTS_FOLDER,
            file.filename
        )

        content = await file.read()

        if not content:
            return {
                "error": "The uploaded file is empty"
            }

        with open(file_path, "wb") as f:
            f.write(content)

        # Automatically (re)index every PDF in documents/ so the new file
        # is immediately searchable -- this calls the exact same
        # extraction/chunking/embedding logic as `python ingest.py`.
        try:
            ingest_result = run_ingestion(collection=collection, model=model, verbose=False)
        except Exception as e:
            return {
                "error": f"File was uploaded but indexing failed: {str(e)}",
                "filename": file.filename
            }

        return {
            "message": "PDF uploaded and indexed successfully",
            "filename": file.filename,
            "chunks_indexed": ingest_result["total_chunks"]
        }

    except Exception as e:
        return {
            "error": f"Upload failed: {str(e)}"
        }


# -----------------------------
# Re-index on demand
# -----------------------------

@app.post("/reindex")
def reindex():
    try:
        result = run_ingestion(collection=collection, model=model, verbose=False)
        return {
            "message": "Re-indexing complete",
            "files_processed": result["files_processed"],
            "chunks_indexed": result["total_chunks"]
        }
    except Exception as e:
        return {
            "error": f"Re-indexing failed: {str(e)}"
        }


# -----------------------------
# Ask question
# -----------------------------

class QuestionRequest(BaseModel):
    question: str


@app.post("/ask")
async def ask_question(request: QuestionRequest):

    try:
        question = request.question

        if not question or not question.strip():
            return {
                "error": "Question cannot be empty"
            }

        # Convert question to embedding
        question_embedding = model.encode(
            question
        ).tolist()

        # Retrieve relevant chunks
        results = collection.query(
            query_embeddings=[question_embedding],
            n_results=5
        )

        documents = results["documents"][0]
        distances = results["distances"][0]
        metadatas = results["metadatas"][0]

        # Filter relevant results
        retrieved_chunks = []
        retrieved_sources = []

        for document, metadata, distance in zip(
            documents,
            metadatas,
            distances
        ):
            if distance <= MAX_DISTANCE:
                retrieved_chunks.append(document)
                retrieved_sources.append(metadata)

        if not retrieved_chunks:
            return {
                "answer": "I couldn't find that information in the document.",
                "sources": []
            }

        # Combine retrieved chunks
        context = "\n\n".join(
            retrieved_chunks
        )

        # Create prompt
        prompt = f"""
Use ONLY the information provided in the context below.

If the answer cannot be found in the context, say:
"I couldn't find that information in the document."

Context:
{context}

Question:
{question}

Answer:
"""

        # Ask Ollama
        response = client.models.generate_content(
           model=LLM_MODEL,
           contents=prompt
            )

        answer = response.text

        # Return answer + sources
        return {
            "answer": answer,
            "sources": [
                {
                    "source": source["source"],
                    "page": source["page"]
                }
                for source in retrieved_sources
            ]
        }

    except Exception as e:
        return {
            "error": f"Question processing failed: {str(e)}"
        }


# -----------------------------
# List documents
# -----------------------------

@app.get("/documents")
def list_documents():

    try:
        files = [
            filename
            for filename in os.listdir(DOCUMENTS_FOLDER)
            if filename.lower().endswith(".pdf")
        ]

        return {
            "documents": files
        }

    except Exception as e:
        return {
            "error": f"Could not list documents: {str(e)}"
        }


# -----------------------------
# Serve the frontend
# -----------------------------
# Mounted last so it doesn't shadow the API routes above. This lets you
# run just this one file and open http://127.0.0.1:8000 to get the whole
# app -- no separate frontend server needed.

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")

if os.path.isdir(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


# -----------------------------
# Start server
# -----------------------------

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000
    )
