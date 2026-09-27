from typing import List, Dict, Any
from app.core.ai_factory.llm import AIFactory

class KnowledgeIngestionService:
    @staticmethod
    def extract_text_from_bytes(file_bytes: bytes) -> str:
        # Reuses exact multi-part string ingestion text parser layout from Nexus Talent
        return file_bytes.decode("utf-8", errors="ignore")

    @classmethod
    def chunk_document(cls, text: str, chunk_size: int = 500, chunk_overlap: int = 100) -> List[Dict[str, Any]]:
        """Splits raw text down into fixed content segments while preserving context overlap markers."""
        words = text.split()
        chunks = []
        step = chunk_size - chunk_overlap
        
        # Simple structural fallback loop mirroring pagination heuristics
        current_page = 1
        for i in range(0, len(words), step):
            segment_words = words[i:i + chunk_size]
            content = " ".join(segment_words)
            if not content.strip():
                continue
            
            # Simple heuristic mapping page transitions per 300 words
            if i > 0 and i % 300 == 0:
                current_page += 1
                
            chunks.append({
                "content": content,
                "page": str(current_page)
            })
        return chunks

    @classmethod
    def process_and_vectorize(cls, filename: str, file_bytes: bytes) -> List[Dict[str, Any]]:
        raw_text = cls.extract_text_from_bytes(file_bytes)
        raw_chunks = cls.chunk_document(raw_text)
        
        processed_chunks = []
        for chunk in raw_chunks:
            # Reuses the exact local/cloud vector embedding engine matrix locked in core
            vector = AIFactory.generate_embedding(text_content=chunk["content"])
            processed_chunks.append({
                "content": chunk["content"],
                "page": chunk["page"],
                "embedding": vector
            })
        return processed_chunks
