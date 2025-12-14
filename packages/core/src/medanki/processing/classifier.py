"""Classification service for categorizing chunks into medical topics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Protocol


BASE_THRESHOLD = 0.65
RELATIVE_THRESHOLD = 0.80
HYBRID_ALPHA = 0.5


class Chunk(Protocol):
    id: str
    text: str


class TaxonomyService(Protocol):
    def get_taxonomy(self, exam_type: str) -> dict: ...
    def get_topics(self) -> List[dict]: ...


class VectorStore(Protocol):
    def hybrid_search(self, query: str, alpha: float = 0.5, **kwargs) -> List[dict]: ...


@dataclass
class TopicMatch:
    topic_id: str
    topic_name: str
    confidence: float
    exam_type: Optional[str] = None


class ClassificationService:
    def __init__(
        self,
        taxonomy_service: TaxonomyService,
        vector_store: VectorStore,
        base_threshold: float = BASE_THRESHOLD,
        relative_threshold: float = RELATIVE_THRESHOLD,
        alpha: float = HYBRID_ALPHA
    ):
        self._taxonomy_service = taxonomy_service
        self._vector_store = vector_store
        self._base_threshold = base_threshold
        self._relative_threshold = relative_threshold
        self._alpha = alpha

    def classify(
        self,
        chunk: Chunk,
        exam_type: Optional[str] = None
    ) -> List[TopicMatch]:
        if not chunk.text or not chunk.text.strip():
            return []

        if exam_type:
            self._taxonomy_service.get_taxonomy(exam_type)

        results = self._vector_store.hybrid_search(
            query=chunk.text,
            alpha=self._alpha
        )

        if not results:
            return []

        matches = []
        for result in results:
            topic_id = result.get("topic_id", "")
            score = result.get("score", 0.0)
            matches.append(TopicMatch(
                topic_id=topic_id,
                topic_name=self._get_topic_name(topic_id),
                confidence=score,
                exam_type=exam_type
            ))

        matches.sort(key=lambda m: m.confidence, reverse=True)

        return self._apply_thresholds(matches)

    def detect_primary_exam(self, chunk: Chunk) -> str:
        mcat_results = self._vector_store.hybrid_search(
            query=chunk.text,
            alpha=self._alpha
        )
        mcat_top = max((r.get("score", 0) for r in mcat_results), default=0)

        usmle_results = self._vector_store.hybrid_search(
            query=chunk.text,
            alpha=self._alpha
        )
        usmle_top = max((r.get("score", 0) for r in usmle_results), default=0)

        return "usmle" if usmle_top >= mcat_top else "mcat"

    def _apply_thresholds(self, matches: List[TopicMatch]) -> List[TopicMatch]:
        if not matches:
            return []

        top_score = matches[0].confidence
        dynamic_threshold = max(self._base_threshold, top_score * self._relative_threshold)

        return [m for m in matches if m.confidence >= dynamic_threshold]

    def _get_topic_name(self, topic_id: str) -> str:
        topics = self._taxonomy_service.get_topics()
        for topic in topics:
            if topic.get("id") == topic_id:
                return topic.get("name", topic_id)
        return topic_id
