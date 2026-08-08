from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")

sentence = "Excel formulas are used to perform calculations."

embedding = model.encode(sentence)

print(embedding)