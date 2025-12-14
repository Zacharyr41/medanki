from collections import deque
from threading import Lock


class JobQueue:
    def __init__(self):
        self._queue: deque[str] = deque()
        self._cancelled: set[str] = set()
        self._current: str | None = None
        self._lock = Lock()

    def enqueue(self, job_id: str) -> None:
        with self._lock:
            self._queue.append(job_id)

    def dequeue(self) -> str | None:
        with self._lock:
            while self._queue:
                job_id = self._queue.popleft()
                if job_id not in self._cancelled:
                    self._current = job_id
                    return job_id
            return None

    def cancel(self, job_id: str) -> bool:
        with self._lock:
            if job_id in self._queue or job_id == self._current:
                self._cancelled.add(job_id)
                return True
            return False

    def is_processing(self) -> bool:
        with self._lock:
            return self._current is not None

    def complete_current(self) -> None:
        with self._lock:
            self._current = None

    def is_cancelled(self, job_id: str) -> bool:
        with self._lock:
            return job_id in self._cancelled

    def size(self) -> int:
        with self._lock:
            return len(self._queue)

    def clear(self) -> None:
        with self._lock:
            self._queue.clear()
            self._cancelled.clear()
            self._current = None
