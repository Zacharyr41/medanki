from pathlib import Path
from typing import Any, Protocol


class IIngestionService(Protocol):
    def ingest(self, file_path: str) -> Any: ...


class IChunkingService(Protocol):
    def chunk(self, content: Any) -> list[Any]: ...


class IClassificationService(Protocol):
    def classify(self, chunks: list[Any]) -> list[dict[str, Any]]: ...


class IGenerationService(Protocol):
    def generate(self, classified_chunks: list[dict[str, Any]]) -> list[dict[str, Any]]: ...


class IExportService(Protocol):
    def export(self, cards: list[dict[str, Any]]) -> str: ...


class IStore(Protocol):
    def get_job(self, job_id: str) -> dict[str, Any]: ...
    def update_job(self, job_id: str, **kwargs: Any) -> None: ...


class IConnectionManager(Protocol):
    async def broadcast(self, message: dict[str, Any]) -> None: ...


class BackgroundProcessor:
    STAGES = ["ingestion", "chunking", "classification", "generation", "export"]

    def __init__(
        self,
        ingestion_service: IIngestionService,
        chunking_service: IChunkingService,
        classification_service: IClassificationService,
        generation_service: IGenerationService,
        export_service: IExportService,
        store: IStore,
        connection_manager: IConnectionManager,
    ):
        self.ingestion_service = ingestion_service
        self.chunking_service = chunking_service
        self.classification_service = classification_service
        self.generation_service = generation_service
        self.export_service = export_service
        self.store = store
        self.connection_manager = connection_manager

    async def process_job(self, job_id: str) -> None:
        job = self.store.get_job(job_id)
        file_path = job.get("file_path", "")
        cleanup_temp = job.get("cleanup_temp", False)

        try:
            self.store.update_job(job_id, status="processing")
            await self._broadcast_progress(job_id, 0, "starting")

            content = await self._ingest(job_id, file_path)
            chunks = await self._chunk(job_id, content)
            classified = await self._classify(job_id, chunks)
            cards = await self._generate(job_id, classified)
            await self._export(job_id, cards)

            self.store.update_job(job_id, status="completed")
            await self._broadcast_progress(job_id, 100, "completed")

        except Exception as e:
            self.store.update_job(job_id, status="failed", error=str(e))
            await self._broadcast_progress(job_id, 0, "failed", error=str(e))

        finally:
            if cleanup_temp and file_path:
                self._cleanup_temp_file(file_path)

    async def _ingest(self, job_id: str, file_path: str) -> Any:
        self.store.update_job(job_id, progress=20, stage="ingestion")
        await self._broadcast_progress(job_id, 20, "ingestion")
        return self.ingestion_service.ingest(file_path)

    async def _chunk(self, job_id: str, content: Any) -> list[Any]:
        self.store.update_job(job_id, progress=40, stage="chunking")
        await self._broadcast_progress(job_id, 40, "chunking")
        return self.chunking_service.chunk(content)

    async def _classify(self, job_id: str, chunks: list[Any]) -> list[dict[str, Any]]:
        self.store.update_job(job_id, progress=60, stage="classification")
        await self._broadcast_progress(job_id, 60, "classification")
        return self.classification_service.classify(chunks)

    async def _generate(
        self, job_id: str, classified: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        self.store.update_job(job_id, progress=80, stage="generation")
        await self._broadcast_progress(job_id, 80, "generation")
        return self.generation_service.generate(classified)

    async def _export(self, job_id: str, cards: list[dict[str, Any]]) -> str:
        self.store.update_job(job_id, progress=100, stage="export")
        await self._broadcast_progress(job_id, 100, "export")
        return self.export_service.export(cards)

    async def _broadcast_progress(
        self, job_id: str, progress: int, stage: str, error: str | None = None
    ) -> None:
        message = {
            "type": "job_progress",
            "job_id": job_id,
            "progress": progress,
            "stage": stage,
        }
        if error:
            message["error"] = error
        await self.connection_manager.broadcast(message)

    def _cleanup_temp_file(self, file_path: str) -> None:
        path = Path(file_path)
        if path.exists():
            path.unlink()
