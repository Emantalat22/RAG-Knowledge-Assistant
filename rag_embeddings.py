import fitz
from sentence_transformers import SentenceTransformer

# Load the embedding model
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

# Create embeddings for every chunk
embeddings = model.encode(chunks)

# Display information
print("Number of chunks:", len(chunks))
print("Number of embeddings:", len(embeddings))
print("First embedding:")
print(embeddings[0])