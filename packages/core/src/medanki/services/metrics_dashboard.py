"""Metrics dashboard for classification performance monitoring."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol


class IMetricsRepository(Protocol):
    async def get_classification_metrics(self) -> dict: ...
    async def get_feedback_summary(self) -> dict: ...
    async def get_metrics_time_series(self, days: int) -> list[dict]: ...
    async def get_topic_metrics(self) -> list[dict]: ...
    async def get_latest_metrics(self) -> dict: ...
    async def get_exam_type_metrics(self) -> dict: ...
    async def get_confusion_matrix(self) -> dict: ...


class IExperimentRepository(Protocol):
    async def list_experiments(self) -> list[dict]: ...


def calculate_accuracy(tp: int, tn: int, fp: int, fn: int) -> float:
    total = tp + tn + fp + fn
    if total == 0:
        return 0.0
    return (tp + tn) / total


def calculate_precision(tp: int, fp: int) -> float:
    if tp + fp == 0:
        return 0.0
    return tp / (tp + fp)


def calculate_recall(tp: int, fn: int) -> float:
    if tp + fn == 0:
        return 0.0
    return tp / (tp + fn)


def calculate_f1(precision: float, recall: float) -> float:
    if precision + recall == 0:
        return 0.0
    return 2 * (precision * recall) / (precision + recall)


class MetricsDashboard:
    def __init__(
        self,
        metrics_repo: IMetricsRepository,
        experiment_repo: IExperimentRepository | None = None,
    ):
        self._metrics_repo = metrics_repo
        self._experiment_repo = experiment_repo

    async def get_classification_summary(self) -> dict:
        return await self._metrics_repo.get_classification_metrics()

    async def get_feedback_summary(self) -> dict:
        summary = await self._metrics_repo.get_feedback_summary()

        total = summary.get("total_positive", 0) + summary.get("total_negative", 0)
        corrections = summary.get("total_corrections", 0)

        summary["correction_rate"] = corrections / total if total > 0 else 0.0

        return summary

    async def get_accuracy_trend(self, days: int = 30) -> list[dict]:
        return await self._metrics_repo.get_metrics_time_series(days)

    async def get_topic_breakdown(self) -> list[dict]:
        topics = await self._metrics_repo.get_topic_metrics()
        return sorted(topics, key=lambda x: x.get("accuracy", 0), reverse=True)

    async def get_experiment_summary(self) -> list[dict]:
        if not self._experiment_repo:
            return []
        return await self._experiment_repo.list_experiments()

    async def get_exam_type_metrics(self) -> dict:
        return await self._metrics_repo.get_exam_type_metrics()

    async def get_exam_confusion_matrix(self) -> dict:
        return await self._metrics_repo.get_confusion_matrix()

    async def get_full_dashboard(self) -> dict:
        classification = await self.get_classification_summary()
        feedback = await self.get_feedback_summary()

        return {
            "classification": classification,
            "feedback": feedback,
            "timestamp": datetime.now().isoformat(),
        }

    async def format_for_frontend(self) -> dict:
        classification = await self.get_classification_summary()
        feedback = await self.get_feedback_summary()

        cards = [
            {
                "title": "Accuracy",
                "value": f"{classification.get('accuracy', 0):.1%}",
                "type": "metric",
            },
            {
                "title": "Precision",
                "value": f"{classification.get('precision', 0):.1%}",
                "type": "metric",
            },
            {
                "title": "Total Feedback",
                "value": feedback.get("total_positive", 0) + feedback.get("total_negative", 0),
                "type": "count",
            },
        ]

        charts = [
            {"type": "accuracy_trend", "title": "Accuracy Over Time"},
            {"type": "topic_breakdown", "title": "Topic Performance"},
            {"type": "exam_confusion", "title": "Exam Type Confusion"},
        ]

        return {"cards": cards, "charts": charts}


class AlertMonitor:
    def __init__(
        self,
        metrics_repo: IMetricsRepository,
        accuracy_threshold: float = 0.70,
        correction_rate_threshold: float = 0.20,
    ):
        self._metrics_repo = metrics_repo
        self._accuracy_threshold = accuracy_threshold
        self._correction_rate_threshold = correction_rate_threshold

    async def check_alerts(self) -> list[dict]:
        alerts = []

        metrics = await self._metrics_repo.get_latest_metrics()
        accuracy = metrics.get("accuracy", 1.0)

        if accuracy < self._accuracy_threshold:
            alerts.append({
                "type": "accuracy_below_threshold",
                "message": f"Accuracy ({accuracy:.1%}) is below threshold ({self._accuracy_threshold:.1%})",
                "severity": "warning",
                "timestamp": datetime.now().isoformat(),
            })

        return alerts
