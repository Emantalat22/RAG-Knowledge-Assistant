import fitz

pdf = fitz.open("documents/ABIHA EXCEL ASSIGNMENT.pdf")

# Extract all text
full_text = ""

for page in pdf:
    full_text += page.get_text()

# Chunk settings
chunk_size = 500
overlap = 100

chunks = []

start = 0

while start < len(full_text):
    end = start + chunk_size

    chunk = full_text[start:end]
    chunks.append(chunk)

    start += chunk_size - overlap

# Display chunks
for number, chunk in enumerate(chunks, start=1):
    print(f"\n--- Chunk {number} ---")
    print(chunk)