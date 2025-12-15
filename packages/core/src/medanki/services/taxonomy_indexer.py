"""Service for indexing taxonomy topics to Weaviate for hybrid search."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from sentence_transformers import SentenceTransformer
from weaviate.classes.config import DataType, Property
from weaviate.classes.data import DataObject

COLLECTION_NAME = "TaxonomyTopic"


@dataclass
class IndexedTopic:
    topic_id: str
    title: str
    path: str
    keywords: list[str]
    exam_type: str
    embedding: list[float]


class TaxonomyIndexer:
    def __init__(
        self,
        weaviate_client: Any,
        taxonomy_dir: Path,
        model_name: str = "neuml/pubmedbert-base-embeddings",
    ):
        self._client = weaviate_client
        self._taxonomy_dir = taxonomy_dir
        self._model = SentenceTransformer(model_name)
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        if not self._client.collections.exists(COLLECTION_NAME):
            self._client.collections.create(
                name=COLLECTION_NAME,
                properties=[
                    Property(name="topic_id", data_type=DataType.TEXT),
                    Property(name="title", data_type=DataType.TEXT),
                    Property(name="path", data_type=DataType.TEXT),
                    Property(name="keywords", data_type=DataType.TEXT_ARRAY),
                    Property(name="exam_type", data_type=DataType.TEXT),
                    Property(name="searchable_text", data_type=DataType.TEXT),
                ],
            )

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

    def index_exam(self, exam_type: str) -> int:
        if exam_type == "USMLE_STEP1":
            topics = self._load_usmle_topics()
        elif exam_type == "MCAT":
            topics = self._load_mcat_topics()
        else:
            return 0
        
        collection = self._client.collections.get(COLLECTION_NAME)

        objects = []
        for topic in topics:
            searchable_text = self._create_searchable_text(topic)
            embedding = self._embed_text(searchable_text)

            objects.append(
                DataObject(
                    properties={
                        "topic_id": topic["topic_id"],
                        "title": topic["title"],
                        "path": topic["path"],
                        "keywords": topic["keywords"],
                        "exam_type": topic["exam_type"],
                        "searchable_text": searchable_text,
                    },
                    vector=embedding,
                    uuid=uuid4(),
                )
            )

        if objects:
            collection.data.insert_many(objects)
        
        return len(objects)

    def search(
        self,
        query: str,
        exam_type: str | None = None,
        alpha: float = 0.5,
        limit: int = 10,
    ) -> list[dict]:
        collection = self._client.collections.get(COLLECTION_NAME)
        
        query_embedding = self._embed_text(query)
        
        results = collection.query.hybrid(
            query=query,
            vector=query_embedding,
            alpha=alpha,
            limit=limit,
            return_metadata=["score"],
        )
        
        matches = []
        for obj in results.objects:
            if exam_type and obj.properties.get("exam_type") != exam_type:
                continue
            
            matches.append({
                "topic_id": obj.properties.get("topic_id"),
                "title": obj.properties.get("title"),
                "path": obj.properties.get("path"),
                "keywords": obj.properties.get("keywords", []),
                "exam_type": obj.properties.get("exam_type"),
                "score": getattr(obj.metadata, "score", 0.0),
            })
        
        return matches

    def clear_collection(self) -> None:
        if self._client.collections.exists(COLLECTION_NAME):
            self._client.collections.delete(COLLECTION_NAME)
        self._ensure_collection()
