"""Migrate taxonomy from Weaviate to Vertex AI Vector Search."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from google.cloud import aiplatform


@dataclass
class TaxonomyTopic:
    topic_id: str
    title: str
    path: str
    keywords: list[str]
    exam_type: str
    embedding: list[float]
    searchable_text: str


class TaxonomyMigrator:
    def __init__(
        self,
        project_id: str,
        location: str,
        taxonomy_dir: Path,
        embedding_model: Any = None,
    ):
        self._project_id = project_id
        self._location = location
        self._taxonomy_dir = taxonomy_dir
        self._embedding_model = embedding_model

        aiplatform.init(project=project_id, location=location)

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
        if self._embedding_model is None:
            raise ValueError("Embedding model not provided")
        embedding = self._embedding_model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def load_all_topics(self) -> list[TaxonomyTopic]:
        raw_topics = self._load_usmle_topics() + self._load_mcat_topics()

        topics = []
        for raw in raw_topics:
            searchable_text = self._create_searchable_text(raw)
            embedding = self._embed_text(searchable_text)

            topics.append(
                TaxonomyTopic(
                    topic_id=raw["topic_id"],
                    title=raw["title"],
                    path=raw["path"],
                    keywords=raw["keywords"],
                    exam_type=raw["exam_type"],
                    embedding=embedding,
                    searchable_text=searchable_text,
                )
            )

        return topics

    def migrate_to_vertex(
        self,
        index_id: str,
        sparse_embedder: Any = None,
    ) -> int:
        topics = self.load_all_topics()

        index = aiplatform.MatchingEngineIndex(index_name=index_id)

        datapoints = []
        for topic in topics:
            datapoint = {
                "datapoint_id": topic.topic_id,
                "feature_vector": topic.embedding,
                "restricts": [
                    {"namespace": "exam_type", "allow_list": [topic.exam_type]},
                ],
            }

            if sparse_embedder:
                sparse = sparse_embedder.embed(topic.searchable_text)
                datapoint["sparse_embedding"] = sparse

            datapoints.append(datapoint)

        batch_size = 100
        for i in range(0, len(datapoints), batch_size):
            batch = datapoints[i : i + batch_size]
            index.upsert_datapoints(datapoints=batch)

        return len(topics)

    def export_to_jsonl(self, output_path: Path) -> int:
        topics = self.load_all_topics()

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            for topic in topics:
                data = {
                    "id": topic.topic_id,
                    "embedding": topic.embedding,
                    "restricts": [
                        {"namespace": "exam_type", "allow": [topic.exam_type]},
                    ],
                }
                f.write(json.dumps(data) + "\n")

        return len(topics)

    @classmethod
    def create_taxonomy_index(
        cls,
        project_id: str,
        location: str,
        display_name: str = "medanki-taxonomy",
        dimensions: int = 768,
    ) -> str:
        aiplatform.init(project=project_id, location=location)

        index = aiplatform.MatchingEngineIndex.create_tree_ah_index(
            display_name=display_name,
            dimensions=dimensions,
            approximate_neighbors_count=150,
            distance_measure_type="DOT_PRODUCT_DISTANCE",  # type: ignore[arg-type]
            index_update_method="STREAM_UPDATE",
            shard_size="SHARD_SIZE_SMALL",
        )
        return index.resource_name

    @classmethod
    def create_taxonomy_endpoint(
        cls,
        project_id: str,
        location: str,
        display_name: str = "medanki-taxonomy-endpoint",
    ) -> str:
        aiplatform.init(project=project_id, location=location)

        endpoint = aiplatform.MatchingEngineIndexEndpoint.create(
            display_name=display_name,
            public_endpoint_enabled=True,
        )
        return endpoint.resource_name

    @classmethod
    def deploy_taxonomy_index(
        cls,
        project_id: str,
        location: str,
        index_resource_name: str,
        endpoint_resource_name: str,
        deployed_index_id: str = "taxonomy-deployed",
    ) -> None:
        aiplatform.init(project=project_id, location=location)

        endpoint = aiplatform.MatchingEngineIndexEndpoint(
            index_endpoint_name=endpoint_resource_name
        )
        index = aiplatform.MatchingEngineIndex(index_name=index_resource_name)

        endpoint.deploy_index(
            index=index,
            deployed_index_id=deployed_index_id,
            machine_type="e2-standard-2",
            min_replica_count=1,
            max_replica_count=1,
        )
