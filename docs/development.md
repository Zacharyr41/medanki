# Development Guide

## Setting Up the Development Environment

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- Node.js 18+ (for frontend)
- Git

### Initial Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/your-org/medanki.git
   cd medanki
   ```

2. Install Python dependencies:
   ```bash
   uv sync
   ```

3. Install frontend dependencies:
   ```bash
   cd web
   npm install
   cd ..
   ```

4. Verify installation:
   ```bash
   uv run pytest --collect-only
   ```

## Running the Application

### Development Servers

**API Server** (with auto-reload):
```bash
uv run uvicorn medanki_api.main:app --reload --port 8000
```

**Web Frontend** (with HMR):
```bash
cd web
npm run dev
```

### Running Both Simultaneously

Use two terminal windows or a process manager like `tmux`:

```bash
# Terminal 1
uv run uvicorn medanki_api.main:app --reload

# Terminal 2
cd web && npm run dev
```

## Testing

### Running All Tests

```bash
uv run pytest
```

### Running Specific Test Files

```bash
uv run pytest tests/unit/processing/test_chunker.py
uv run pytest tests/unit/export/test_deck.py
```

### Running Tests with Coverage

```bash
uv run pytest --cov=packages --cov-report=html
open htmlcov/index.html
```

### Running Tests by Marker

```bash
uv run pytest -m "not slow"
uv run pytest -m integration
```

### Test Structure

```
tests/
├── conftest.py           # Shared fixtures
├── unit/
│   ├── processing/       # Chunker, classifier tests
│   ├── export/           # Deck, APKG, tags tests
│   ├── storage/          # SQLite tests
│   ├── api/              # Route tests
│   └── models/           # Data model tests
└── integration/          # End-to-end tests
```

## Code Style

### Python

We use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
# Check for issues
uv run ruff check .

# Auto-fix issues
uv run ruff check --fix .

# Format code
uv run ruff format .
```

Configuration in `pyproject.toml`:
```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM", "C4"]
```

### TypeScript/JavaScript

For the web frontend:

```bash
cd web
npm run lint
npm run format
```

### Commit Messages

Follow conventional commits:
```
type(scope): description

feat(api): add card filtering by topic
fix(chunker): preserve medical terms during split
docs(readme): update installation instructions
test(export): add deck builder edge cases
```

## Project Structure

```
medanki/
├── packages/
│   ├── __init__.py
│   ├── core/                    # Core library
│   │   ├── __init__.py
│   │   └── src/
│   │       └── medanki/
│   │           ├── __init__.py
│   │           ├── processing/  # Document processing
│   │           │   ├── chunker.py
│   │           │   └── classifier.py
│   │           ├── export/      # Anki export
│   │           │   ├── apkg.py
│   │           │   ├── deck.py
│   │           │   ├── models.py
│   │           │   └── tags.py
│   │           └── storage/     # Data persistence
│   │               ├── models.py
│   │               └── sqlite.py
│   └── api/                     # REST API
│       ├── __init__.py
│       └── src/
│           └── medanki_api/
│               ├── __init__.py
│               ├── main.py
│               ├── routes/
│               │   ├── download.py
│               │   └── preview.py
│               └── schemas/
│                   └── preview.py
├── web/                         # React frontend
│   ├── src/
│   ├── package.json
│   └── vite.config.ts
├── tests/                       # Test suite
├── docs/                        # Documentation
├── pyproject.toml
└── uv.lock
```

## Adding New Features

### 1. Core Module Changes

1. Write tests first in `tests/unit/`
2. Implement in `packages/core/src/medanki/`
3. Run tests: `uv run pytest tests/unit/your_module/`
4. Update type hints and docstrings

### 2. API Endpoint Changes

1. Define schemas in `packages/api/src/medanki_api/schemas/`
2. Implement route in `packages/api/src/medanki_api/routes/`
3. Register in `main.py`
4. Write tests in `tests/unit/api/`

### 3. Frontend Changes

1. Work in `web/src/`
2. Follow React/TypeScript conventions
3. Run `npm run lint` before committing

## Debugging

### API Debugging

Enable debug logging:
```bash
LOG_LEVEL=DEBUG uv run uvicorn medanki_api.main:app --reload
```

### Database Inspection

```bash
sqlite3 medanki.db
.tables
.schema cards
SELECT * FROM jobs LIMIT 5;
```

### Test Debugging

```bash
uv run pytest -v --tb=long tests/unit/processing/test_chunker.py
uv run pytest --pdb  # Drop into debugger on failure
```

## Contributing Guidelines

1. **Fork** the repository
2. **Create a branch**: `git checkout -b feature/your-feature`
3. **Write tests** for new functionality
4. **Ensure all tests pass**: `uv run pytest`
5. **Run linting**: `uv run ruff check --fix .`
6. **Commit** with conventional commit messages
7. **Push** and create a Pull Request

### PR Checklist

- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Linting passes
- [ ] All tests pass
- [ ] Commit messages follow conventions
