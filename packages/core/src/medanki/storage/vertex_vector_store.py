"""Vertex AI Vector Search adapter implementing IVectorStore protocol."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol
from uuid import uuid4

from google.cloud import aiplatform
from google.cloud.aiplatform.matching_engine.matching_engine_index_endpoint import Namespace

from medanki.storage.weaviate import MedicalChunk, SearchResult


class SparseEmbedder(Protocol):
    def embed(self, text: str) -> dict: ...


@dataclass
class VertexDatapoint:
    datapoint_id: str
    feature_vector: list[float]
    sparse_embedding: dict | None = None
    restricts: list[dict] | None = None


class VertexVectorStore:
    def __init__(
        self,
        project_id: str,
        location: str,
        index_id: str,
        endpoint_id: str,
        sparse_embedder: SparseEmbedder | None = None,
        deployed_index_id: str | None = None,
    ):
        self._project_id = project_id
        self._location = location
        self._index_id = index_id
        self._endpoint_id = endpoint_id
        self._sparse_embedder = sparse_embedder
        self._deployed_index_id = deployed_index_id or "deployed_index"

        aiplatform.init(project=project_id, location=location)

        self._index = aiplatform.MatchingEngineIndex(index_name=index_id)
        self._endpoint = aiplatform.MatchingEngineIndexEndpoint(
            index_endpoint_name=endpoint_id
        )

    @classmethod
    def create_index(
        cls,
        project_id: str,
        location: str,
        display_name: str,
        dimensions: int = 768,
        streaming: bool = True,
        approximate_neighbors_count: int = 150,
        distance_measure_type: str = "DOT_PRODUCT_DISTANCE",
        shard_size: str = "SHARD_SIZE_SMALL",
    ) -> Any:
        aiplatform.init(project=project_id, location=location)

        index = aiplatform.MatchingEngineIndex.create_tree_ah_index(
            display_name=display_name,
            dimensions=dimensions,
            approximate_neighbors_count=approximate_neighbors_count,
            distance_measure_type=distance_measure_type,
            index_update_method="STREAM_UPDATE" if streaming else "BATCH_UPDATE",
            shard_size=shard_size,
        )
        return index

    @classmethod
    def create_endpoint(
        cls,
        project_id: str,
        location: str,
        display_name: str,
        public: bool = True,
    ) -> Any:
        aiplatform.init(project=project_id, location=location)

        endpoint = aiplatform.MatchingEngineIndexEndpoint.create(
            display_name=display_name,
            public_endpoint_enabled=public,
        )
        return endpoint

    @classmethod
    def deploy_index(
        cls,
        project_id: str,
        location: str,
        index_id: str,
        endpoint_id: str,
        deployed_index_id: str,
        machine_type: str = "e2-standard-2",
        min_replica_count: int = 1,
        max_replica_count: int = 1,
    ) -> None:
        aiplatform.init(project=project_id, location=location)

        endpoint = aiplatform.MatchingEngineIndexEndpoint(
            index_endpoint_name=endpoint_id
        )
        index = aiplatform.MatchingEngineIndex(index_name=index_id)

        endpoint.deploy_index(
            index=index,
            deployed_index_id=deployed_index_id,
            machine_type=machine_type,
            min_replica_count=min_replica_count,
            max_replica_count=max_replica_count,
        )

    def health_check(self) -> bool:
        try:
            deployed = self._endpoint.deployed_indexes
            return len(deployed) > 0
        except Exception:
            return False

    async def upsert(self, chunk: MedicalChunk) -> str:
        chunk_id = chunk.id or str(uuid4())

        restricts = []
        if chunk.exam_type:
            restricts.append({
                "namespace": "exam_type",
                "allow_list": [chunk.exam_type],
            })
        if chunk.document_id:
            restricts.append({
                "namespace": "document_id",
                "allow_list": [chunk.document_id],
            })

        datapoint = {
            "datapoint_id": chunk_id,
            "feature_vector": chunk.embedding,
        }
        if restricts:
            datapoint["restricts"] = restricts

        self._index.upsert_datapoints(datapoints=[datapoint])
        return chunk_id

    async def upsert_batch(self, chunks: list[MedicalChunk]) -> list[str]:
        datapoints = []
        chunk_ids = []

        for chunk in chunks:
            chunk_id = chunk.id or str(uuid4())
            chunk_ids.append(chunk_id)

            restricts = []
            if chunk.exam_type:
                restricts.append({
                    "namespace": "exam_type",
                    "allow_list": [chunk.exam_type],
                })

            datapoint = {
                "datapoint_id": chunk_id,
                "feature_vector": chunk.embedding,
            }
            if restricts:
                datapoint["restricts"] = restricts

            datapoints.append(datapoint)

        self._index.upsert_datapoints(datapoints=datapoints)
        return chunk_ids

    async def vector_search(
        self,
        embedding: list[float],
        limit: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        namespace_filter = None
        if filters:
            namespace_filter = []
            for key, value in filters.items():
                allow_list = [value] if isinstance(value, str) else value
                namespace_filter.append(Namespace(key, allow_list, []))

        response = self._endpoint.find_neighbors(
            deployed_index_id=self._deployed_index_id,
            queries=[embedding],
            num_neighbors=limit,
            filter=namespace_filter,
        )

        results = []
        if response and len(response) > 0:
            for neighbor in response[0]:
                chunk = MedicalChunk(
                    id=neighbor.id,
                    content="",
                    embedding=[],
                    document_id="",
                )
                score = 1.0 - neighbor.distance if hasattr(neighbor, "distance") else 0.0
                results.append(SearchResult(chunk=chunk, score=score))

        return results

    async def hybrid_search(
        self,
        query: str,
        embedding: list[float],
        alpha: float = 0.5,
        limit: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        namespace_filter = None
        if filters:
            namespace_filter = []
            for key, value in filters.items():
                allow_list = [value] if isinstance(value, str) else value
                namespace_filter.append(Namespace(key, allow_list, []))

        response = self._endpoint.find_neighbors(
            deployed_index_id=self._deployed_index_id,
            queries=[embedding],
            num_neighbors=limit,
            filter=namespace_filter,
        )

        results = []
        if response and len(response) > 0:
            for neighbor in response[0]:
                chunk = MedicalChunk(
                    id=neighbor.id,
                    content="",
                    embedding=[],
                    document_id="",
                )
                score = 1.0 - neighbor.distance if hasattr(neighbor, "distance") else 0.0
                results.append(SearchResult(chunk=chunk, score=score))

        return results

    def get_by_id(self, chunk_id: str) -> MedicalChunk | None:
        return None

    def delete(self, chunk_id: str) -> None:
        self._index.remove_datapoints(datapoint_ids=[chunk_id])

    def keyword_search(self, query: str, limit: int = 10) -> list[SearchResult]:
        return []
