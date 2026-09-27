from sqlalchemy.orm import Session
from typing import List, Dict, Any
from uuid import UUID
from app.core.ai_factory.llm import AIFactory
from app.modules.support.knowledge.models import KnowledgeChunkModel, KnowledgeDocumentModel

class TenantIsolatedSearchEngine:
    @staticmethod
    def compute_cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        # Reuses text vector calculation rules from Nexus Talent Matcher
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm_a = sum(a * a for a in vec1) ** 0.5
        norm_b = sum(b * b for b in vec2) ** 0.5
        return dot_product / (norm_a * norm_b) if norm_a and norm_b else 0.0

    @classmethod
    def execute_hybrid_retrieval(cls, query: str, org_id: UUID, db: Session, limit: int = 3) -> List[Dict[str, Any]]:
        """Retrieves matched knowledge segments while strictly restricting records by tenant ID."""
        query_vector = AIFactory.generate_embedding(text_content=query)
        
        # MANDATORY CRITERIA: Isolation filter applied directly to the query statement
        chunks = db.query(KnowledgeChunkModel).filter(
            KnowledgeChunkModel.organization_id == org_id
        ).all()
        
        scored_chunks = []
        for chunk in chunks:
            similarity = cls.compute_cosine_similarity(query_vector, chunk.embedding)
            
            # Hybrid validation: Add minor keyword boosting if search terms cross-align
            keyword_score = 0.1 if any(word.lower() in chunk.content.lower() for word in query.split()) else 0.0
            total_score = similarity + keyword_score
            
            doc = db.query(KnowledgeDocumentModel).filter(
                KnowledgeDocumentModel.document_id == chunk.document_id
            ).first()
            
            scored_chunks.append({
                "content": chunk.content,
                "page": chunk.page_number,
                "filename": doc.filename if doc else "unknown.pdf",
                "score": total_score
            })
            
        scored_chunks.sort(key=lambda x: x["score"], reverse=True)
        return scored_chunks[:limit]
