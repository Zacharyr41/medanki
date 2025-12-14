import asyncio
from typing import Callable, Awaitable

from .processor import BackgroundProcessor
from .queue import JobQueue


class BackgroundRunner:
    def __init__(
        self,
        queue: JobQueue,
        processor: BackgroundProcessor,
        poll_interval: float = 1.0,
    ):
        self.queue = queue
        self.processor = processor
        self.poll_interval = poll_interval
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _run_loop(self) -> None:
        while self._running:
            job_id = self.queue.dequeue()
            if job_id:
                try:
                    if not self.queue.is_cancelled(job_id):
                        await self.processor.process_job(job_id)
                finally:
                    self.queue.complete_current()
            else:
                await asyncio.sleep(self.poll_interval)

    @property
    def is_running(self) -> bool:
        return self._running
