from chromadb.utils import embedding_functions
from sklearn.metrics.pairwise import cosine_distances

ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

emb_1 = ef(["Generative AI"])
emb_2 = ef(["Langchain"])

dist = cosine_distances(emb_1, emb_2)[0][0]
sim = 1.0 - dist
print(f"Distance: {dist}")
print(f"Similarity: {sim}")
