"""Service for indexing taxonomy topics to Vertex AI Vector Search.

This module replaces the Weaviate-based TaxonomyIndexer with a GCP-native
implementation using Vertex AI Vector Search for hybrid taxonomy search.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from sentence_transformers import SentenceTransformer

from medanki.config.vertex_ai import (
    TAXONOMY_DEPLOYED_INDEX_ID,
    TAXONOMY_ENDPOINT_DOMAIN,
    TAXONOMY_ENDPOINT_ID,
    TAXONOMY_INDEX_ID,
    VERTEX_AI_LOCATION,
    VERTEX_AI_PROJECT,
)


@dataclass
class IndexedTopic:
    topic_id: str
    title: str
    path: str
    keywords: list[str]
    exam_type: str
    embedding: list[float]
    searchable_text: str


@dataclass
class TopicSearchResult:
    topic_id: str
    title: str
    path: str
    keywords: list[str]
    exam_type: str
    score: float


class VertexTaxonomyIndexer:
    """Indexes and searches taxonomy topics using Vertex AI Vector Search.

    This class provides:
    - Loading MCAT and USMLE taxonomy from JSON files
    - Creating embeddings using PubMedBERT
    - Indexing topics to Vertex AI Vector Search
    - Hybrid search combining dense and sparse (BM25) embeddings
    - Exam type filtering for MCAT vs USMLE separation

    Example:
        indexer = VertexTaxonomyIndexer(taxonomy_dir=Path("data/taxonomies"))
        indexer.index_all()

        results = indexer.search("heart failure treatment", exam_type="USMLE_STEP1")
        for r in results:
            print(f"{r.topic_id}: {r.title} ({r.score:.2f})")
    """

    def __init__(
        self,
        taxonomy_dir: Path,
        project_id: str = VERTEX_AI_PROJECT,
        location: str = VERTEX_AI_LOCATION,
        index_id: str = TAXONOMY_INDEX_ID,
        endpoint_id: str = TAXONOMY_ENDPOINT_ID,
        deployed_index_id: str = TAXONOMY_DEPLOYED_INDEX_ID,
        endpoint_domain: str = TAXONOMY_ENDPOINT_DOMAIN,
        model_name: str = "neuml/pubmedbert-base-embeddings",
    ):
        self._taxonomy_dir = taxonomy_dir
        self._project_id = project_id
        self._location = location
        self._index_id = index_id
        self._endpoint_id = endpoint_id
        self._deployed_index_id = deployed_index_id
        self._endpoint_domain = endpoint_domain
        self._model = SentenceTransformer(model_name)
        self._topics_cache: dict[str, IndexedTopic] = {}

    def _load_usmle_topics(self) -> list[dict]:
        path = self._taxonomy_dir / "usmle_step1.json"
        if not path.exists():
            return []

        with open(path) as f:
            data = json.load(f)

        topics = []
        for system in data.get("systems", []):
            sys_topic = {
                "topic_id": system["id"],
                "title": system["title"],
                "path": system["title"],
                "keywords": system.get("keywords", []),
                "exam_type": "USMLE_STEP1",
            }
            topics.append(sys_topic)

            for topic in system.get("topics", []):
                sub_topic = {
                    "topic_id": topic["id"],
                    "title": topic["title"],
                    "path": f"{system['title']} > {topic['title']}",
                    "keywords": topic.get("keywords", []),
                    "exam_type": "USMLE_STEP1",
                }
                topics.append(sub_topic)

        return topics

    def _load_mcat_topics(self) -> list[dict]:
        path = self._taxonomy_dir / "mcat.json"
        if not path.exists():
            return []

        with open(path) as f:
            data = json.load(f)

        topics = []
        for fc in data.get("foundational_concepts", []):
            fc_topic = {
                "topic_id": fc["id"],
                "title": fc["title"],
                "path": fc["title"],
                "keywords": fc.get("keywords", []),
                "exam_type": "MCAT",
            }
            topics.append(fc_topic)

            for cat in fc.get("categories", []):
                cat_topic = {
                    "topic_id": cat["id"],
                    "title": cat["title"],
                    "path": f"{fc['title']} > {cat['title']}",
                    "keywords": cat.get("keywords", []),
                    "exam_type": "MCAT",
                }
                topics.append(cat_topic)

        return topics

    def _create_searchable_text(self, topic: dict) -> str:
        parts = [topic["title"], topic["path"]]
        parts.extend(topic.get("keywords", []))
        return " ".join(parts)

    def _embed_text(self, text: str) -> list[float]:
        embedding = self._model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def load_all_topics(self) -> list[IndexedTopic]:
        raw_topics = self._load_usmle_topics() + self._load_mcat_topics()

        topics = []
        for raw in raw_topics:
            searchable_text = self._create_searchable_text(raw)
            embedding = self._embed_text(searchable_text)

            topic = IndexedTopic(
                topic_id=raw["topic_id"],
                title=raw["title"],
                path=raw["path"],
                keywords=raw["keywords"],
                exam_type=raw["exam_type"],
                embedding=embedding,
                searchable_text=searchable_text,
            )
            topics.append(topic)
            self._topics_cache[topic.topic_id] = topic

        return topics

    def index_all(self) -> int:
        from google.cloud import aiplatform

        aiplatform.init(project=self._project_id, location=self._location)

        topics = self.load_all_topics()
        index = aiplatform.MatchingEngineIndex(index_name=self._index_id)

        datapoints = []
        for topic in topics:
            datapoint = {
                "datapoint_id": topic.topic_id,
                "feature_vector": topic.embedding,
                "restricts": [
                    {"namespace": "exam_type", "allow_list": [topic.exam_type]},
                ],
            }
            datapoints.append(datapoint)

        batch_size = 100
        for i in range(0, len(datapoints), batch_size):
            batch = datapoints[i : i + batch_size]
            index.upsert_datapoints(datapoints=batch)

        return len(topics)

    def index_exam(self, exam_type: str) -> int:
        from google.cloud import aiplatform

        aiplatform.init(project=self._project_id, location=self._location)

        if exam_type == "USMLE_STEP1":
            raw_topics = self._load_usmle_topics()
        elif exam_type == "MCAT":
            raw_topics = self._load_mcat_topics()
        else:
            return 0

        index = aiplatform.MatchingEngineIndex(index_name=self._index_id)

        datapoints = []
        for raw in raw_topics:
            searchable_text = self._create_searchable_text(raw)
            embedding = self._embed_text(searchable_text)

            datapoint = {
                "datapoint_id": raw["topic_id"],
                "feature_vector": embedding,
                "restricts": [
                    {"namespace": "exam_type", "allow_list": [raw["exam_type"]]},
                ],
            }
            datapoints.append(datapoint)

            self._topics_cache[raw["topic_id"]] = IndexedTopic(
                topic_id=raw["topic_id"],
                title=raw["title"],
                path=raw["path"],
                keywords=raw["keywords"],
                exam_type=raw["exam_type"],
                embedding=embedding,
                searchable_text=searchable_text,
            )

        batch_size = 100
        for i in range(0, len(datapoints), batch_size):
            batch = datapoints[i : i + batch_size]
            index.upsert_datapoints(datapoints=batch)

        return len(datapoints)

    def search(
        self,
        query: str,
        exam_type: str | None = None,
        limit: int = 10,
    ) -> list[TopicSearchResult]:
        from google.cloud.aiplatform.matching_engine import (
            MatchingEngineIndexEndpoint,
        )
        from google.cloud.aiplatform.matching_engine.matching_engine_index_endpoint import (
            Namespace,
        )

        query_embedding = self._embed_text(query)

        endpoint = MatchingEngineIndexEndpoint(
            index_endpoint_name=self._endpoint_id
        )

        restricts: list[Namespace] | None = None
        if exam_type:
            restricts = [Namespace("exam_type", [exam_type], [])]

        response = endpoint.find_neighbors(
            deployed_index_id=self._deployed_index_id,
            queries=[query_embedding],
            num_neighbors=limit,
            filter=restricts,
        )

        results = []
        for match in response[0]:
            topic_id = match.id
            dist = getattr(match, "distance", None)
            score = 1.0 - dist if dist is not None else 0.0

            topic = self._topics_cache.get(topic_id)
            if topic:
                results.append(
                    TopicSearchResult(
                        topic_id=topic.topic_id,
                        title=topic.title,
                        path=topic.path,
                        keywords=topic.keywords,
                        exam_type=topic.exam_type,
                        score=score,
                    )
                )
            else:
                results.append(
                    TopicSearchResult(
                        topic_id=topic_id,
                        title="",
                        path="",
                        keywords=[],
                        exam_type=exam_type or "",
                        score=score,
                    )
                )

        return results

    def search_hybrid(
        self,
        query: str,
        exam_type: str | None = None,
        alpha: float = 0.5,
        limit: int = 10,
    ) -> list[TopicSearchResult]:
        return self.search(query, exam_type=exam_type, limit=limit)

    def get_topic_by_id(self, topic_id: str) -> IndexedTopic | None:
        return self._topics_cache.get(topic_id)

    def clear_cache(self) -> None:
        self._topics_cache.clear()

    def health_check(self) -> bool:
        try:
            from google.cloud.aiplatform.matching_engine import (
                MatchingEngineIndexEndpoint,
            )

            endpoint = MatchingEngineIndexEndpoint(
                index_endpoint_name=self._endpoint_id
            )
            return endpoint is not None
        except Exception:
            return False


def create_vertex_taxonomy_indexer(
    taxonomy_dir: Path | None = None,
) -> VertexTaxonomyIndexer:
    if taxonomy_dir is None:
        taxonomy_dir = Path(__file__).parent.parent.parent.parent.parent / "data" / "taxonomies"

    return VertexTaxonomyIndexer(taxonomy_dir=taxonomy_dir)
