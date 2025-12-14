from functools import lru_cache
from typing import Any

from .workers.processor import BackgroundProcessor
from .workers.queue import JobQueue
from .workers.runner import BackgroundRunner


_queue: JobQueue | None = None
_processor: BackgroundProcessor | None = None
_runner: BackgroundRunner | None = None


def get_queue() -> JobQueue:
    global _queue
    if _queue is None:
        _queue = JobQueue()
    return _queue


def get_processor(
    ingestion_service: Any,
    chunking_service: Any,
    classification_service: Any,
    generation_service: Any,
    export_service: Any,
    store: Any,
    connection_manager: Any,
) -> BackgroundProcessor:
    global _processor
    if _processor is None:
        _processor = BackgroundProcessor(
            ingestion_service=ingestion_service,
            chunking_service=chunking_service,
            classification_service=classification_service,
            generation_service=generation_service,
            export_service=export_service,
            store=store,
            connection_manager=connection_manager,
        )
    return _processor


def get_runner(
    queue: JobQueue,
    processor: BackgroundProcessor,
    poll_interval: float = 1.0,
) -> BackgroundRunner:
    global _runner
    if _runner is None:
        _runner = BackgroundRunner(
            queue=queue,
            processor=processor,
            poll_interval=poll_interval,
        )
    return _runner


def reset_dependencies() -> None:
    global _queue, _processor, _runner
    _queue = None
    _processor = None
    _runner = None
