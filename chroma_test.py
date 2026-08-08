import fitz
import chromadb
from sentence_transformers import SentenceTransformer

# Load embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")

# Open PDF
pdf = fitz.open("documents/ABIHA EXCEL ASSIGNMENT.pdf")

# Extract text
full_text = ""

for page in pdf:
    full_text += page.get_text()

# Create chunks
chunk_size = 500
overlap = 100

chunks = []

start = 0

while start < len(full_text):
    end = start + chunk_size

    chunk = full_text[start:end]
    chunks.append(chunk)

    start += chunk_size - overlap

# Create embeddings
embeddings = model.encode(chunks)

# Create ChromaDB client
client = chromadb.PersistentClient(path="./chroma_db")

# Create collection
collection = client.get_or_create_collection(
    name="abiha_excel_assignment"
)

# Add chunks and embeddings
collection.add(
    ids=[f"chunk_{i}" for i in range(len(chunks))],
    documents=chunks,
    embeddings=embeddings.tolist()
)

print("Number of chunks stored:", collection.count())