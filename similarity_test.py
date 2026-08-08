from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

model = SentenceTransformer("all-MiniLM-L6-v2")

sentence1 = "Excel formulas are used to perform calculations."
sentence2 = "Formulas help calculate values in spreadsheets."

embedding1 = model.encode([sentence1])
embedding2 = model.encode([sentence2])

similarity = cosine_similarity(embedding1, embedding2)

print("Similarity:", similarity[0][0])