
import chromadb
from sentence_transformers import SentenceTransformer
import ollama

conversation_history = []

# -----------------------------
# 1. Load embedding model
# -----------------------------

model = SentenceTransformer("all-MiniLM-L6-v2")

# -----------------------------
# 2. Connect to ChromaDB
# -----------------------------

client = chromadb.PersistentClient(path="./chroma_db")

collection = client.get_collection(
    name="knowledge_base"
)

# -----------------------------
# 3. Continuous question loop
# -----------------------------

while True:

    question = input("\nAsk a question about your PDF (type 'exit' to quit): ")

    if question.lower() == "exit":
        print("Goodbye!")
        break

    # -----------------------------
    # 4. Convert question to embedding
    # -----------------------------

    question_embedding = model.encode(question).tolist()

    # -----------------------------
    # 5. Retrieve relevant chunks
    # -----------------------------

    results = collection.query(
        query_embeddings=[question_embedding],
        n_results=5
    )

    distances = results["distances"][0]
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]

    print("\n🔎 Retrieved chunks:")

    for i, (document, distance) in enumerate(
        zip(documents, distances), start=1
    ):
        print(f"\n--- Result {i} | Distance: {distance:.4f} ---")
        print(document[:500])

    print("\n🔎 Retrieval distances:")

    for i, distance in enumerate(distances, start=1):
        print(f"Result {i}: {distance:.4f}")

    # -----------------------------
    # 6. Filter by relevance
    # -----------------------------

    retrieved_chunks = []
    retrieved_sources = []

    MAX_DISTANCE = 1.5

    for document, metadata, distance in zip(
        documents, metadatas, distances
    ):
        if distance <= MAX_DISTANCE:
            retrieved_chunks.append(document)
            retrieved_sources.append(metadata)

    if not retrieved_chunks:
        print("\n❌ I couldn't find relevant information in your documents.")
        continue

    # -----------------------------
    # 7. Combine chunks into context
    # -----------------------------

    context = "\n\n".join(retrieved_chunks)

    print("\n📚 Retrieved Sources:")

    for source in retrieved_sources:
        print(f"- {source['source']} — Page {source['page']}")

    # -----------------------------
    # 8. Add question to history
    # -----------------------------

    conversation_history.append({
        "role": "user",
        "content": question
    })

    history_text = "\n".join(
        f"{message['role']}: {message['content']}"
        for message in conversation_history
    )

    # -----------------------------
    # 9. Create prompt
    # -----------------------------

    prompt = f"""
Use ONLY the information provided in the context below.

If the answer cannot be found in the context, say:
"I couldn't find that information in the document."

Conversation history:
{history_text}

Context:
{context}

Current question:
{question}

Answer:
"""

    # -----------------------------
    # 10. Send to Llama
    # -----------------------------

    response = ollama.chat(
        model="llama3.2:3b",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    # -----------------------------
    # 11. Display answer
    # -----------------------------

    answer = response["message"]["content"]

    print("\n🤖 Answer:")
    print(answer)

    # -----------------------------
    # 12. Add answer to history
    # -----------------------------

    conversation_history.append({
        "role": "assistant",
        "content": answer
    })

