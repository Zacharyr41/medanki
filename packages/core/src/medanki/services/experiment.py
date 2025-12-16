"""A/B testing experiment service for classification improvement."""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol


class IExperimentRepository(Protocol):
    async def get_experiment(self, experiment_id: str) -> Any: ...
    async def create_experiment(self, **kwargs: Any) -> Any: ...
    async def list_active_experiments(self) -> list[Any]: ...
    async def record_exposure(self, user_id: str, experiment_id: str, variant: str) -> None: ...
    async def record_outcome(self, user_id: str, experiment_id: str, metric_name: str, value: float) -> None: ...
    async def update_experiment_status(self, experiment_id: str, status: str) -> None: ...


class IMetricsService(Protocol):
    async def get_experiment_metrics(self, experiment_id: str) -> dict: ...


class IMetricsRepository(Protocol):
    async def get_metrics(self, experiment_id: str, variant: str) -> dict: ...
    async def record_feedback(self, **kwargs: Any) -> None: ...


def hash_assignment(user_id: str, experiment_id: str) -> float:
    combined = f"{user_id}:{experiment_id}"
    hash_bytes = hashlib.md5(combined.encode()).digest()
    hash_int = int.from_bytes(hash_bytes[:8], byteorder="big")
    return (hash_int % 10000) / 10000


def chi_square_test(observed_a: dict, observed_b: dict) -> tuple[float, float]:
    total_a = observed_a["success"] + observed_a["failure"]
    total_b = observed_b["success"] + observed_b["failure"]
    total = total_a + total_b

    success_rate = (observed_a["success"] + observed_b["success"]) / total
    failure_rate = 1 - success_rate

    expected_a_success = total_a * success_rate
    expected_a_failure = total_a * failure_rate
    expected_b_success = total_b * success_rate
    expected_b_failure = total_b * failure_rate

    chi2 = 0.0
    chi2 += (observed_a["success"] - expected_a_success) ** 2 / expected_a_success
    chi2 += (observed_a["failure"] - expected_a_failure) ** 2 / expected_a_failure
    chi2 += (observed_b["success"] - expected_b_success) ** 2 / expected_b_success
    chi2 += (observed_b["failure"] - expected_b_failure) ** 2 / expected_b_failure

    p_value = math.exp(-chi2 / 2) if chi2 < 10 else 0.001
    return chi2, p_value


def t_test(
    mean_a: float,
    std_a: float,
    n_a: int,
    mean_b: float,
    std_b: float,
    n_b: int,
) -> tuple[float, float]:
    se = math.sqrt((std_a ** 2 / n_a) + (std_b ** 2 / n_b))
    if se == 0:
        return 0.0, 1.0
    t_stat = (mean_b - mean_a) / se

    p_value = 2 * (1 - _normal_cdf(abs(t_stat)))
    return t_stat, p_value


def _normal_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def cohens_d(mean_a: float, std_a: float, mean_b: float, std_b: float) -> float:
    pooled_std = math.sqrt((std_a ** 2 + std_b ** 2) / 2)
    if pooled_std == 0:
        return 0.0
    return (mean_b - mean_a) / pooled_std


def calculate_sample_size(
    effect_size: float,
    alpha: float = 0.05,
    power: float = 0.8,
) -> int:
    z_alpha = 1.96
    z_beta = 0.84

    n = 2 * ((z_alpha + z_beta) ** 2) / (effect_size ** 2)
    return int(math.ceil(n))


def create_classifier_experiment_config(
    baseline_model: str,
    challenger_model: str,
) -> dict:
    return {
        "variant_a": {"model": baseline_model},
        "variant_b": {"model": challenger_model},
    }


def create_threshold_experiment_config(
    baseline_threshold: float,
    challenger_threshold: float,
) -> dict:
    return {
        "variant_a": {"threshold": baseline_threshold},
        "variant_b": {"threshold": challenger_threshold},
    }


@dataclass
class ExperimentResult:
    p_value: float
    is_significant: bool
    winner: str | None
    effect_size: float
    confidence_interval: tuple[float, float]


