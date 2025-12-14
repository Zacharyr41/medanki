# API Reference

Base URL: `http://localhost:8000`

## Endpoints

### Health Check

```
GET /health
```

Returns API health status.

**Response**
```json
{
  "status": "healthy"
}
```

---

### Preview Cards

```
GET /api/jobs/{job_id}/preview
```

Retrieve generated cards for a completed job with filtering and pagination.

**Path Parameters**
| Parameter | Type   | Description |
|-----------|--------|-------------|
| job_id    | string | Job identifier |

**Query Parameters**
| Parameter | Type    | Default | Description |
|-----------|---------|---------|-------------|
| limit     | integer | 20      | Cards per page (1-100) |
| offset    | integer | 0       | Pagination offset |
| type      | string  | null    | Filter by card type: `cloze`, `vignette`, `basic_qa` |
| topic     | string  | null    | Filter by topic tag |
| status    | string  | null    | Filter by status: `pending`, `approved`, `rejected` |

**Response**
```json
{
  "cards": [
    {
      "id": "card_abc123",
      "type": "cloze",
      "text": "The {{c1::mitochondria}} is the powerhouse of the cell.",
      "tags": ["#MCAT::Biology::Cell_Biology"],
      "topics": ["1A"],
      "status": "pending",
      "source": "chunk_xyz789"
    },
    {
      "id": "card_def456",
      "type": "vignette",
      "text": "A 45-year-old man presents with...",
      "tags": ["#AK_Step1_v12::Cardiovascular"],
      "topics": ["Cardiology"],
      "status": "pending",
      "source": "chunk_uvw012",
      "front": "A 45-year-old man presents with crushing chest pain...",
      "answer": "Acute myocardial infarction",
      "explanation": "ST elevation in leads V1-V4 indicates anterior MI.",
      "distinguishing_feature": "Troponin elevation with ST changes"
    }
  ],
  "total": 150,
  "limit": 20,
  "offset": 0
}
```

**Error Responses**
| Code | Description |
|------|-------------|
| 404  | Job not found |
| 409  | Job not complete |

---

### Download Deck

```
GET /api/jobs/{job_id}/download
```

Download the generated Anki deck as an .apkg file.

**Path Parameters**
| Parameter | Type   | Description |
|-----------|--------|-------------|
| job_id    | string | Job identifier |

**Response**
- Content-Type: `application/octet-stream`
- Content-Disposition: `attachment; filename="medanki_{job_id}.apkg"`

**Error Responses**
| Code | Description |
|------|-------------|
| 404  | Job not found |
| 409  | Job not complete |

---

### Regenerate Deck

```
POST /api/jobs/{job_id}/regenerate
```

Create a new processing job with modified options.

**Path Parameters**
| Parameter | Type   | Description |
|-----------|--------|-------------|
| job_id    | string | Original job identifier |

**Request Body**
```json
{
  "deck_name": "Custom Deck Name",
  "include_tags": ["cardiology", "neurology"],
  "exclude_tags": ["anatomy"]
}
```

| Field        | Type     | Description |
|--------------|----------|-------------|
| deck_name    | string?  | Custom deck name |
| include_tags | string[]? | Only include cards with these tags |
| exclude_tags | string[]? | Exclude cards with these tags |

**Response**
```json
{
  "job_id": "job_new123"
}
```

**Error Responses**
| Code | Description |
|------|-------------|
| 404  | Job not found |

---

### Job Statistics

```
GET /api/jobs/{job_id}/stats
```

Get statistics for a completed job.

**Path Parameters**
| Parameter | Type   | Description |
|-----------|--------|-------------|
| job_id    | string | Job identifier |

**Response**
```json
{
  "counts": {
    "total": 150,
    "cloze": 100,
    "vignette": 45,
    "basic_qa": 5
  },
  "topics": {
    "cardiology": 30,
    "neurology": 25,
    "anatomy": 20
  },
  "timing": {
    "created_at": "2024-01-15T10:30:00Z",
    "completed_at": "2024-01-15T10:32:45Z",
    "duration_seconds": 165.0
  }
}
```

**Error Responses**
| Code | Description |
|------|-------------|
| 404  | Job not found |
| 409  | Job not complete |

---

## Error Codes

All errors return JSON with this structure:

```json
{
  "detail": "Error message describing the issue"
}
```

| HTTP Code | Meaning |
|-----------|---------|
| 400       | Bad Request - Invalid parameters |
| 404       | Not Found - Resource doesn't exist |
| 409       | Conflict - Job not in expected state |
| 422       | Validation Error - Invalid request body |
| 500       | Internal Server Error |

---

## Schemas

### CardPreview

```typescript
interface CardPreview {
  id: string;
  type: "cloze" | "vignette" | "basic_qa";
  text: string;
  tags: string[];
  topics: string[];
  status: "pending" | "approved" | "rejected";
  source?: string;
  front?: string;        // vignette only
  answer?: string;       // vignette only
  explanation?: string;  // vignette only
  distinguishing_feature?: string;  // vignette only
}
```

### PreviewResponse

```typescript
interface PreviewResponse {
  cards: CardPreview[];
  total: number;
  limit: number;
  offset: number;
}
```

### CardCounts

```typescript
interface CardCounts {
  total: number;
  cloze: number;
  vignette: number;
  basic_qa: number;
}
```

### TimingInfo

```typescript
interface TimingInfo {
  created_at: string;  // ISO 8601
  completed_at: string;
  duration_seconds: number;
}
```

### StatsResponse

```typescript
interface StatsResponse {
  counts: CardCounts;
  topics: Record<string, number>;
  timing: TimingInfo;
}
```

---

## OpenAPI Documentation

Interactive API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
