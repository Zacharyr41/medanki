from dataclasses import dataclass
from typing import Protocol, Any
from uuid import uuid4


@dataclass
class MedicalChunk:
    id: str
    content: str
    embedding: list[float]
    document_id: str
    exam_type: str | None = None
    metadata: dict | None = None


@dataclass
class SearchResult:
    chunk: MedicalChunk
    score: float


class IVectorStore(Protocol):
    def upsert(self, chunk: MedicalChunk) -> str: ...
    def upsert_batch(self, chunks: list[MedicalChunk]) -> list[str]: ...
    def get_by_id(self, chunk_id: str) -> MedicalChunk | None: ...
    def delete(self, chunk_id: str) -> None: ...
    def vector_search(
        self,
        embedding: list[float],
        limit: int = 10,
        filters: dict[str, Any] | None = None
    ) -> list[SearchResult]: ...
    def keyword_search(self, query: str, limit: int = 10) -> list[SearchResult]: ...
    def hybrid_search(
        self,
        query: str,
        embedding: list[float],
        alpha: float = 0.5,
        limit: int = 10
    ) -> list[SearchResult]: ...
    def health_check(self) -> bool: ...


class WeaviateStore:
    COLLECTION_NAME = "MedicalChunk"

    def __init__(self, client: Any):
        self.client = client
        self._ensure_ready()
        self._ensure_schema()

    def _ensure_ready(self) -> None:
        self.client.is_ready()

    def _ensure_schema(self) -> None:
        if not self.client.collections.exists(self.COLLECTION_NAME):
            self.client.collections.create(
                name=self.COLLECTION_NAME,
                properties=[
                    {"name": "content", "dataType": ["text"]},
                    {"name": "document_id", "dataType": ["text"]},
                    {"name": "exam_type", "dataType": ["text"]},
                    {"name": "metadata", "dataType": ["object"]},
                ],
                vectorizer_config=None,
            )

    def health_check(self) -> bool:
        return self.client.is_ready()

    def _get_collection(self):
        return self.client.collections.get(self.COLLECTION_NAME)

    def upsert(self, chunk: MedicalChunk) -> str:
        collection = self._get_collection()
        chunk_id = chunk.id or str(uuid4())

        collection.data.insert(
            properties={
                "content": chunk.content,
                "document_id": chunk.document_id,
                "exam_type": chunk.exam_type,
                "metadata": chunk.metadata,
            },
            vector=chunk.embedding,
            uuid=chunk_id,
        )
        return chunk_id

    def upsert_batch(self, chunks: list[MedicalChunk]) -> list[str]:
        collection = self._get_collection()
        chunk_ids = []
        objects = []

        for chunk in chunks:
            chunk_id = chunk.id or str(uuid4())
            chunk_ids.append(chunk_id)
            objects.append({
                "properties": {
                    "content": chunk.content,
                    "document_id": chunk.document_id,
                    "exam_type": chunk.exam_type,
                    "metadata": chunk.metadata,
                },
                "vector": chunk.embedding,
                "uuid": chunk_id,
            })

        collection.data.insert_many(objects)
        return chunk_ids

    def get_by_id(self, chunk_id: str) -> MedicalChunk | None:
        collection = self._get_collection()
        result = collection.query.fetch_object_by_id(chunk_id, include_vector=True)

        if result is None:
            return None

        return MedicalChunk(
            id=str(result.uuid),
            content=result.properties.get("content", ""),
            embedding=result.vector.get("default", []),
            document_id=result.properties.get("document_id", ""),
            exam_type=result.properties.get("exam_type"),
            metadata=result.properties.get("metadata"),
        )

    def delete(self, chunk_id: str) -> None:
        collection = self._get_collection()
        collection.data.delete_by_id(chunk_id)

    def _build_filters(self, filters: dict[str, Any] | None):
        if not filters:
            return None

        try:
            from weaviate.classes.query import Filter

            filter_conditions = []
            for key, value in filters.items():
                filter_conditions.append(Filter.by_property(key).equal(value))

            if len(filter_conditions) == 1:
                return filter_conditions[0]

            combined = filter_conditions[0]
            for f in filter_conditions[1:]:
                combined = combined & f
            return combined
        except ImportError:
            return filters

    def vector_search(
        self,
        embedding: list[float],
        limit: int = 10,
        filters: dict[str, Any] | None = None
    ) -> list[SearchResult]:
        collection = self._get_collection()

        query_kwargs = {
            "near_vector": embedding,
            "limit": limit,
            "include_vector": True,
            "return_metadata": ["distance"],
        }

        if filters:
            query_kwargs["filters"] = self._build_filters(filters)

        results = collection.query.near_vector(**query_kwargs)

        search_results = []
        for obj in results.objects:
            chunk = MedicalChunk(
                id=str(obj.uuid),
                content=obj.properties.get("content", ""),
                embedding=obj.vector.get("default", []),
                document_id=obj.properties.get("document_id", ""),
                exam_type=obj.properties.get("exam_type"),
                metadata=obj.properties.get("metadata"),
            )
            distance = getattr(obj.metadata, "distance", 0.0)
            score = 1.0 - distance if distance else 0.0
            search_results.append(SearchResult(chunk=chunk, score=score))

        return search_results

    def keyword_search(self, query: str, limit: int = 10) -> list[SearchResult]:
        collection = self._get_collection()

        results = collection.query.bm25(
            query=query,
            limit=limit,
            include_vector=True,
            return_metadata=["score"],
        )

        search_results = []
        for obj in results.objects:
            chunk = MedicalChunk(
                id=str(obj.uuid),
                content=obj.properties.get("content", ""),
                embedding=obj.vector.get("default", []),
                document_id=obj.properties.get("document_id", ""),
                exam_type=obj.properties.get("exam_type"),
                metadata=obj.properties.get("metadata"),
            )
            score = getattr(obj.metadata, "score", 0.0)
            search_results.append(SearchResult(chunk=chunk, score=score))

        return search_results

    def hybrid_search(
        self,
        query: str,
        embedding: list[float],
        alpha: float = 0.5,
        limit: int = 10
    ) -> list[SearchResult]:
        collection = self._get_collection()

        results = collection.query.hybrid(
            query=query,
            vector=embedding,
            alpha=alpha,
            limit=limit,
            include_vector=True,
            return_metadata=["score"],
        )

        search_results = []
        for obj in results.objects:
            chunk = MedicalChunk(
                id=str(obj.uuid),
                content=obj.properties.get("content", ""),
                embedding=obj.vector.get("default", []),
                document_id=obj.properties.get("document_id", ""),
                exam_type=obj.properties.get("exam_type"),
                metadata=obj.properties.get("metadata"),
            )
            score = getattr(obj.metadata, "score", 0.0)
            search_results.append(SearchResult(chunk=chunk, score=score))

        return search_results
