import logging
import os
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

class QdrantStore:
    def __init__(self):
        self.collection_name = settings.QDRANT_COLLECTION
        self.vector_dim = 384  # Standard for all-MiniLM-L6-v2 or TF-IDF dense projection
        self.client = self._init_client()
        self._ensure_collection()

    def _init_client(self) -> QdrantClient:
        # First attempt remote Qdrant (Docker Compose / Prod)
        try:
            client = QdrantClient(url=settings.QDRANT_URL, timeout=2.0)
            client.get_collections()
            logger.info(f"Connected to remote Qdrant at {settings.QDRANT_URL}")
            return client
        except Exception as e:
            logger.info(
                f"Remote Qdrant unavailable at {settings.QDRANT_URL} ({e}). "
                f"Falling back to embedded local storage at '{settings.QDRANT_LOCAL_PATH}'."
            )
            try:
                os.makedirs(settings.QDRANT_LOCAL_PATH, exist_ok=True)
                return QdrantClient(path=settings.QDRANT_LOCAL_PATH)
            except Exception as local_err:
                logger.warning(
                    f"Local disk Qdrant failed (e.g. storage locked by concurrent process): {local_err}. "
                    "Falling back to in-memory QdrantClient(':memory:')."
                )
                return QdrantClient(":memory:")

    def _ensure_collection(self):
        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)
            if not exists:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=qmodels.VectorParams(
                        size=self.vector_dim,
                        distance=qmodels.Distance.COSINE
                    )
                )
                logger.info(f"Created Qdrant collection '{self.collection_name}' with dim {self.vector_dim}")
        except Exception as e:
            logger.error(f"Error ensuring Qdrant collection: {e}")

    def insert_failure_embedding(
        self,
        point_id: str,
        vector: List[float],
        payload: Dict[str, Any]
    ) -> bool:
        """
        Payload fields: {fingerprint_id, failure_id, test_id, classification, created_at, error_signature}
        """
        try:
            self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    qmodels.PointStruct(
                        id=point_id,
                        vector=vector,
                        payload=payload
                    )
                ]
            )
            return True
        except Exception as e:
            logger.error(f"Failed to upsert vector in Qdrant: {e}")
            return False

    def search_similar_failures(
        self,
        query_vector: List[float],
        limit: int = 5,
        score_threshold: float = 0.4
    ) -> List[Dict[str, Any]]:
        try:
            hits = []
            if hasattr(self.client, "query_points"):
                res = self.client.query_points(
                    collection_name=self.collection_name,
                    query=query_vector,
                    limit=limit,
                    score_threshold=score_threshold
                )
                hits = res.points if hasattr(res, "points") else res
            elif hasattr(self.client, "search"):
                hits = self.client.search(
                    collection_name=self.collection_name,
                    query_vector=query_vector,
                    limit=limit,
                    score_threshold=score_threshold
                )

            output = []
            for hit in hits:
                output.append({
                    "id": str(hit.id),
                    "score": float(hit.score),
                    "payload": hit.payload
                })
            return output
        except Exception as e:
            logger.error(f"Error searching Qdrant collection: {e}")
            return []

vector_store = QdrantStore()
