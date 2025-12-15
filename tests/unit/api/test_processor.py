import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from medanki_api.workers.processor import BackgroundProcessor
from medanki_api.workers.queue import JobQueue


class TestJobExecution:
    @pytest.fixture
    def mock_services(self):
        return {
            "ingestion_service": Mock(),
            "chunking_service": Mock(),
            "classification_service": Mock(),
            "generation_service": Mock(),
            "export_service": Mock(),
            "store": Mock(),
            "connection_manager": AsyncMock(),
        }

    @pytest.fixture
    def processor(self, mock_services):
        return BackgroundProcessor(**mock_services)

    @pytest.mark.asyncio
    async def test_processes_pending_job(self, processor, mock_services):
        job_id = str(uuid4())
        mock_services["store"].get_job.return_value = {
            "id": job_id,
            "status": "pending",
            "file_path": "/tmp/test.pdf",
        }

        await processor.process_job(job_id)

        mock_services["store"].get_job.assert_called_once_with(job_id)

    @pytest.mark.asyncio
    async def test_updates_job_status(self, processor, mock_services):
        job_id = str(uuid4())
        mock_services["store"].get_job.return_value = {
            "id": job_id,
            "status": "pending",
            "file_path": "/tmp/test.pdf",
        }

        await processor.process_job(job_id)

        mock_services["store"].update_job.assert_any_call(job_id, status="processing")

    @pytest.mark.asyncio
    async def test_completes_job(self, processor, mock_services):
        job_id = str(uuid4())
        mock_services["store"].get_job.return_value = {
            "id": job_id,
            "status": "pending",
            "file_path": "/tmp/test.pdf",
        }

        await processor.process_job(job_id)

        mock_services["store"].update_job.assert_any_call(job_id, status="completed")

    @pytest.mark.asyncio
    async def test_records_error_on_failure(self, processor, mock_services):
        job_id = str(uuid4())
        mock_services["store"].get_job.return_value = {
            "id": job_id,
            "status": "pending",
            "file_path": "/tmp/test.pdf",
        }
        mock_services["ingestion_service"].ingest.side_effect = Exception("Ingestion failed")

        await processor.process_job(job_id)

        mock_services["store"].update_job.assert_any_call(
            job_id, status="failed", error="Ingestion failed"
        )


class TestPipelineStages:
    @pytest.fixture
    def mock_services(self):
        return {
            "ingestion_service": Mock(),
            "chunking_service": Mock(),
            "classification_service": Mock(),
            "generation_service": Mock(),
            "export_service": Mock(),
            "store": Mock(),
            "connection_manager": AsyncMock(),
        }

    @pytest.fixture
    def processor(self, mock_services):
        return BackgroundProcessor(**mock_services)

    @pytest.mark.asyncio
    async def test_runs_ingestion_stage(self, processor, mock_services):
        job_id = str(uuid4())
        mock_services["store"].get_job.return_value = {
            "id": job_id,
            "status": "pending",
            "file_path": "/tmp/test.pdf",
        }

        await processor.process_job(job_id)

        mock_services["ingestion_service"].ingest.assert_called_once()

    @pytest.mark.asyncio
    async def test_runs_chunking_stage(self, processor, mock_services):
        job_id = str(uuid4())
        mock_services["store"].get_job.return_value = {
            "id": job_id,
            "status": "pending",
            "file_path": "/tmp/test.pdf",
        }
        mock_services["ingestion_service"].ingest.return_value = "document content"

        await processor.process_job(job_id)

        mock_services["chunking_service"].chunk.assert_called_once()

    @pytest.mark.asyncio
    async def test_runs_classification_stage(self, processor, mock_services):
        job_id = str(uuid4())
        mock_services["store"].get_job.return_value = {
            "id": job_id,
            "status": "pending",
            "file_path": "/tmp/test.pdf",
        }
        mock_services["ingestion_service"].ingest.return_value = "document content"
        mock_services["chunking_service"].chunk.return_value = ["chunk1", "chunk2"]

        await processor.process_job(job_id)

        mock_services["classification_service"].classify.assert_called_once()

    @pytest.mark.asyncio
    async def test_runs_generation_stage(self, processor, mock_services):
        job_id = str(uuid4())
        mock_services["store"].get_job.return_value = {
            "id": job_id,
            "status": "pending",
            "file_path": "/tmp/test.pdf",
        }
        mock_services["ingestion_service"].ingest.return_value = "document content"
        mock_services["chunking_service"].chunk.return_value = ["chunk1", "chunk2"]
        mock_services["classification_service"].classify.return_value = [
            {"chunk": "chunk1", "category": "anatomy"}
        ]

        await processor.process_job(job_id)

        mock_services["generation_service"].generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_runs_export_stage(self, processor, mock_services):
        job_id = str(uuid4())
        mock_services["store"].get_job.return_value = {
            "id": job_id,
            "status": "pending",
            "file_path": "/tmp/test.pdf",
        }
        mock_services["ingestion_service"].ingest.return_value = "document content"
        mock_services["chunking_service"].chunk.return_value = ["chunk1", "chunk2"]
        mock_services["classification_service"].classify.return_value = [
            {"chunk": "chunk1", "category": "anatomy"}
        ]
        mock_services["generation_service"].generate.return_value = [{"card": "test card"}]

        await processor.process_job(job_id)

        mock_services["export_service"].export.assert_called_once()


