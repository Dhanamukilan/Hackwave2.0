import logging
from typing import List, Dict, Any, Tuple
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

logger = logging.getLogger(__name__)

class FailureClusterer:
    """
    Clusters failure embeddings to identify duplicate / co-occurring failure patterns.
    """

    def cluster_embeddings(
        self,
        vectors: List[List[float]],
        n_clusters: int = 3
    ) -> Tuple[List[int], float]:
        """
        Takes a list of vector embeddings, performs clustering, and returns
        cluster labels and silhouette score.
        """
        if not vectors or len(vectors) < 2:
            return ([0] * len(vectors), 0.0)

        X = np.array(vectors)
        k = min(n_clusters, len(vectors) - 1)
        if k < 2:
            return ([0] * len(vectors), 0.0)

        try:
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            labels = kmeans.fit_predict(X).tolist()
            score = float(silhouette_score(X, labels)) if len(set(labels)) > 1 else 0.0
            return labels, score
        except Exception as e:
            logger.error(f"Clustering error: {e}")
            return ([0] * len(vectors), 0.0)

failure_clusterer = FailureClusterer()
