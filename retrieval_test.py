import chromadb
from sentence_transformers import SentenceTransformer

# Load the embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")

# Connect to our existing ChromaDB
client = chromadb.PersistentClient(path="./chroma_db")

# Get our collection
collection = client.get_collection(
    name="abiha_excel_assignment"
)

# The user's question
question = "What is a formula in Excel?"

# Convert question into an embedding
question_embedding = model.encode(question).tolist()

# Search ChromaDB
results = collection.query(
    query_embeddings=[question_embedding],
    n_results=3
)

# Display results
print("\nRetrieved chunks:\n")

for i, document in enumerate(results["documents"][0], start=1):
    print(f"--- Result {i} ---")
    print(document)
    print()