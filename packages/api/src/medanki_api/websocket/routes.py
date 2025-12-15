from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from medanki_api.websocket.manager import ConnectionManager

BASE_THRESHOLD = 0.65
TAXONOMY_DIR = Path(__file__).parent.parent.parent.parent.parent.parent / "data" / "taxonomies"

router = APIRouter()

_manager = ConnectionManager()

STAGES = ["ingesting", "chunking", "classifying", "generating", "exporting"]


async def _send_progress(
    websocket: WebSocket,
    job: dict[str, Any],
    progress: float,
    stage: str,
) -> None:
    if websocket.client_state != WebSocketState.CONNECTED:
        return
    job["progress"] = progress
    job["stage"] = stage
    await websocket.send_json(
        {
            "type": "progress",
            "progress": progress,
            "stage": stage,
        }
    )


async def _process_topic_job(websocket: WebSocket, job: dict[str, Any]) -> None:
    """Process a job that generates cards from a topic description."""
    topic_text = job.get("topic_text", "")
    if not topic_text:
        raise ValueError("No topic text provided")

    await _send_progress(websocket, job, 10, "generating")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    cards: list[dict[str, Any]] = []

    exam = job.get("exam", "USMLE_STEP1")
    card_types_str = job.get("card_types", "cloze,vignette") or "cloze,vignette"
    enabled_types = {t.strip().lower() for t in card_types_str.split(",")}
    generate_cloze = "cloze" in enabled_types
    generate_vignette = "vignette" in enabled_types
    max_cards = job.get("max_cards", 20) or 20

    if api_key:
        from uuid import uuid4

        from medanki.services.llm import ClaudeClient

        client = ClaudeClient(api_key=api_key)

        await _send_progress(websocket, job, 30, "generating")

        cloze_count = max_cards if generate_cloze else 0
        vignette_count = min(max_cards // 4, 5) if generate_vignette else 0

        if generate_cloze and cloze_count > 0:
            try:
                topic_cards = await client.generate_cards_from_topic(
                    topic_prompt=topic_text,
                    count=cloze_count,
                    exam_type=exam,
                )
                await _send_progress(websocket, job, 60, "generating")

                for card_data in topic_cards:
                    cards.append({
                        "id": str(uuid4()),
                        "type": "cloze",
                        "text": card_data.get("text", ""),
                        "topic_id": exam,
                        "topic_title": card_data.get("topic", topic_text[:50]),
                        "source_chunk": f"Generated from topic: {topic_text[:200]}",
                    })
            except Exception as e:
                print(f"Topic cloze generation error: {e}")

        if generate_vignette and vignette_count > 0:
            await _send_progress(websocket, job, 75, "generating")
            try:
                from medanki.generation.vignette import VignetteGenerator

                vignette_generator = VignetteGenerator(llm_client=client)
                vignettes = await vignette_generator.generate(
                    content=f"Create clinical vignettes about: {topic_text}",
                    source_chunk_id=uuid4(),
                    topic_id=exam,
                    num_cards=vignette_count,
                )
                for vcard in vignettes:
                    options_text = " | ".join(
                        f"{opt.letter}. {opt.text}" for opt in vcard.options
                    )
                    cards.append({
                        "id": str(vcard.id),
                        "type": "vignette",
                        "text": f"{vcard.stem}\n\n{vcard.question}",
                        "front": f"{vcard.stem}\n\n{vcard.question}\n\n{options_text}",
                        "answer": vcard.answer,
                        "explanation": vcard.explanation,
                        "topic_id": exam,
                        "topic_title": topic_text[:50],
                        "source_chunk": f"Generated from topic: {topic_text[:200]}",
                    })
            except Exception as e:
                print(f"Topic vignette generation error: {e}")
    else:
        from uuid import uuid4

        for _ in range(min(max_cards, 5)):
            cards.append({
                "id": str(uuid4()),
                "type": "cloze",
                "text": f"{{{{c1::Sample concept}}}} related to {topic_text[:30]}...",
                "topic_id": exam,
                "topic_title": topic_text[:50],
                "source_chunk": f"Generated from topic: {topic_text[:200]}",
            })

    await _send_progress(websocket, job, 90, "exporting")

    job["cards"] = cards
    job["cards_generated"] = len(cards)

    await _send_progress(websocket, job, 100, "exporting")


async def _process_file_job(websocket: WebSocket, job: dict[str, Any]) -> None:
    """Process a job that generates cards from an uploaded file."""
    file_path = job.get("file_path")
    if not file_path or not Path(file_path).exists():
        raise ValueError(f"File not found: {file_path}")

    path = Path(file_path)

    # Stage 1: Ingestion (0-20%)
    await _send_progress(websocket, job, 5, "ingesting")

    from medanki.ingestion.pdf import PDFExtractor
    from medanki.ingestion.text import TextLoader

    if path.suffix.lower() == ".pdf":
        extractor = PDFExtractor()
        document = await asyncio.to_thread(extractor.extract, path)
    else:
        loader = TextLoader()
        document = await asyncio.to_thread(loader.load, path)

    await _send_progress(websocket, job, 20, "ingesting")

    # Stage 2: Chunking (20-40%)
    await _send_progress(websocket, job, 25, "chunking")

    from dataclasses import dataclass

    from medanki.processing.chunker import ChunkingService

    @dataclass
    class ChunkableDoc:
        id: str
        raw_text: str
        sections: list

    chunkable = ChunkableDoc(
        id=str(job.get("id", "doc")),
        raw_text=document.content,
        sections=document.sections,
    )

    chunker = ChunkingService()
    chunks = chunker.chunk(chunkable)

    await _send_progress(websocket, job, 40, "chunking")

    if not chunks:
        job["cards"] = []
        job["cards_generated"] = 0
        return

    # Stage 3: Classification (40-60%)
    await _send_progress(websocket, job, 45, "classifying")
    exam = job.get("exam", "USMLE_STEP1")

    classified_chunks = []
    indexer = None

    try:
        import weaviate
        from weaviate.classes.init import Auth

        weaviate_url = os.environ.get("WEAVIATE_URL", "http://localhost:8080")
        weaviate_api_key = os.environ.get("WEAVIATE_API_KEY")

        if weaviate_url.startswith("https://") and weaviate_api_key:
            weaviate_client = weaviate.connect_to_weaviate_cloud(
                cluster_url=weaviate_url,
                auth_credentials=Auth.api_key(weaviate_api_key),
            )
        else:
            weaviate_client = weaviate.connect_to_local(port=8080)

        from medanki.services.taxonomy_indexer import TaxonomyIndexer

        indexer = TaxonomyIndexer(weaviate_client, TAXONOMY_DIR)

        collection = weaviate_client.collections.get("TaxonomyTopic")
        count_result = collection.aggregate.over_all(total_count=True)
        if count_result.total_count == 0:
            indexer.index_exam("USMLE_STEP1")
            indexer.index_exam("MCAT")

        await _send_progress(websocket, job, 50, "classifying")

        for i, chunk in enumerate(chunks):
            progress = 50 + (i / len(chunks)) * 10
            await _send_progress(websocket, job, progress, "classifying")

            results = indexer.search(chunk.text, exam_type=exam, limit=3)

            if results and results[0]["score"] >= BASE_THRESHOLD:
                classified_chunks.append(
                    {
                        "chunk": chunk,
                        "topic_id": results[0]["topic_id"],
                        "topic_title": results[0]["title"],
                        "topic_path": results[0]["path"],
                        "score": results[0]["score"],
                    }
                )
            else:
                classified_chunks.append(
                    {
                        "chunk": chunk,
                        "topic_id": None,
                        "topic_title": None,
                        "topic_path": None,
                        "score": results[0]["score"] if results else 0.0,
                    }
                )

        weaviate_client.close()
    except Exception as e:
        print(f"Classification error (falling back to unclassified): {e}")
        for chunk in chunks:
            classified_chunks.append(
                {
                    "chunk": chunk,
                    "topic_id": exam,
                    "topic_title": None,
                    "topic_path": None,
                    "score": 0.0,
                }
            )

    relevant_chunks = [c for c in classified_chunks if c["topic_id"] is not None]
    if not relevant_chunks:
        relevant_chunks = classified_chunks

    await _send_progress(websocket, job, 60, "classifying")

    # Stage 4: Generation (60-90%)
    await _send_progress(websocket, job, 65, "generating")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    cards: list[dict[str, Any]] = []

    card_types_str = job.get("card_types", "cloze,vignette") or "cloze,vignette"
    enabled_types = {t.strip().lower() for t in card_types_str.split(",")}
    generate_cloze = "cloze" in enabled_types
    generate_vignette = "vignette" in enabled_types

    if api_key:
        from uuid import uuid4

        from medanki.generation.cloze import ClozeGenerator
        from medanki.generation.vignette import VignetteGenerator
        from medanki.services.llm import ClaudeClient

        client = ClaudeClient(api_key=api_key)
        cloze_generator = ClozeGenerator(llm_client=client) if generate_cloze else None
        vignette_generator = VignetteGenerator(llm_client=client) if generate_vignette else None

        max_cards = job.get("max_cards", 20) or 20
        num_chunks = len(relevant_chunks) or 1
        cards_per_chunk = max(1, max_cards // num_chunks)
        cloze_per_chunk = min(cards_per_chunk, 3) if generate_cloze else 0
        vignette_per_chunk = 1 if generate_vignette else 0

        for i, classified in enumerate(relevant_chunks):
            chunk = classified["chunk"]
            topic_id = classified["topic_id"]
            topic_title = classified["topic_title"]
            topic_path = classified["topic_path"]

            progress = 65 + (i / len(relevant_chunks)) * 25
            await _send_progress(websocket, job, progress, "generating")

            topic_context = f"Topic: {topic_path}" if topic_path else None
            chunk_id = uuid4()

            if cloze_generator:
                try:
                    generated = await cloze_generator.generate(
                        content=chunk.text,
                        source_chunk_id=chunk_id,
                        topic_id=topic_id or exam,
                        topic_context=topic_context,
                        num_cards=cloze_per_chunk,
                    )
                    for card in generated:
                        cards.append(
                            {
                                "id": str(card.id),
                                "type": "cloze",
                                "text": card.text,
                                "topic_id": topic_id or exam,
                                "topic_title": topic_title,
                                "source_chunk": chunk.text[:200],
                            }
                        )
                except Exception as e:
                    print(f"Cloze generation error for chunk {i}: {e}")

            if vignette_generator:
                try:
                    vignettes = await vignette_generator.generate(
                        content=chunk.text,
                        source_chunk_id=chunk_id,
                        topic_id=topic_id or exam,
                        num_cards=vignette_per_chunk,
                    )
                    for vcard in vignettes:
                        options_text = " | ".join(
                            f"{opt.letter}. {opt.text}" for opt in vcard.options
                        )
                        cards.append(
                            {
                                "id": str(vcard.id),
                                "type": "vignette",
                                "text": f"{vcard.stem}\n\n{vcard.question}",
                                "front": f"{vcard.stem}\n\n{vcard.question}\n\n{options_text}",
                                "answer": vcard.answer,
                                "explanation": vcard.explanation,
                                "topic_id": topic_id or exam,
                                "topic_title": topic_title,
                                "source_chunk": chunk.text[:200],
                            }
                        )
                except Exception as e:
                    print(f"Vignette generation error for chunk {i}: {e}")
    else:
        for i, classified in enumerate(relevant_chunks[:5]):
            chunk = classified["chunk"]
            cards.append(
                {
                    "id": f"card_{i}",
                    "type": "cloze",
                    "text": f"{{{{c1::{chunk.text[:50]}}}}} is important medical content.",
                    "topic_id": classified["topic_id"] or exam,
                    "topic_title": classified["topic_title"],
                    "source_chunk": chunk.text[:200],
                }
            )

    await _send_progress(websocket, job, 90, "generating")

    # Stage 5: Export (90-100%)
    await _send_progress(websocket, job, 95, "exporting")

    job["cards"] = cards
    job["cards_generated"] = len(cards)

    await _send_progress(websocket, job, 100, "exporting")


async def _process_job(websocket: WebSocket, job: dict[str, Any]) -> None:
    """Dispatch job processing based on input type."""
    input_type = job.get("input_type", "file")

    if input_type == "topic":
        await _process_topic_job(websocket, job)
    else:
        await _process_file_job(websocket, job)


@router.websocket("/api/ws/{job_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    job_id: str,
) -> None:
    job_storage: dict[str, Any] = websocket.app.state.job_storage
    job = job_storage.get(job_id)

    if job is None:
        await websocket.close(code=4004, reason="Job not found")
        return

    await websocket.accept()
    await _manager.connect(job_id, websocket)

    try:
        if job.get("status") == "completed":
            await websocket.send_json(
                {
                    "type": "complete",
                    "progress": 100,
                    "cards_generated": job.get("cards_generated", 0),
                }
            )
            return

        job["status"] = "processing"
        job["stage"] = "generating" if job.get("input_type") == "topic" else "ingesting"
        job["progress"] = 0

        await _process_job(websocket, job)

        job["status"] = "completed"
        job["updated_at"] = datetime.now(UTC).isoformat()

        await websocket.send_json(
            {
                "type": "complete",
                "progress": 100,
                "cards_generated": job.get("cards_generated", 0),
            }
        )

    except WebSocketDisconnect:
        pass
    except Exception as e:
        job["status"] = "failed"
        job["error_message"] = str(e)
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.send_json(
                {
                    "type": "error",
                    "error": str(e),
                }
            )
    finally:
        await _manager.disconnect(job_id, websocket)