class ExperimentService:
    def __init__(
        self,
        experiment_repo: IExperimentRepository,
        metrics_service: IMetricsService | None = None,
        auto_stop: bool = False,
        min_samples: int = 1000,
        significance_threshold: float = 0.05,
    ):
        self._experiment_repo = experiment_repo
        self._metrics_service = metrics_service
        self._auto_stop = auto_stop
        self._min_samples = min_samples
        self._significance_threshold = significance_threshold

    async def create_experiment(
        self,
        name: str,
        variant_a: str,
        variant_b: str,
        traffic_split: float = 0.5,
    ) -> Any:
        return await self._experiment_repo.create_experiment(
            name=name,
            variant_a=variant_a,
            variant_b=variant_b,
            traffic_split=traffic_split,
            start_time=datetime.now(),
            status="running",
        )

    async def get_variant(self, user_id: str, experiment_id: str) -> str:
        experiment = await self._experiment_repo.get_experiment(experiment_id)
        hash_value = hash_assignment(user_id, experiment_id)
        traffic_split = getattr(experiment, "traffic_split", 0.5)

        if hash_value < traffic_split:
            return "variant_a"
        return "variant_b"

    async def record_exposure(
        self,
        user_id: str,
        experiment_id: str,
        variant: str,
    ) -> None:
        await self._experiment_repo.record_exposure(user_id, experiment_id, variant)

    async def record_outcome(
        self,
        user_id: str,
        experiment_id: str,
        metric_name: str,
        value: float,
    ) -> None:
        await self._experiment_repo.record_outcome(
            user_id, experiment_id, metric_name, value
        )

    async def analyze_experiment(self, experiment_id: str) -> dict:
        if not self._metrics_service:
            return {"error": "No metrics service configured"}

        metrics = await self._metrics_service.get_experiment_metrics(experiment_id)

        a_metrics = metrics.get("variant_a", {})
        b_metrics = metrics.get("variant_b", {})

        a_accuracy = a_metrics.get("accuracy", 0)
        b_accuracy = b_metrics.get("accuracy", 0)
        a_samples = a_metrics.get("samples", 0)
        b_samples = b_metrics.get("samples", 0)

        std_a = 0.1
        std_b = 0.1

        _, p_value = t_test(a_accuracy, std_a, a_samples, b_accuracy, std_b, b_samples)

        is_significant = p_value < self._significance_threshold
        winner = None
        if is_significant:
            winner = "variant_b" if b_accuracy > a_accuracy else "variant_a"

        return {
            "p_value": p_value,
            "is_significant": is_significant,
            "winner": winner,
            "effect_size": cohens_d(a_accuracy, std_a, b_accuracy, std_b),
        }

    async def check_and_maybe_stop(self, experiment_id: str) -> None:
        if not self._auto_stop or not self._metrics_service:
            return

        metrics = await self._metrics_service.get_experiment_metrics(experiment_id)

        a_samples = metrics.get("variant_a", {}).get("samples", 0)
        b_samples = metrics.get("variant_b", {}).get("samples", 0)

        if a_samples < self._min_samples or b_samples < self._min_samples:
            return

        result = await self.analyze_experiment(experiment_id)

        if result.get("is_significant"):
            await self._experiment_repo.update_experiment_status(
                experiment_id, "completed"
            )


class ExperimentMetricsCollector:
    def __init__(self, metrics_repo: IMetricsRepository):
        self._metrics_repo = metrics_repo

    async def collect_classification_metrics(
        self,
        experiment_id: str,
        variant: str,
    ) -> dict:
        return await self._metrics_repo.get_metrics(experiment_id, variant)

    async def record_feedback(
        self,
        experiment_id: str,
        variant: str,
        feedback_type: str,
        topic_id: str,
    ) -> None:
        await self._metrics_repo.record_feedback(
            experiment_id=experiment_id,
            variant=variant,
            feedback_type=feedback_type,
            topic_id=topic_id,
        )