class TestProgressReporting:
    @pytest.fixture
    def mock_services(self):
        return {
            "ingestion_service": Mock(),
            "chunking_service": Mock(),
            "classification_service": Mock(),
            "generation_service": Mock(),
            "export_service": Mock(),
            "store": Mock(),
            "connection_manager": AsyncMock(),
        }

    @pytest.fixture
    def processor(self, mock_services):
        return BackgroundProcessor(**mock_services)

    @pytest.mark.asyncio
    async def test_reports_stage_progress(self, processor, mock_services):
        job_id = str(uuid4())
        mock_services["store"].get_job.return_value = {
            "id": job_id,
            "status": "pending",
            "file_path": "/tmp/test.pdf",
        }

        await processor.process_job(job_id)

        progress_calls = [
            call
            for call in mock_services["store"].update_job.call_args_list
            if "progress" in str(call)
        ]
        assert len(progress_calls) >= 5

    @pytest.mark.asyncio
    async def test_broadcasts_via_websocket(self, processor, mock_services):
        job_id = str(uuid4())
        mock_services["store"].get_job.return_value = {
            "id": job_id,
            "status": "pending",
            "file_path": "/tmp/test.pdf",
        }

        await processor.process_job(job_id)

        mock_services["connection_manager"].broadcast.assert_called()

    @pytest.mark.asyncio
    async def test_progress_is_percentage(self, processor, mock_services):
        job_id = str(uuid4())
        mock_services["store"].get_job.return_value = {
            "id": job_id,
            "status": "pending",
            "file_path": "/tmp/test.pdf",
        }

        await processor.process_job(job_id)

        for call in mock_services["store"].update_job.call_args_list:
            if len(call.args) > 1 or "progress" in call.kwargs:
                progress = call.kwargs.get("progress")
                if progress is not None:
                    assert 0 <= progress <= 100


class TestConcurrency:
    @pytest.fixture
    def queue(self):
        return JobQueue()

    def test_processes_one_at_a_time(self, queue):
        job1 = str(uuid4())
        job2 = str(uuid4())
        queue.enqueue(job1)
        queue.enqueue(job2)

        first = queue.dequeue()
        assert first == job1
        assert queue.is_processing()

    def test_queue_order_fifo(self, queue):
        job1 = str(uuid4())
        job2 = str(uuid4())
        job3 = str(uuid4())

        queue.enqueue(job1)
        queue.enqueue(job2)
        queue.enqueue(job3)

        assert queue.dequeue() == job1
        queue.complete_current()
        assert queue.dequeue() == job2
        queue.complete_current()
        assert queue.dequeue() == job3

    def test_handles_cancellation(self, queue):
        job1 = str(uuid4())
        job2 = str(uuid4())

        queue.enqueue(job1)
        queue.enqueue(job2)

        queue.cancel(job2)

        queue.dequeue()
        queue.complete_current()
        result = queue.dequeue()
        assert result is None


class TestResourceCleanup:
    @pytest.fixture
    def mock_services(self):
        return {
            "ingestion_service": Mock(),
            "chunking_service": Mock(),
            "classification_service": Mock(),
            "generation_service": Mock(),
            "export_service": Mock(),
            "store": Mock(),
            "connection_manager": AsyncMock(),
        }

    @pytest.fixture
    def processor(self, mock_services):
        return BackgroundProcessor(**mock_services)

    @pytest.mark.asyncio
    async def test_cleans_temp_files(self, processor, mock_services):
        job_id = str(uuid4())

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp_path = tmp.name
            tmp.write(b"test content")

        mock_services["store"].get_job.return_value = {
            "id": job_id,
            "status": "pending",
            "file_path": tmp_path,
            "cleanup_temp": True,
        }

        await processor.process_job(job_id)

        assert not Path(tmp_path).exists()

    @pytest.mark.asyncio
    async def test_cleans_on_failure(self, processor, mock_services):
        job_id = str(uuid4())

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp_path = tmp.name
            tmp.write(b"test content")

        mock_services["store"].get_job.return_value = {
            "id": job_id,
            "status": "pending",
            "file_path": tmp_path,
            "cleanup_temp": True,
        }
        mock_services["ingestion_service"].ingest.side_effect = Exception("Failed")

        await processor.process_job(job_id)

        assert not Path(tmp_path).exists()
