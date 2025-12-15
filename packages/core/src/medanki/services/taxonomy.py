"""Taxonomy service for MCAT and USMLE topic management."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class ExamType(Enum):
    MCAT = "MCAT"
    USMLE_STEP1 = "USMLE_STEP1"


@dataclass
class TaxonomyTopic:
    id: str
    title: str
    path: str
    keywords: list[str]
    parent_id: str | None
    exam_type: ExamType
    level: int = 0
    children: list[TaxonomyTopic] = field(default_factory=list)


class TaxonomyService:
    def __init__(self, taxonomy_dir: Path) -> None:
        self._taxonomy_dir = taxonomy_dir
        self._mcat_topics: dict[str, TaxonomyTopic] = {}
        self._usmle_topics: dict[str, TaxonomyTopic] = {}
        self._mcat_loaded = False
        self._usmle_loaded = False
        self._load_taxonomies()

    def _load_taxonomies(self) -> None:
        mcat_path = self._taxonomy_dir / "mcat.json"
        if mcat_path.exists():
            self._load_mcat(mcat_path)

        usmle_path = self._taxonomy_dir / "usmle_step1.json"
        if usmle_path.exists():
            self._load_usmle(usmle_path)

    def _load_mcat(self, path: Path) -> None:
        with open(path) as f:
            data = json.load(f)

        for fc in data.get("foundational_concepts", []):
            fc_topic = TaxonomyTopic(
                id=fc["id"],
                title=fc["title"],
                path=fc["title"],
                keywords=fc.get("keywords", []),
                parent_id=None,
                exam_type=ExamType.MCAT,
                level=0,
            )
            self._mcat_topics[fc["id"]] = fc_topic

            for cat in fc.get("categories", []):
                cat_path = f"{fc['title']} > {cat['title']}"
                cat_topic = TaxonomyTopic(
                    id=cat["id"],
                    title=cat["title"],
                    path=cat_path,
                    keywords=cat.get("keywords", []),
                    parent_id=fc["id"],
                    exam_type=ExamType.MCAT,
                    level=1,
                )
                self._mcat_topics[cat["id"]] = cat_topic
                fc_topic.children.append(cat_topic)

        self._mcat_loaded = True

    def _load_usmle(self, path: Path) -> None:
        with open(path) as f:
            data = json.load(f)

        for sys in data.get("systems", []):
            sys_topic = TaxonomyTopic(
                id=sys["id"],
                title=sys["title"],
                path=sys["title"],
                keywords=sys.get("keywords", []),
                parent_id=None,
                exam_type=ExamType.USMLE_STEP1,
                level=0,
            )
            self._usmle_topics[sys["id"]] = sys_topic

            for topic in sys.get("topics", []):
                topic_path = f"{sys['title']} > {topic['title']}"
                topic_obj = TaxonomyTopic(
                    id=topic["id"],
                    title=topic["title"],
                    path=topic_path,
                    keywords=topic.get("keywords", []),
                    parent_id=sys["id"],
                    exam_type=ExamType.USMLE_STEP1,
                    level=1,
                )
                self._usmle_topics[topic["id"]] = topic_obj
                sys_topic.children.append(topic_obj)

        self._usmle_loaded = True

    @property
    def mcat_loaded(self) -> bool:
        return self._mcat_loaded

    @property
    def usmle_loaded(self) -> bool:
        return self._usmle_loaded

    def get_foundational_concepts(self, exam_type: ExamType) -> list[TaxonomyTopic]:
        if exam_type == ExamType.MCAT:
            return [t for t in self._mcat_topics.values() if t.parent_id is None]
        return []

    def get_content_categories(self, exam_type: ExamType) -> list[TaxonomyTopic]:
        if exam_type == ExamType.MCAT:
            return [t for t in self._mcat_topics.values() if t.parent_id is not None]
        return []

    def get_topic_by_id(self, topic_id: str, exam_type: ExamType) -> TaxonomyTopic | None:
        if exam_type == ExamType.MCAT:
            return self._mcat_topics.get(topic_id)
        elif exam_type == ExamType.USMLE_STEP1:
            return self._usmle_topics.get(topic_id)
        return None

    def get_topics_by_exam(self, exam_type: ExamType) -> list[TaxonomyTopic]:
        if exam_type == ExamType.MCAT:
            return list(self._mcat_topics.values())
        elif exam_type == ExamType.USMLE_STEP1:
            return list(self._usmle_topics.values())
        return []

    def search_topics_by_keyword(self, keyword: str, exam_type: ExamType) -> list[TaxonomyTopic]:
        keyword_lower = keyword.lower()
        topics = self.get_topics_by_exam(exam_type)
        results = []

        for topic in topics:
            if keyword_lower in topic.title.lower():
                results.append(topic)
                continue

            for kw in topic.keywords:
                if keyword_lower in kw.lower():
                    results.append(topic)
                    break

        return results

    def get_topic_path(self, topic_id: str, exam_type: ExamType) -> str | None:
        topic = self.get_topic_by_id(topic_id, exam_type)
        if topic is None:
            return None

        if topic.parent_id is None:
            return topic.title

        parent = self.get_topic_by_id(topic.parent_id, exam_type)
        if parent is None:
            return topic.title

        return f"{parent.id} > {topic.id}"

    def get_all_leaf_topics(self, exam_type: ExamType) -> list[TaxonomyTopic]:
        topics = self.get_topics_by_exam(exam_type)
        return [t for t in topics if t.parent_id is not None]

    async def get_topics(
        self,
        parent_id: str | None = None,
        level: int | None = None,
    ) -> list[TaxonomyTopic]:
        all_topics = list(self._mcat_topics.values()) + list(self._usmle_topics.values())
        results = all_topics

        if parent_id is not None:
            results = [t for t in results if t.parent_id == parent_id]

        if level is not None:
            results = [t for t in results if t.level == level]

        return results

    async def search_topics(
        self,
        query: str,
        limit: int = 10,
    ) -> list[TaxonomyTopic]:
        mcat_results = self.search_topics_by_keyword(query, ExamType.MCAT)
        usmle_results = self.search_topics_by_keyword(query, ExamType.USMLE_STEP1)
        return (mcat_results + usmle_results)[:limit]

    async def get_topic_ancestors(self, topic_id: str) -> list[TaxonomyTopic]:
        topic = self._mcat_topics.get(topic_id) or self._usmle_topics.get(topic_id)
        if topic is None:
            return []

        ancestors = []
        current = topic
        while current.parent_id is not None:
            parent = self._mcat_topics.get(current.parent_id) or self._usmle_topics.get(
                current.parent_id
            )
            if parent is None:
                break
            ancestors.append(parent)
            current = parent

        return list(reversed(ancestors))
