from sentence_transformers import SentenceTransformer
import re


class Embedder:
    def __init__(self, model_path: str):
        self.model = SentenceTransformer(model_path)

    def embed(self, texts):
        return self.model.encode(texts, normalize_embeddings=True).tolist()
    

    def chunk_text(self, text: str, size: int = 150, overlap: int = 30) -> list[str]:
        separators = [
            r'\n{2,}',
            r'\n',
            r'(?<=[.!?])\s+',
            r'(?<=:)\s+',
            r'\s+',
        ]

        segments = [text]
        for sep in separators:
            if all(len(s) <= size for s in segments):
                break
            new_segments = []
            for seg in segments:
                if len(seg) <= size:
                    new_segments.append(seg)
                else:
                    parts = re.split(sep, seg)
                    new_segments.extend(p for p in parts if p.strip())
            segments = new_segments

        split_segments = []
        for seg in segments:
            while len(seg) > size:
                split_segments.append(seg[:size])
                seg = seg[size:]
            if seg:
                split_segments.append(seg.strip())

        chunks = []
        current = ""
        for segment in split_segments:
            if not current:
                current = segment
            elif len(current) + 1 + len(segment) <= size:
                current = current + " " + segment
            else:
                chunks.append(current)
                current = (current[-overlap:] + " " + segment).strip()
        if current:
            chunks.append(current)
        return chunks

