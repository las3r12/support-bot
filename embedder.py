from sentence_transformers import SentenceTransformer

MODEL_PATH = "./models/all-MiniLM-L6-v2"


class Embedder:
    def __init__(self, model_path: str = MODEL_PATH):
        self.model = SentenceTransformer(model_path)

    def embed(self, texts):
        return self.model.encode(texts, normalize_embeddings=True).tolist()

    def chunk_text(self, text: str, size: int = 500, overlap: int = 50):
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + size, len(text))
            if end < len(text):
                last_space = text.rfind(" ", start, end)
                if last_space > start:
                    end = last_space
            chunks.append(text[start:end].strip())
            start += size - overlap
        return chunks
