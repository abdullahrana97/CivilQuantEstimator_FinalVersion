"""Small, session-local FAISS index with page-aware, token-sized chunks.

Only the public encoder is shared by Streamlit's resource cache. Documents and
indexes must stay in the user's session; no pickle or uploaded FAISS is loaded.
"""
from dataclasses import dataclass
from hashlib import sha256
import io
from pathlib import Path

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
MAX_FILES = 5
MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_TOTAL_BYTES = 10 * 1024 * 1024
MAX_PAGES = 100
MAX_TEXT_CHARS = 500000
MAX_CHUNKS = 400


@dataclass(frozen=True)
class Passage:
    id: str
    filename: str
    page: int
    text: str


@dataclass(frozen=True)
class Hit:
    passage: Passage
    score: float


def read_documents(files):
    """files is a list of (display filename, bytes). Never interpreted as paths."""
    if not 1 <= len(files) <= MAX_FILES:
        raise ValueError("Choose between 1 and 5 documents.")
    if sum(len(data) for _, data in files) > MAX_TOTAL_BYTES:
        raise ValueError("Use at most 10 MB across all documents.")
    pages, warnings, seen = [], [], set()
    char_count = 0
    for original_name, data in files:
        name = Path(original_name.replace("\\", "/")).name[:150]
        if not data or len(data) > MAX_FILE_BYTES:
            raise ValueError(f"{name}: choose a nonempty file under 5 MB.")
        digest = sha256(data).hexdigest()
        if digest in seen:
            warnings.append(f"Skipped duplicate content: {name}")
            continue
        seen.add(digest)
        suffix = Path(name).suffix.lower()
        if suffix == ".pdf":
            from pypdf import PdfReader
            try:
                reader = PdfReader(io.BytesIO(data))
                if reader.is_encrypted and not reader.decrypt(""):
                    raise ValueError(f"{name}: password-protected PDFs are not supported.")
                if len(reader.pages) > MAX_PAGES:
                    raise ValueError(f"{name}: limit is 100 pages per PDF.")
                texts = [(i + 1, p.extract_text() or "") for i, p in enumerate(reader.pages)]
            except ValueError:
                raise
            except Exception as exc:
                raise ValueError(f"{name}: PDF could not be read; try a text-based PDF.") from exc
        elif suffix in (".txt", ".md"):
            try:
                texts = [(1, data.decode("utf-8-sig"))]
            except UnicodeDecodeError as exc:
                raise ValueError(f"{name}: save the file using UTF-8 encoding.") from exc
        else:
            raise ValueError("Supported formats are PDF, TXT and MD.")
        empty = 0
        for page, text in texts:
            text = " ".join(text.replace("\x00", " ").split())
            if not text:
                empty += 1
                continue
            char_count += len(text)
            if char_count > MAX_TEXT_CHARS:
                raise ValueError("Too much extracted text. Index a smaller selection of documents.")
            pages.append((name, page, text))
        if empty:
            warnings.append(f"{name}: {empty} empty/image-only pages skipped. OCR is not included.")
    if not pages:
        raise ValueError("No readable text found. Scanned PDFs need OCR before upload.")
    return pages, warnings


def chunk_pages(pages, tokenizer, size=200, overlap=32):
    if not 0 <= overlap < size:
        raise ValueError("Chunk overlap must be smaller than chunk size.")
    passages = []
    for name, page, text in pages:
        encoded = tokenizer(text, add_special_tokens=False, return_offsets_mapping=True,
                            truncation=False, verbose=False)
        tokens, offsets = encoded["input_ids"], encoded["offset_mapping"]
        for start in range(0, len(tokens), size - overlap):
            end = min(start + size, len(tokens))
            body = text[offsets[start][0]:offsets[end - 1][1]].strip()
            if body:
                passages.append(Passage(f"S{len(passages)+1:04}", name, page, body))
            if len(passages) > MAX_CHUNKS:
                raise ValueError("Document set exceeds 400 chunks. Use fewer/shorter documents.")
            if start + size >= len(tokens):
                break
    return passages


class KnowledgeIndex:
    def __init__(self, passages, encoder):
        import faiss
        import numpy as np
        if not passages:
            raise ValueError("Nothing to index.")
        self.passages = list(passages)
        self.encoder = encoder
        embeddings = encoder.encode([p.text for p in passages], normalize_embeddings=True,
                                    convert_to_numpy=True, batch_size=16, show_progress_bar=False)
        self.index = faiss.IndexFlatIP(embeddings.shape[1])
        self.index.add(np.ascontiguousarray(embeddings, dtype="float32"))

    def search(self, query, limit=3, threshold=0.25):
        import numpy as np
        if not query.strip():
            return []
        vector = self.encoder.encode([query[:2000]], normalize_embeddings=True,
                                     convert_to_numpy=True, show_progress_bar=False)
        scores, ids = self.index.search(np.ascontiguousarray(vector, dtype="float32"),
                                        min(max(1, limit), len(self.passages)))
        return [Hit(self.passages[int(i)], float(score)) for i, score in zip(ids[0], scores[0])
                if i >= 0 and float(score) >= threshold]


def evidence_text(hits):
    return "\n\n".join(f"[{h.passage.id}] {h.passage.filename}, page {h.passage.page}\n{h.passage.text}"
                       for h in hits)


def source_dict(hit):
    p = hit.passage
    return dict(id=p.id, filename=p.filename, page=p.page, text=p.text, similarity=round(hit.score, 4))
