# MedAnki Web Interface Design
## Lightweight Drag-and-Drop Flashcard Generator

A minimal web interface for uploading medical notes and downloading generated Anki decks. Designed to run locally or deploy cheaply on GCP.

---

## Table of Contents

1. [Design Goals](#design-goals)
2. [Architecture Options](#architecture-options)
3. [Recommended Stack](#recommended-stack)
4. [UI/UX Design](#uiux-design)
5. [API Design](#api-design)
6. [Implementation Details](#implementation-details)
7. [Deployment Options](#deployment-options)
8. [Cost Analysis](#cost-analysis)
9. [Security Considerations](#security-considerations)
10. [Implementation Roadmap](#implementation-roadmap)

---

## Design Goals

### Must Have
- Drag-and-drop file upload (PDF, audio, markdown)
- Progress indication during processing
- Download link for generated `.apkg` file
- Works on desktop and mobile browsers
- Can run entirely locally (localhost)

### Nice to Have
- Multiple file batch processing
- Preview generated cards before download
- Edit/delete cards before export
- Save processing history
- Share decks via link

### Non-Goals (for v1)
- User accounts/authentication
- Cloud storage of decks
- Collaborative editing
- Real-time sync with Anki

---

## Architecture Options

### Option A: Python Full-Stack (Recommended for MVP)

```
┌─────────────────────────────────────────────────────────────┐
│                     Browser (Client)                         │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Single Page Application                 │    │
│  │          (HTMX + Alpine.js + Tailwind)              │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP / WebSocket
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Upload    │  │   Process   │  │   Download          │  │
│  │   Endpoint  │  │   Worker    │  │   Endpoint          │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│                           │                                  │
│                           ▼                                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              MedAnki Core Library                    │    │
│  │    (Ingestion → Processing → Generation → Export)   │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

**Pros:**
- Single language (Python everywhere)
- Reuses existing MedAnki core
- HTMX = minimal JavaScript
- Easy to run locally

**Cons:**
- Less reactive UI than React
- HTMX has learning curve

---

### Option B: Python Backend + React Frontend

```
┌─────────────────────────────────────────────────────────────┐
│                     Browser (Client)                         │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              React SPA (Vite)                        │    │
│  │          + TailwindCSS + React Query                │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ REST API / WebSocket
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                           │
│                    (Same as Option A)                        │
└─────────────────────────────────────────────────────────────┘
```

**Pros:**
- More reactive UI
- Better for complex interactions (card editing)
- Large ecosystem

**Cons:**
- Two languages to maintain
- Heavier client bundle
- More complex build

---

### Option C: Gradio (Quickest to Build)

```python
import gradio as gr

def process_file(file, exam_type):
    # Call MedAnki core
    result = pipeline.run(file.name, exam_type)
    return result.output_path

demo = gr.Interface(
    fn=process_file,
    inputs=[
        gr.File(label="Upload PDF/Audio"),
        gr.Dropdown(["MCAT", "USMLE Step 1"], label="Exam")
    ],
    outputs=gr.File(label="Download Deck")
)

demo.launch()
```

**Pros:**
- Build in 30 minutes
- Built-in file handling
- Easy sharing via Gradio Cloud

**Cons:**
- Limited UI customization
- Looks like a "demo" not a "product"
- Less control over UX

---

## Recommended Stack

For a balance of speed, customization, and maintainability:

### Frontend
| Component | Choice | Rationale |
|-----------|--------|-----------|
| **Framework** | HTMX + Alpine.js | Minimal JS, server-driven |
| **Styling** | Tailwind CSS | Rapid UI development |
| **Icons** | Heroicons | Matches Tailwind aesthetic |
| **File Upload** | Dropzone.js | Best drag-drop UX |

### Backend
| Component | Choice | Rationale |
|-----------|--------|-----------|
| **Framework** | FastAPI | Async, automatic OpenAPI docs |
| **Task Queue** | None (MVP) / Celery (scale) | Keep simple initially |
| **WebSocket** | FastAPI native | Real-time progress |
| **Templates** | Jinja2 | Server-rendered HTML for HTMX |

### Storage
| Component | Choice | Rationale |
|-----------|--------|-----------|
| **Uploads** | Local filesystem / GCS | Simple, cheap |
| **Jobs** | SQLite | No separate DB needed |
| **Generated Decks** | Temp files + cleanup | Auto-delete after 24h |

---

## UI/UX Design

### Main Screen (Upload)

```
┌─────────────────────────────────────────────────────────────────┐
│  MedAnki                                            [Settings]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                                                         │   │
│   │     ┌─────────┐                                        │   │
│   │     │  📄 📎  │   Drag & drop your files here         │   │
│   │     └─────────┘   or click to browse                   │   │
│   │                                                         │   │
│   │     Supported: PDF, MP3, M4A, MD, TXT                  │   │
│   │                                                         │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │  Target Exam                                            │   │
│   │  ┌──────────────────────────────────────────────────┐  │   │
│   │  │  ● USMLE Step 1    ○ USMLE Step 2    ○ MCAT     │  │   │
│   │  └──────────────────────────────────────────────────┘  │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │  Cards per section: [3 ▼]    Include vignettes: [✓]    │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│                    [ Generate Flashcards ]                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Processing Screen

```
┌─────────────────────────────────────────────────────────────────┐
│  MedAnki                                                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   Processing: lecture_biochem.pdf                               │
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │  ████████████████████░░░░░░░░░░░░░░░░░░░░  45%         │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│   ✓ Extracting text from PDF                                   │
│   ✓ Chunking content (12 chunks)                               │
│   ✓ Classifying topics                                         │
│   ◐ Generating flashcards... (18/36 cards)                     │
│   ○ Validating cards                                           │
│   ○ Building Anki deck                                         │
│                                                                 │
│   Estimated time remaining: ~2 minutes                          │
│                                                                 │
│                        [ Cancel ]                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Download Screen

```
┌─────────────────────────────────────────────────────────────────┐
│  MedAnki                                                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│                          ✓                                      │
│                                                                 │
│               Successfully generated 36 cards!                  │
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                                                         │   │
│   │    📦 lecture_biochem_cards.apkg                       │   │
│   │    36 cards • 1.2 MB • USMLE Step 1                    │   │
│   │                                                         │   │
│   │              [ ⬇️ Download Deck ]                       │   │
│   │                                                         │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│   Preview (first 5 cards):                                      │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ 1. The rate-limiting enzyme of glycolysis is {{c1::___}}│   │
│   │ 2. {{c1::___}} is the committed step of fatty acid...  │   │
│   │ 3. A 45-year-old man presents with chest pain...       │   │
│   │ ...                                                     │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│           [ Generate Another ]    [ Edit Cards ]                │
│                                                                 │
│   ⚠️ Download expires in 24 hours                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Mobile Layout

```
┌─────────────────────┐
│ MedAnki        [☰]  │
├─────────────────────┤
│                     │
│  ┌───────────────┐  │
│  │   📄          │  │
│  │  Tap to       │  │
│  │  upload       │  │
│  └───────────────┘  │
│                     │
│  Target Exam        │
│  ┌───────────────┐  │
│  │ USMLE Step 1 ▼│  │
│  └───────────────┘  │
│                     │
│  Cards/chunk: [3]   │
│                     │
│  ┌───────────────┐  │
│  │   Generate    │  │
│  └───────────────┘  │
│                     │
└─────────────────────┘
```

---

## API Design

### Endpoints

```yaml
openapi: 3.0.0
info:
  title: MedAnki Web API
  version: 1.0.0

paths:
  /api/upload:
    post:
      summary: Upload file for processing
      requestBody:
        content:
          multipart/form-data:
            schema:
              type: object
              properties:
                file:
                  type: string
                  format: binary
                exam_type:
                  type: string
                  enum: [mcat, usmle_step1, usmle_step2]
                cards_per_chunk:
                  type: integer
                  default: 3
                include_vignettes:
                  type: boolean
                  default: true
      responses:
        202:
          description: Processing started
          content:
            application/json:
              schema:
                type: object
                properties:
                  job_id:
                    type: string
                  status_url:
                    type: string

  /api/jobs/{job_id}:
    get:
      summary: Get job status
      responses:
        200:
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: string
                    enum: [pending, processing, completed, failed]
                  progress:
                    type: integer
                  current_step:
                    type: string
                  cards_generated:
                    type: integer
                  download_url:
                    type: string

  /api/jobs/{job_id}/download:
    get:
      summary: Download generated deck
      responses:
        200:
          content:
            application/octet-stream:
              schema:
                type: string
                format: binary

  /api/jobs/{job_id}/preview:
    get:
      summary: Preview generated cards
      responses:
        200:
          content:
            application/json:
              schema:
                type: array
                items:
                  type: object
                  properties:
                    text:
                      type: string
                    extra:
                      type: string
                    tags:
                      type: array
                      items:
                        type: string

  /ws/jobs/{job_id}:
    description: WebSocket for real-time progress updates
```

### WebSocket Messages

```typescript
// Server → Client
interface ProgressUpdate {
  type: "progress";
  data: {
    step: string;
    progress: number;  // 0-100
    cards_generated: number;
    message: string;
  };
}

interface CompletedUpdate {
  type: "completed";
  data: {
    download_url: string;
    card_count: number;
    preview: Card[];
  };
}

interface ErrorUpdate {
  type: "error";
  data: {
    message: string;
    recoverable: boolean;
  };
}
```

---

## Implementation Details

### Project Structure

```
medanki-web/
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
│
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app
│   ├── config.py            # Settings
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py        # API endpoints
│   │   └── websocket.py     # WebSocket handlers
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   └── processor.py     # Wraps MedAnki core
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py       # Pydantic models
│   │
│   └── templates/
│       ├── base.html
│       ├── index.html
│       ├── processing.html
│       └── download.html
│
├── static/
│   ├── css/
│   │   └── styles.css       # Tailwind output
│   ├── js/
│   │   └── app.js           # Alpine.js components
│   └── uploads/             # Temp upload storage
│
└── tests/
    └── test_api.py
```

### FastAPI Backend

```python
# app/main.py
from fastapi import FastAPI, UploadFile, File, Form, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse, HTMLResponse
import uuid
import asyncio

app = FastAPI(title="MedAnki Web")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# In-memory job storage (use Redis for production)
jobs: dict[str, dict] = {}


@app.get("/", response_class=HTMLResponse)
async def home(request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    exam_type: str = Form("usmle_step1"),
    cards_per_chunk: int = Form(3),
    include_vignettes: bool = Form(True),
):
    job_id = str(uuid.uuid4())
    
    # Save uploaded file
    upload_path = f"static/uploads/{job_id}_{file.filename}"
    with open(upload_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    # Initialize job
    jobs[job_id] = {
        "status": "pending",
        "progress": 0,
        "file_path": upload_path,
        "exam_type": exam_type,
        "cards_per_chunk": cards_per_chunk,
        "include_vignettes": include_vignettes,
    }
    
    # Start processing in background
    asyncio.create_task(process_job(job_id))
    
    return {
        "job_id": job_id,
        "status_url": f"/api/jobs/{job_id}",
    }


async def process_job(job_id: str):
    """Background task to process the uploaded file."""
    job = jobs[job_id]
    job["status"] = "processing"
    
    try:
        # Import MedAnki core
        from medanki.pipeline import FlashcardPipeline
        
        pipeline = FlashcardPipeline()
        
        # Process with progress callback
        def progress_callback(step: str, progress: int, cards: int):
            job["current_step"] = step
            job["progress"] = progress
            job["cards_generated"] = cards
        
        result = await pipeline.run_async(
            input_path=job["file_path"],
            exam_type=job["exam_type"],
            cards_per_chunk=job["cards_per_chunk"],
            include_vignettes=job["include_vignettes"],
            progress_callback=progress_callback,
        )
        
        job["status"] = "completed"
        job["progress"] = 100
        job["output_path"] = result.output_path
        job["card_count"] = result.card_count
        job["preview"] = result.cards[:5]  # First 5 cards
        
    except Exception as e:
        job["status"] = "failed"
        job["error"] = str(e)


@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")
    
    job = jobs[job_id]
    response = {
        "status": job["status"],
        "progress": job.get("progress", 0),
        "current_step": job.get("current_step", ""),
        "cards_generated": job.get("cards_generated", 0),
    }
    
    if job["status"] == "completed":
        response["download_url"] = f"/api/jobs/{job_id}/download"
        response["card_count"] = job["card_count"]
    
    if job["status"] == "failed":
        response["error"] = job.get("error", "Unknown error")
    
    return response


@app.get("/api/jobs/{job_id}/download")
async def download_deck(job_id: str):
    if job_id not in jobs or jobs[job_id]["status"] != "completed":
        raise HTTPException(404, "Deck not ready")
    
    return FileResponse(
        jobs[job_id]["output_path"],
        media_type="application/octet-stream",
        filename=f"medanki_{job_id[:8]}.apkg"
    )


@app.websocket("/ws/jobs/{job_id}")
async def websocket_progress(websocket: WebSocket, job_id: str):
    await websocket.accept()
    
    if job_id not in jobs:
        await websocket.close(code=4004)
        return
    
    last_progress = -1
    while True:
        job = jobs[job_id]
        
        if job["progress"] != last_progress:
            await websocket.send_json({
                "type": "progress",
                "data": {
                    "step": job.get("current_step", ""),
                    "progress": job["progress"],
                    "cards_generated": job.get("cards_generated", 0),
                }
            })
            last_progress = job["progress"]
        
        if job["status"] == "completed":
            await websocket.send_json({
                "type": "completed",
                "data": {
                    "download_url": f"/api/jobs/{job_id}/download",
                    "card_count": job["card_count"],
                }
            })
            break
        
        if job["status"] == "failed":
            await websocket.send_json({
                "type": "error",
                "data": {"message": job.get("error", "Unknown error")}
            })
            break
        
        await asyncio.sleep(0.5)
    
    await websocket.close()
```

### Frontend (HTMX + Alpine.js)

```html
<!-- app/templates/index.html -->
{% extends "base.html" %}

{% block content %}
<div x-data="uploadForm()" class="max-w-2xl mx-auto p-6">
    
    <!-- Drop Zone -->
    <div 
        x-on:drop.prevent="handleDrop($event)"
        x-on:dragover.prevent="isDragging = true"
        x-on:dragleave="isDragging = false"
        :class="isDragging ? 'border-blue-500 bg-blue-50' : 'border-gray-300'"
        class="border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-colors"
        x-on:click="$refs.fileInput.click()"
    >
        <input 
            type="file" 
            x-ref="fileInput" 
            x-on:change="handleFileSelect($event)"
            accept=".pdf,.mp3,.m4a,.md,.txt"
            class="hidden"
        >
        
        <div x-show="!selectedFile">
            <svg class="mx-auto h-12 w-12 text-gray-400" stroke="currentColor" fill="none" viewBox="0 0 48 48">
                <path d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
            <p class="mt-4 text-lg text-gray-600">
                Drag & drop your files here
            </p>
            <p class="mt-2 text-sm text-gray-500">
                or click to browse
            </p>
            <p class="mt-4 text-xs text-gray-400">
                Supported: PDF, MP3, M4A, MD, TXT
            </p>
        </div>
        
        <div x-show="selectedFile" class="text-left">
            <div class="flex items-center gap-3 p-3 bg-gray-50 rounded">
                <svg class="h-8 w-8 text-red-500" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" />
                </svg>
                <div>
                    <p class="font-medium" x-text="selectedFile?.name"></p>
                    <p class="text-sm text-gray-500" x-text="formatSize(selectedFile?.size)"></p>
                </div>
                <button 
                    x-on:click.stop="selectedFile = null"
                    class="ml-auto text-gray-400 hover:text-red-500"
                >
                    ✕
                </button>
            </div>
        </div>
    </div>
    
    <!-- Options -->
    <div class="mt-6 space-y-4">
        <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
                Target Exam
            </label>
            <div class="flex gap-4">
                <label class="flex items-center">
                    <input type="radio" x-model="examType" value="usmle_step1" class="mr-2">
                    USMLE Step 1
                </label>
                <label class="flex items-center">
                    <input type="radio" x-model="examType" value="usmle_step2" class="mr-2">
                    USMLE Step 2
                </label>
                <label class="flex items-center">
                    <input type="radio" x-model="examType" value="mcat" class="mr-2">
                    MCAT
                </label>
            </div>
        </div>
        
        <div class="flex gap-6">
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">
                    Cards per section
                </label>
                <select x-model="cardsPerChunk" class="border rounded px-3 py-2">
                    <option value="1">1</option>
                    <option value="2">2</option>
                    <option value="3">3</option>
                    <option value="5">5</option>
                </select>
            </div>
            
            <div class="flex items-center">
                <label class="flex items-center">
                    <input type="checkbox" x-model="includeVignettes" class="mr-2">
                    Include clinical vignettes
                </label>
            </div>
        </div>
    </div>
    
    <!-- Submit -->
    <button
        x-on:click="submitForm()"
        :disabled="!selectedFile || isSubmitting"
        :class="!selectedFile || isSubmitting ? 'bg-gray-300' : 'bg-blue-600 hover:bg-blue-700'"
        class="mt-8 w-full py-3 px-4 rounded-lg text-white font-medium transition-colors"
    >
        <span x-show="!isSubmitting">Generate Flashcards</span>
        <span x-show="isSubmitting">Uploading...</span>
    </button>
    
</div>

<script>
function uploadForm() {
    return {
        selectedFile: null,
        isDragging: false,
        examType: 'usmle_step1',
        cardsPerChunk: '3',
        includeVignettes: true,
        isSubmitting: false,
        
        handleDrop(event) {
            this.isDragging = false;
            const files = event.dataTransfer.files;
            if (files.length > 0) {
                this.selectedFile = files[0];
            }
        },
        
        handleFileSelect(event) {
            this.selectedFile = event.target.files[0];
        },
        
        formatSize(bytes) {
            if (!bytes) return '';
            const mb = bytes / (1024 * 1024);
            return mb.toFixed(1) + ' MB';
        },
        
        async submitForm() {
            if (!this.selectedFile) return;
            
            this.isSubmitting = true;
            
            const formData = new FormData();
            formData.append('file', this.selectedFile);
            formData.append('exam_type', this.examType);
            formData.append('cards_per_chunk', this.cardsPerChunk);
            formData.append('include_vignettes', this.includeVignettes);
            
            try {
                const response = await fetch('/api/upload', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                window.location.href = `/processing/${data.job_id}`;
                
            } catch (error) {
                alert('Upload failed: ' + error.message);
                this.isSubmitting = false;
            }
        }
    }
}
</script>
{% endblock %}
```

### Processing Page with WebSocket

```html
<!-- app/templates/processing.html -->
{% extends "base.html" %}

{% block content %}
<div x-data="processingView('{{ job_id }}')" class="max-w-2xl mx-auto p-6">
    
    <h2 class="text-xl font-semibold mb-6">
        Processing: {{ filename }}
    </h2>
    
    <!-- Progress Bar -->
    <div class="mb-6">
        <div class="h-4 bg-gray-200 rounded-full overflow-hidden">
            <div 
                class="h-full bg-blue-500 transition-all duration-300"
                :style="`width: ${progress}%`"
            ></div>
        </div>
        <p class="mt-2 text-right text-sm text-gray-600" x-text="`${progress}%`"></p>
    </div>
    
    <!-- Steps -->
    <div class="space-y-3">
        <template x-for="step in steps" :key="step.id">
            <div class="flex items-center gap-3">
                <div x-show="step.status === 'completed'" class="text-green-500">✓</div>
                <div x-show="step.status === 'active'" class="text-blue-500 animate-spin">◐</div>
                <div x-show="step.status === 'pending'" class="text-gray-300">○</div>
                <span :class="step.status === 'pending' ? 'text-gray-400' : ''" x-text="step.label"></span>
                <span x-show="step.detail" class="text-sm text-gray-500" x-text="step.detail"></span>
            </div>
        </template>
    </div>
    
    <!-- Cards Counter -->
    <div x-show="cardsGenerated > 0" class="mt-6 p-4 bg-blue-50 rounded-lg">
        <p class="text-blue-800">
            Generated <span class="font-bold" x-text="cardsGenerated"></span> cards so far...
        </p>
    </div>
    
    <!-- Error -->
    <div x-show="error" class="mt-6 p-4 bg-red-50 border border-red-200 rounded-lg">
        <p class="text-red-800" x-text="error"></p>
        <button 
            x-on:click="window.location.href = '/'"
            class="mt-3 text-red-600 underline"
        >
            Try again
        </button>
    </div>
    
    <!-- Cancel -->
    <button
        x-show="!completed && !error"
        x-on:click="cancel()"
        class="mt-8 text-gray-500 hover:text-gray-700"
    >
        Cancel
    </button>
    
</div>

<script>
function processingView(jobId) {
    return {
        progress: 0,
        cardsGenerated: 0,
        currentStep: '',
        completed: false,
        error: null,
        steps: [
            { id: 'extract', label: 'Extracting text', status: 'pending', detail: '' },
            { id: 'chunk', label: 'Chunking content', status: 'pending', detail: '' },
            { id: 'classify', label: 'Classifying topics', status: 'pending', detail: '' },
            { id: 'generate', label: 'Generating flashcards', status: 'pending', detail: '' },
            { id: 'validate', label: 'Validating cards', status: 'pending', detail: '' },
            { id: 'export', label: 'Building Anki deck', status: 'pending', detail: '' },
        ],
        
        init() {
            this.connectWebSocket();
        },
        
        connectWebSocket() {
            const ws = new WebSocket(`ws://${window.location.host}/ws/jobs/${jobId}`);
            
            ws.onmessage = (event) => {
                const msg = JSON.parse(event.data);
                
                if (msg.type === 'progress') {
                    this.progress = msg.data.progress;
                    this.cardsGenerated = msg.data.cards_generated;
                    this.updateSteps(msg.data.step);
                }
                
                if (msg.type === 'completed') {
                    this.completed = true;
                    this.progress = 100;
                    window.location.href = `/download/${jobId}`;
                }
                
                if (msg.type === 'error') {
                    this.error = msg.data.message;
                }
            };
            
            ws.onerror = () => {
                this.error = 'Connection lost. Please refresh.';
            };
        },
        
        updateSteps(currentStep) {
            const stepMap = {
                'extracting': 0,
                'chunking': 1,
                'classifying': 2,
                'generating': 3,
                'validating': 4,
                'exporting': 5,
            };
            
            const currentIdx = stepMap[currentStep] ?? -1;
            
            this.steps.forEach((step, idx) => {
                if (idx < currentIdx) {
                    step.status = 'completed';
                } else if (idx === currentIdx) {
                    step.status = 'active';
                } else {
                    step.status = 'pending';
                }
            });
        },
        
        cancel() {
            if (confirm('Are you sure you want to cancel?')) {
                fetch(`/api/jobs/${jobId}/cancel`, { method: 'POST' });
                window.location.href = '/';
            }
        }
    }
}
</script>
{% endblock %}
```

---

## Deployment Options

### Option 1: Local Only (Free)

```bash
# Run with uvicorn
uvicorn app.main:app --reload --port 8000

# Or with Docker
docker-compose up
```

Access at `http://localhost:8000`

---

### Option 2: Google Cloud Run (Cheapest Cloud)

**Why Cloud Run:**
- Pay only when processing requests
- Auto-scales to zero
- No server management
- Free tier: 2M requests/month

**Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download scispacy model
RUN pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_lg-0.5.4.tar.gz

# Copy application
COPY . .

# Run
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

**Deploy:**
```bash
# Build and push
gcloud builds submit --tag gcr.io/PROJECT_ID/medanki-web

# Deploy
gcloud run deploy medanki-web \
    --image gcr.io/PROJECT_ID/medanki-web \
    --platform managed \
    --region us-central1 \
    --memory 2Gi \
    --cpu 2 \
    --timeout 600 \
    --set-env-vars ANTHROPIC_API_KEY=xxx \
    --allow-unauthenticated
```

**Estimated cost:**
- Light usage (50 requests/month): ~$0-2
- Medium usage (500 requests/month): ~$5-15
- Heavy usage (5000 requests/month): ~$30-50

---

### Option 3: Fly.io (Simple Alternative)

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Launch
fly launch

# Deploy
fly deploy

# Set secrets
fly secrets set ANTHROPIC_API_KEY=xxx
```

**Estimated cost:** $0-5/month for light usage

---

### Option 4: Railway (Easiest)

1. Connect GitHub repo
2. Railway auto-detects Python
3. Add environment variables
4. Deploy

**Cost:** $5/month hobby plan

---

## Cost Analysis

### Cloud Run Detailed Breakdown

| Component | Cost |
|-----------|------|
| **Compute** (2 vCPU, 2GB) | $0.00002400/vCPU-second |
| **Memory** | $0.00000250/GiB-second |
| **Requests** | $0.40/million |
| **Egress** | $0.12/GB (first 1GB free) |

**Per request estimate (60-second processing):**
- Compute: $0.0029
- Memory: $0.0003
- Request: $0.0000004
- **Total: ~$0.003 per request**

Plus Claude API: ~$0.03-0.05 per request

**Monthly estimates:**

| Usage | Requests | Cloud Run | Claude API | Total |
|-------|----------|-----------|------------|-------|
| Light | 50 | $0.15 | $2.50 | ~$3 |
| Medium | 200 | $0.60 | $10 | ~$11 |
| Heavy | 1000 | $3.00 | $50 | ~$53 |

---

## Security Considerations

### File Upload Security

```python
# Validate file type
ALLOWED_EXTENSIONS = {'.pdf', '.mp3', '.m4a', '.md', '.txt'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

def validate_upload(file: UploadFile):
    # Check extension
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"File type {ext} not allowed")
    
    # Check size (read in chunks)
    size = 0
    for chunk in file.file:
        size += len(chunk)
        if size > MAX_FILE_SIZE:
            raise HTTPException(400, "File too large (max 50MB)")
    file.file.seek(0)
    
    # Check MIME type
    import magic
    mime = magic.from_buffer(file.file.read(1024), mime=True)
    file.file.seek(0)
    
    allowed_mimes = {'application/pdf', 'audio/mpeg', 'text/plain', 'text/markdown'}
    if mime not in allowed_mimes:
        raise HTTPException(400, f"Invalid file type: {mime}")
```

### Rate Limiting

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/api/upload")
@limiter.limit("10/hour")  # 10 uploads per hour per IP
async def upload_file(...):
    ...
```

### Cleanup Job

```python
import asyncio
from datetime import datetime, timedelta

async def cleanup_old_files():
    """Delete files older than 24 hours."""
    while True:
        cutoff = datetime.now() - timedelta(hours=24)
        
        for job_id, job in list(jobs.items()):
            if job.get("created_at", datetime.now()) < cutoff:
                # Delete files
                if job.get("file_path"):
                    Path(job["file_path"]).unlink(missing_ok=True)
                if job.get("output_path"):
                    Path(job["output_path"]).unlink(missing_ok=True)
                # Remove job
                del jobs[job_id]
        
        await asyncio.sleep(3600)  # Run hourly

@app.on_event("startup")
async def start_cleanup():
    asyncio.create_task(cleanup_old_files())
```

---

## Implementation Roadmap

### Week 1: Basic Upload Flow
- [ ] FastAPI project setup
- [ ] File upload endpoint
- [ ] Basic HTML template
- [ ] Local file storage
- [ ] Integration with MedAnki core

### Week 2: Progress & Download
- [ ] WebSocket progress updates
- [ ] Processing status page
- [ ] Download endpoint
- [ ] Job cleanup task

### Week 3: Polish & Deploy
- [ ] Error handling
- [ ] Mobile responsive
- [ ] Rate limiting
- [ ] Docker setup
- [ ] Cloud Run deployment

### Week 4: Enhancements
- [ ] Card preview before download
- [ ] Edit cards interface
- [ ] Batch file upload
- [ ] Processing history

---

## Quick Start Commands

```bash
# 1. Create project
mkdir medanki-web && cd medanki-web
uv init

# 2. Add dependencies
uv add fastapi uvicorn python-multipart jinja2 aiofiles websockets

# 3. Create basic structure
mkdir -p app/{api,templates} static/{css,js,uploads}

# 4. Run locally
uv run uvicorn app.main:app --reload

# 5. Access
open http://localhost:8000
```

---

*Document version: 1.0 | Last updated: December 2025*
