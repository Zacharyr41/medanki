"""Automated retraining scheduler for model improvement."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Protocol


class IFeedbackRepository(Protocol):
    async def get_feedback_count_since(self, since: datetime) -> int: ...
    async def get_correction_rate(self) -> float: ...


class IEmbeddingTuner(Protocol):
    async def has_sufficient_data(self) -> bool: ...
    async def start_training_job(self, training_data_uri: str, output_dir: str) -> str: ...


class IExperimentService(Protocol):
    async def create_experiment(self, **kwargs: Any) -> Any: ...


class IMetricsService(Protocol):
    async def get_accuracy_trend(self, window_days: int) -> list[float]: ...


def kl_divergence(p: list[float], q: list[float]) -> float:
    kl = 0.0
    for pi, qi in zip(p, q, strict=True):
        if pi > 0 and qi > 0:
            kl += pi * math.log(pi / qi)
    return kl


def create_schedule(
    frequency: str,
    time_of_day: str = "03:00",
    day_of_week: str | None = None,
) -> dict:
    hour, minute = map(int, time_of_day.split(":"))

    schedule = {
        "frequency": frequency,
        "hour": hour,
        "minute": minute,
    }

    if frequency == "weekly" and day_of_week:
        schedule["day"] = day_of_week

    return schedule


def calculate_next_run(schedule: dict) -> datetime:
    now = datetime.now()
    hour = schedule.get("hour", 3)
    minute = schedule.get("minute", 0)

    next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

    if next_run <= now:
        next_run += timedelta(days=1)

    if schedule.get("frequency") == "weekly":
        days_map = {
            "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
            "friday": 4, "saturday": 5, "sunday": 6,
        }
        target_day = days_map.get(schedule.get("day", "sunday"), 6)
        current_day = next_run.weekday()
        days_ahead = (target_day - current_day) % 7
        if days_ahead == 0 and next_run <= now:
            days_ahead = 7
        next_run += timedelta(days=days_ahead)

    return next_run


@dataclass
class RetrainingJob:
    job_id: str
    started_at: datetime
    status: str = "running"
    completed_at: datetime | None = None


class RetrainingScheduler:
    def __init__(
        self,
        feedback_repo: IFeedbackRepository,
        embedding_tuner: IEmbeddingTuner,
        experiment_service: IExperimentService | None = None,
        min_new_feedback: int = 100,
        max_correction_rate: float = 0.20,
        last_retrain_time: datetime | None = None,
    ):
        self._feedback_repo = feedback_repo
        self._embedding_tuner = embedding_tuner
        self._experiment_service = experiment_service
        self._min_new_feedback = min_new_feedback
        self._max_correction_rate = max_correction_rate
        self._last_retrain_time = last_retrain_time or datetime.now() - timedelta(days=30)
        self._history: list[dict] = []

    async def should_trigger_retraining(self) -> bool:
        feedback_count = await self._feedback_repo.get_feedback_count_since(
            self._last_retrain_time
        )
        correction_rate = await self._feedback_repo.get_correction_rate()

        if feedback_count >= self._min_new_feedback:
            return True

        return correction_rate > self._max_correction_rate

    async def start_retraining(self) -> str:
        has_data = await self._embedding_tuner.has_sufficient_data()
        if not has_data:
            raise ValueError("Insufficient training data")

        job_id = await self._embedding_tuner.start_training_job(
            training_data_uri="gs://medanki-training/data.jsonl",
            output_dir="gs://medanki-training/output",
        )

        self._history.append({
            "job_id": job_id,
            "started_at": datetime.now(),
            "status": "running",
        })

        self._last_retrain_time = datetime.now()
        return job_id

    async def deploy_with_experiment(self, model_uri: str) -> str:
        if not self._experiment_service:
            raise ValueError("Experiment service not configured")

        experiment = await self._experiment_service.create_experiment(
            name=f"model_retrain_{datetime.now().strftime('%Y%m%d')}",
            variant_a="current_model",
            variant_b=model_uri,
            traffic_split=0.5,
        )

        return experiment.id

    def get_retraining_history(self) -> list[dict]:
        return self._history


class AccuracyDeclineTrigger:
    def __init__(
        self,
        metrics_service: IMetricsService,
        decline_threshold: float = 0.05,
        window_days: int = 7,
    ):
        self._metrics_service = metrics_service
        self._decline_threshold = decline_threshold
        self._window_days = window_days

    async def check(self) -> bool:
        trend = await self._metrics_service.get_accuracy_trend(self._window_days)

        if len(trend) < 2:
            return False

        max_accuracy = max(trend)
        current_accuracy = trend[-1]
        decline = max_accuracy - current_accuracy

        return decline > self._decline_threshold


class DataDriftTrigger:
    def __init__(self, drift_threshold: float = 0.1):
        self._drift_threshold = drift_threshold

    def check_drift(
        self,
        baseline_dist: list[float],
        current_dist: list[float],
    ) -> bool:
        kl = kl_divergence(current_dist, baseline_dist)
        return kl > self._drift_threshold


class RetrainingPipeline:
    def __init__(
        self,
        gcs_client: Any,
        bucket_name: str,
    ):
        self._gcs_client = gcs_client
        self._bucket_name = bucket_name

    async def export_training_data(self, data: list[dict]) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        blob_name = f"training_data_{timestamp}.jsonl"

        content = "\n".join(json.dumps(d) for d in data)

        bucket = self._gcs_client.bucket(self._bucket_name)
        blob = bucket.blob(blob_name)
        blob.upload_from_string(content)

        return f"gs://{self._bucket_name}/{blob_name}"

    def validate_model(
        self,
        metrics: dict,
        min_accuracy: float = 0.75,
        max_latency: float = 500,
    ) -> bool:
        accuracy = metrics.get("accuracy", 0)
        latency = metrics.get("latency_p50", float("inf"))

        if accuracy < min_accuracy:
            return False

        return latency <= max_latency
