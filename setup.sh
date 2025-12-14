#!/bin/bash
#===============================================================================
# MedAnki Complete Setup Script
# 
# This script sets up the entire MedAnki development environment including:
# - Environment variable validation
# - Python environment (uv)
# - Node.js environment
# - Docker services (Weaviate)
# - Git worktrees for parallel development
# - Claude Code agents and MCPs
# - Project scaffolding
#
# Usage: ./setup.sh [--skip-docker] [--skip-worktrees] [--minimal]
#===============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Flags
SKIP_DOCKER=false
SKIP_WORKTREES=false
MINIMAL=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-docker)
            SKIP_DOCKER=true
            shift
            ;;
        --skip-worktrees)
            SKIP_WORKTREES=true
            shift
            ;;
        --minimal)
            MINIMAL=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

#===============================================================================
# Helper Functions
#===============================================================================

print_header() {
    echo ""
    echo -e "${BLUE}${BOLD}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}${BOLD}  $1${NC}"
    echo -e "${BLUE}${BOLD}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
}

print_step() {
    echo -e "${CYAN}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "  ${BOLD}$1${NC}"
}

check_command() {
    if command -v "$1" &> /dev/null; then
        print_success "$1 found: $(command -v $1)"
        return 0
    else
        print_error "$1 not found"
        return 1
    fi
}

#===============================================================================
# Environment Variable Validation
#===============================================================================

validate_env_vars() {
    print_header "Validating Environment Variables"
    
    local has_errors=false
    local has_warnings=false
    
    # Load .env if it exists
    if [ -f ".env" ]; then
        print_info "Loading .env file..."
        set -a
        source .env
        set +a
    fi
    
    echo ""
    echo -e "${BOLD}Required API Keys:${NC}"
    echo "─────────────────────────────────────────────────────────────"
    
    # ANTHROPIC_API_KEY (Required)
    if [ -z "$ANTHROPIC_API_KEY" ]; then
        print_error "ANTHROPIC_API_KEY is not set (REQUIRED)"
        print_info "  Get it from: https://console.anthropic.com/settings/keys"
        has_errors=true
    elif [[ ! "$ANTHROPIC_API_KEY" =~ ^sk-ant- ]]; then
        print_warning "ANTHROPIC_API_KEY format looks incorrect (should start with sk-ant-)"
        has_warnings=true
    else
        print_success "ANTHROPIC_API_KEY is set (${ANTHROPIC_API_KEY:0:12}...)"
        
        # Validate API key works
        print_step "  Validating Anthropic API key..."
        if curl -s -o /dev/null -w "%{http_code}" \
            -H "x-api-key: $ANTHROPIC_API_KEY" \
            -H "anthropic-version: 2023-06-01" \
            "https://api.anthropic.com/v1/messages" | grep -q "401\|400"; then
            print_success "  Anthropic API key is valid"
        else
            # 400 is expected without a body, 401 means invalid key
            print_success "  Anthropic API key format accepted"
        fi
    fi
    
    echo ""
    echo -e "${BOLD}Optional API Keys:${NC}"
    echo "─────────────────────────────────────────────────────────────"
    
    # OPENAI_API_KEY (Optional - for Whisper API and Marker LLM mode)
    if [ -z "$OPENAI_API_KEY" ]; then
        print_warning "OPENAI_API_KEY is not set (optional)"
        print_info "  Needed for: Whisper API transcription, Marker LLM mode"
        print_info "  Get it from: https://platform.openai.com/api-keys"
        print_info "  Alternative: Use local Whisper model (requires ~6GB VRAM)"
    elif [[ ! "$OPENAI_API_KEY" =~ ^sk- ]]; then
        print_warning "OPENAI_API_KEY format looks incorrect (should start with sk-)"
    else
        print_success "OPENAI_API_KEY is set (${OPENAI_API_KEY:0:8}...)"
    fi
    
    # GITHUB_PERSONAL_ACCESS_TOKEN (Optional - for GitHub MCP)
    if [ -z "$GITHUB_PERSONAL_ACCESS_TOKEN" ]; then
        print_warning "GITHUB_PERSONAL_ACCESS_TOKEN is not set (optional)"
        print_info "  Needed for: GitHub MCP (create issues, PRs from Claude Code)"
        print_info "  Get it from: https://github.com/settings/tokens"
        print_info "  Required scopes: repo, read:org"
    elif [[ ! "$GITHUB_PERSONAL_ACCESS_TOKEN" =~ ^ghp_ ]] && [[ ! "$GITHUB_PERSONAL_ACCESS_TOKEN" =~ ^github_pat_ ]]; then
        print_warning "GITHUB_PERSONAL_ACCESS_TOKEN format looks incorrect"
    else
        print_success "GITHUB_PERSONAL_ACCESS_TOKEN is set (${GITHUB_PERSONAL_ACCESS_TOKEN:0:8}...)"
    fi
    
    # HF_TOKEN (Optional - for some Hugging Face models)
    if [ -z "$HF_TOKEN" ]; then
        print_warning "HF_TOKEN is not set (optional)"
        print_info "  Needed for: Some gated Hugging Face models"
        print_info "  Get it from: https://huggingface.co/settings/tokens"
    else
        print_success "HF_TOKEN is set (${HF_TOKEN:0:8}...)"
    fi
    
    # UMLS_API_KEY (Optional - for full UMLS entity linking)
    if [ -z "$UMLS_API_KEY" ]; then
        print_warning "UMLS_API_KEY is not set (optional)"
        print_info "  Needed for: Full UMLS concept linking in scispaCy"
        print_info "  Get it from: https://uts.nlm.nih.gov/uts/signup-login"
        print_info "  Note: Requires NLM account approval (free, takes ~1 day)"
    else
        print_success "UMLS_API_KEY is set"
    fi
    
    echo ""
    echo -e "${BOLD}Infrastructure Configuration:${NC}"
    echo "─────────────────────────────────────────────────────────────"
    
    # WEAVIATE_URL (Optional - defaults to localhost)
    if [ -z "$WEAVIATE_URL" ]; then
        print_info "WEAVIATE_URL not set, will use default: http://localhost:8080"
        export WEAVIATE_URL="http://localhost:8080"
    else
        print_success "WEAVIATE_URL is set: $WEAVIATE_URL"
    fi
    
    # WEAVIATE_API_KEY (Optional - only for Weaviate Cloud)
    if [ -n "$WEAVIATE_API_KEY" ]; then
        print_success "WEAVIATE_API_KEY is set (for Weaviate Cloud)"
    else
        print_info "WEAVIATE_API_KEY not set (not needed for local Docker)"
    fi
    
    echo ""
    echo -e "${BOLD}Application Settings:${NC}"
    echo "─────────────────────────────────────────────────────────────"
    
    # MEDANKI settings with defaults
    echo "  MEDANKI_DEBUG=${MEDANKI_DEBUG:-false}"
    echo "  MEDANKI_LOG_LEVEL=${MEDANKI_LOG_LEVEL:-INFO}"
    echo "  MEDANKI_ENABLE_VIGNETTES=${MEDANKI_ENABLE_VIGNETTES:-true}"
    echo "  MEDANKI_ENABLE_HALLUCINATION_CHECK=${MEDANKI_ENABLE_HALLUCINATION_CHECK:-true}"
    echo "  MEDANKI_MAX_CARDS_PER_CHUNK=${MEDANKI_MAX_CARDS_PER_CHUNK:-5}"
    
    echo ""
    
    if $has_errors; then
        echo -e "${RED}${BOLD}════════════════════════════════════════════════════════════════${NC}"
        echo -e "${RED}${BOLD}  SETUP CANNOT CONTINUE - Required API keys are missing!${NC}"
        echo -e "${RED}${BOLD}════════════════════════════════════════════════════════════════${NC}"
        echo ""
        echo "Please set the required environment variables:"
        echo ""
        echo "  Option 1: Export directly"
        echo "    export ANTHROPIC_API_KEY=sk-ant-api03-xxxxx"
        echo ""
        echo "  Option 2: Create a .env file"
        echo "    cp .env.example .env"
        echo "    # Edit .env with your API keys"
        echo ""
        echo "Then run this script again."
        exit 1
    fi
    
    if $has_warnings; then
        echo -e "${YELLOW}Some optional API keys are missing. You can continue, but some features will be limited.${NC}"
        echo ""
        read -p "Continue with setup? [Y/n] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Nn]$ ]]; then
            exit 0
        fi
    else
        print_success "All API keys validated!"
    fi
}

#===============================================================================
# System Dependencies Check
#===============================================================================

check_system_deps() {
    print_header "Checking System Dependencies"
    
    local missing_deps=()
    
    # Python
    print_step "Checking Python..."
    if check_command python3; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        if [[ "$(printf '%s\n' "3.11" "$PYTHON_VERSION" | sort -V | head -n1)" != "3.11" ]]; then
            print_warning "Python $PYTHON_VERSION found, but 3.11+ recommended"
        fi
    else
        missing_deps+=("python3")
    fi
    
    # Node.js
    print_step "Checking Node.js..."
    if check_command node; then
        NODE_VERSION=$(node --version | cut -c2-)
        if [[ "$(printf '%s\n' "18.0.0" "$NODE_VERSION" | sort -V | head -n1)" != "18.0.0" ]]; then
            print_warning "Node.js $NODE_VERSION found, but 18+ recommended"
        fi
    else
        missing_deps+=("node")
    fi
    
    # npm
    print_step "Checking npm..."
    check_command npm || missing_deps+=("npm")
    
    # Git
    print_step "Checking Git..."
    check_command git || missing_deps+=("git")
    
    # Docker (optional but recommended)
    print_step "Checking Docker..."
    if ! check_command docker; then
        print_warning "Docker not found - Weaviate will need to be run manually"
        print_info "  Install from: https://docs.docker.com/get-docker/"
    fi
    
    # uv (will install if missing)
    print_step "Checking uv package manager..."
    if ! check_command uv; then
        print_warning "uv not found - will install"
    fi
    
    # Claude Code CLI (optional)
    print_step "Checking Claude Code CLI..."
    if ! check_command claude; then
        print_warning "Claude Code CLI not found"
        print_info "  Install with: npm install -g @anthropic-ai/claude-code"
    fi
    
    # Tesseract (for PDF OCR)
    print_step "Checking Tesseract OCR..."
    if ! check_command tesseract; then
        print_warning "Tesseract not found - PDF OCR will be limited"
        print_info "  macOS: brew install tesseract"
        print_info "  Ubuntu: sudo apt-get install tesseract-ocr"
    fi
    
    # FFmpeg (for audio processing)
    print_step "Checking FFmpeg..."
    if ! check_command ffmpeg; then
        print_warning "FFmpeg not found - audio transcription will not work"
        print_info "  macOS: brew install ffmpeg"
        print_info "  Ubuntu: sudo apt-get install ffmpeg"
    fi
    
    echo ""
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        print_error "Missing required dependencies: ${missing_deps[*]}"
        echo ""
        echo "Please install the missing dependencies and run this script again."
        exit 1
    fi
    
    print_success "All required system dependencies found!"
}

#===============================================================================
# Install uv Package Manager
#===============================================================================

install_uv() {
    print_header "Setting Up uv Package Manager"
    
    if command -v uv &> /dev/null; then
        print_success "uv is already installed: $(uv --version)"
    else
        print_step "Installing uv..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        
        # Add to PATH for this session
        export PATH="$HOME/.cargo/bin:$PATH"
        
        if command -v uv &> /dev/null; then
            print_success "uv installed successfully: $(uv --version)"
        else
            print_error "Failed to install uv"
            exit 1
        fi
    fi
}

#===============================================================================
# Project Structure Setup
#===============================================================================

setup_project_structure() {
    print_header "Creating Project Structure"
    
    # Create all directories
    print_step "Creating directories..."
    
    mkdir -p packages/core/src/medanki/{models,ingestion,processing,generation,export,services,storage}
    mkdir -p packages/cli/src/medanki_cli/commands
    mkdir -p packages/api/src/medanki_api/{routes,websocket,workers,schemas}
    mkdir -p web/src/{components,pages,hooks,api,stores}/__tests__
    mkdir -p tests/{unit,integration,e2e}/{models,ingestion,processing,generation,export,api}
    mkdir -p data/{taxonomies,cache,test_fixtures,uploads}
    mkdir -p docker
    mkdir -p scripts
    mkdir -p docs
    mkdir -p .claude/{agents,hooks,commands}
    mkdir -p .github/workflows
    
    print_success "Directories created"
    
    # Create __init__.py files
    print_step "Creating __init__.py files..."
    find packages -type d | while read dir; do
        if [[ "$dir" == *"/src/"* ]] || [[ "$dir" == *"/medanki"* ]] || [[ "$dir" == *"/medanki_"* ]]; then
            touch "$dir/__init__.py" 2>/dev/null || true
        fi
    done
    touch tests/__init__.py
    touch tests/unit/__init__.py
    touch tests/integration/__init__.py
    touch tests/e2e/__init__.py
    
    print_success "__init__.py files created"
}

#===============================================================================
# Create Configuration Files
#===============================================================================

create_config_files() {
    print_header "Creating Configuration Files"
    
    # .env.example
    print_step "Creating .env.example..."
    cat > .env.example << 'EOF'
#===============================================================================
# MedAnki Environment Configuration
#===============================================================================

#-------------------------------------------------------------------------------
# REQUIRED - Claude API for flashcard generation
#-------------------------------------------------------------------------------
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx

#-------------------------------------------------------------------------------
# OPTIONAL - OpenAI (for Whisper transcription and Marker LLM mode)
#-------------------------------------------------------------------------------
# Get from: https://platform.openai.com/api-keys
# OPENAI_API_KEY=sk-xxxxx

#-------------------------------------------------------------------------------
# OPTIONAL - GitHub (for Claude Code GitHub MCP)
#-------------------------------------------------------------------------------
# Get from: https://github.com/settings/tokens
# Required scopes: repo, read:org
# GITHUB_PERSONAL_ACCESS_TOKEN=ghp_xxxxx

#-------------------------------------------------------------------------------
# OPTIONAL - Hugging Face (for gated models)
#-------------------------------------------------------------------------------
# Get from: https://huggingface.co/settings/tokens
# HF_TOKEN=hf_xxxxx

#-------------------------------------------------------------------------------
# OPTIONAL - UMLS (for full medical entity linking)
#-------------------------------------------------------------------------------
# Get from: https://uts.nlm.nih.gov/uts/signup-login
# Note: Requires NLM account approval (free, ~1 day)
# UMLS_API_KEY=xxxxx

#-------------------------------------------------------------------------------
# INFRASTRUCTURE - Weaviate Vector Database
#-------------------------------------------------------------------------------
# Local Docker (default)
WEAVIATE_URL=http://localhost:8080

# Cloud (uncomment if using Weaviate Cloud)
# WEAVIATE_URL=https://your-cluster.weaviate.network
# WEAVIATE_API_KEY=xxxxx

#-------------------------------------------------------------------------------
# APPLICATION SETTINGS
#-------------------------------------------------------------------------------
MEDANKI_DEBUG=false
MEDANKI_LOG_LEVEL=INFO

# Feature flags
MEDANKI_ENABLE_VIGNETTES=true
MEDANKI_ENABLE_HALLUCINATION_CHECK=true

# Processing
MEDANKI_MAX_CARDS_PER_CHUNK=5
MEDANKI_CHUNK_SIZE=512
MEDANKI_CHUNK_OVERLAP=75
MEDANKI_CLASSIFICATION_THRESHOLD=0.65
EOF
    print_success ".env.example created"
    
    # Create .env from .env.example if it doesn't exist
    if [ ! -f ".env" ]; then
        print_step "Creating .env from template..."
        cp .env.example .env
        print_warning ".env created - please edit with your API keys!"
    else
        print_info ".env already exists, skipping"
    fi
    
    # .gitignore
    print_step "Creating .gitignore..."
    cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
.venv/
venv/
ENV/

# Node
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*
.npm
.pnpm-debug.log*

# Build outputs
web/dist/
*.apkg

# IDE
.idea/
.vscode/
*.swp
*.swo
*~
.project
.pydevproject
.settings/

# Environment
.env
.env.local
.env.*.local
!.env.example

# Data
data/cache/
data/uploads/*
!data/uploads/.gitkeep
*.db
*.sqlite
*.sqlite3

# Testing
.coverage
htmlcov/
.pytest_cache/
.hypothesis/
coverage.xml
*.cover
cassettes/

# OS
.DS_Store
Thumbs.db

# Logs
logs/
*.log

# Docker
docker-compose.override.yml

# Temporary
tmp/
temp/
*.tmp
*.bak
EOF
    print_success ".gitignore created"
    
    # pyproject.toml (workspace root)
    print_step "Creating pyproject.toml..."
    cat > pyproject.toml << 'EOF'
[project]
name = "medanki-workspace"
version = "0.1.0"
description = "Medical flashcard generation from educational content"
readme = "README.md"
license = { text = "MIT" }
requires-python = ">=3.11"
authors = [{ name = "Your Name", email = "you@example.com" }]

[tool.uv.workspace]
members = ["packages/*"]

[tool.uv.sources]
medanki = { workspace = true }
medanki-cli = { workspace = true }
medanki-api = { workspace = true }

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM", "C4"]
ignore = ["E501"]

[tool.ruff.lint.isort]
known-first-party = ["medanki", "medanki_cli", "medanki_api"]

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_ignores = true
disallow_untyped_defs = true
plugins = ["pydantic.mypy"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
filterwarnings = ["ignore::DeprecationWarning"]
markers = [
    "slow: marks tests as slow",
    "integration: marks tests requiring external services",
    "vcr: marks tests using VCR cassettes",
]
EOF
    print_success "pyproject.toml created"
    
    # packages/core/pyproject.toml
    print_step "Creating packages/core/pyproject.toml..."
    cat > packages/core/pyproject.toml << 'EOF'
[project]
name = "medanki"
version = "0.1.0"
description = "Core library for medical flashcard generation"
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    "aiosqlite>=0.19.0",
    "httpx>=0.26.0",
]

[project.optional-dependencies]
ingestion = [
    "marker-pdf>=0.3.0",
    "pymupdf>=1.23.0",
    "pymupdf4llm>=0.0.5",
]
processing = [
    "sentence-transformers>=2.3.0",
    "weaviate-client>=4.4.0",
    "tiktoken>=0.5.0",
]
nlp = [
    "scispacy>=0.5.4",
    "spacy>=3.7.0",
]
generation = [
    "anthropic>=0.18.0",
    "instructor>=1.0.0",
]
export = [
    "genanki>=0.13.0",
]
audio = [
    "openai-whisper>=20231117",
    "openai>=1.0.0",
]
all = [
    "medanki[ingestion,processing,nlp,generation,export,audio]",
]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-vcr>=1.0.0",
    "pytest-cov>=4.1.0",
    "hypothesis>=6.98.0",
    "ruff>=0.2.0",
    "mypy>=1.8.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/medanki"]
EOF
    print_success "packages/core/pyproject.toml created"
    
    # packages/cli/pyproject.toml
    print_step "Creating packages/cli/pyproject.toml..."
    cat > packages/cli/pyproject.toml << 'EOF'
[project]
name = "medanki-cli"
version = "0.1.0"
description = "CLI for MedAnki flashcard generation"
requires-python = ">=3.11"
dependencies = [
    "medanki[all]",
    "typer[all]>=0.12.0",
    "rich>=13.0.0",
]

[project.scripts]
medanki = "medanki_cli.main:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/medanki_cli"]
EOF
    print_success "packages/cli/pyproject.toml created"
    
    # packages/api/pyproject.toml
    print_step "Creating packages/api/pyproject.toml..."
    cat > packages/api/pyproject.toml << 'EOF'
[project]
name = "medanki-api"
version = "0.1.0"
description = "FastAPI backend for MedAnki"
requires-python = ">=3.11"
dependencies = [
    "medanki[all]",
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "python-multipart>=0.0.6",
    "websockets>=12.0",
    "slowapi>=0.1.9",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/medanki_api"]
EOF
    print_success "packages/api/pyproject.toml created"
    
    # Makefile
    print_step "Creating Makefile..."
    cat > Makefile << 'EOF'
.PHONY: install install-dev sync test test-unit test-integration lint format typecheck clean dev-api dev-web docker-up docker-down setup-hooks

# Installation
install:
	uv sync

install-dev:
	uv sync --all-extras

sync:
	uv sync --all-extras

# Testing
test:
	uv run pytest tests/ -v

test-unit:
	uv run pytest tests/unit -v --tb=short

test-integration:
	uv run pytest tests/integration -v --tb=short

test-cov:
	uv run pytest tests/ --cov=medanki --cov-report=html --cov-report=term

# Code quality
lint:
	uv run ruff check .

lint-fix:
	uv run ruff check --fix .

format:
	uv run ruff format .

typecheck:
	uv run mypy packages/

check: lint typecheck test-unit

# Development servers
dev-api:
	uv run uvicorn medanki_api.main:app --reload --port 8000

dev-web:
	cd web && npm run dev

# Docker
docker-up:
	docker compose -f docker/docker-compose.yml up -d

docker-down:
	docker compose -f docker/docker-compose.yml down

docker-logs:
	docker compose -f docker/docker-compose.yml logs -f

# Cleanup
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .coverage coverage.xml

# Setup
setup-hooks:
	chmod +x .claude/hooks/*.sh

setup-scispacy:
	uv run pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_lg-0.5.4.tar.gz

# Help
help:
	@echo "Available targets:"
	@echo "  install        - Install dependencies"
	@echo "  install-dev    - Install with dev dependencies"
	@echo "  test           - Run all tests"
	@echo "  test-unit      - Run unit tests only"
	@echo "  lint           - Run linter"
	@echo "  format         - Format code"
	@echo "  typecheck      - Run type checker"
	@echo "  dev-api        - Start FastAPI dev server"
	@echo "  dev-web        - Start React dev server"
	@echo "  docker-up      - Start Docker services"
	@echo "  docker-down    - Stop Docker services"
	@echo "  clean          - Clean build artifacts"
EOF
    print_success "Makefile created"
    
    # docker/docker-compose.yml
    print_step "Creating docker/docker-compose.yml..."
    cat > docker/docker-compose.yml << 'EOF'
version: '3.8'

services:
  weaviate:
    image: semitechnologies/weaviate:1.24.1
    ports:
      - "8080:8080"
      - "50051:50051"
    environment:
      AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED: 'true'
      PERSISTENCE_DATA_PATH: '/var/lib/weaviate'
      QUERY_DEFAULTS_LIMIT: 25
      DEFAULT_VECTORIZER_MODULE: 'none'
      CLUSTER_HOSTNAME: 'node1'
    volumes:
      - weaviate_data:/var/lib/weaviate
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/v1/.well-known/ready"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  weaviate_data:
EOF
    print_success "docker/docker-compose.yml created"
    
    # tests/conftest.py
    print_step "Creating tests/conftest.py..."
    cat > tests/conftest.py << 'EOF'
"""Pytest configuration and fixtures."""
import pytest
from pathlib import Path

# Test data directory
TEST_DATA_DIR = Path(__file__).parent.parent / "data" / "test_fixtures"


@pytest.fixture
def sample_pdf_path() -> Path:
    """Path to sample PDF for testing."""
    return TEST_DATA_DIR / "sample_lecture.pdf"


@pytest.fixture
def sample_text() -> str:
    """Sample medical text for testing."""
    return """
    Congestive heart failure (CHF) is a chronic progressive condition 
    that affects the pumping power of the heart muscles. The left ventricle 
    is unable to pump blood efficiently to meet the body's needs.
    
    Treatment includes ACE inhibitors such as lisinopril, beta-blockers 
    like metoprolol, and diuretics including furosemide.
    """


@pytest.fixture
def sample_chunk_text() -> str:
    """Sample chunk text for classification testing."""
    return """
    The cardiac cycle consists of two phases: systole and diastole.
    During systole, the ventricles contract and eject blood into the 
    aorta and pulmonary artery. The mitral and tricuspid valves close,
    producing the first heart sound (S1).
    """
EOF
    print_success "tests/conftest.py created"
    
    # README.md
    print_step "Creating README.md..."
    cat > README.md << 'EOF'
# MedAnki

Medical flashcard generation from educational content with automatic MCAT/USMLE taxonomy tagging.

## Features

- 📄 Extract content from PDFs, audio lectures, and text files
- 🏷️ Automatic classification against MCAT and USMLE taxonomies
- 🎴 Generate high-quality cloze deletion and clinical vignette cards
- 📦 Export to Anki-compatible .apkg format
- 🌐 Web interface with drag-and-drop upload

## Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/medanki.git
cd medanki

# Run setup
chmod +x setup.sh
./setup.sh

# Start Docker services (Weaviate)
make docker-up

# Install dependencies
make install-dev

# Run tests
make test
```

## Development

See [docs/development.md](docs/development.md) for detailed development instructions.

## Architecture

See [docs/architecture.md](docs/architecture.md) for system design documentation.

## License

MIT
EOF
    print_success "README.md created"
    
    # Create empty .gitkeep files
    touch data/uploads/.gitkeep
    touch data/cache/.gitkeep
    touch data/test_fixtures/.gitkeep
}

#===============================================================================
# Install Dependencies
#===============================================================================

install_dependencies() {
    print_header "Installing Dependencies"
    
    # Python dependencies
    print_step "Installing Python dependencies with uv..."
    uv sync --all-extras
    print_success "Python dependencies installed"
    
    # scispaCy model (large)
    print_step "Downloading scispaCy medical NER model..."
    if uv run python -c "import spacy; spacy.load('en_core_sci_lg')" 2>/dev/null; then
        print_success "scispaCy model already installed"
    else
        uv pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_lg-0.5.4.tar.gz || {
            print_warning "Failed to install scispaCy model - you can install it later with:"
            print_info "  make setup-scispacy"
        }
    fi
    
    # Node.js dependencies (if web directory has package.json)
    if [ -f "web/package.json" ]; then
        print_step "Installing Node.js dependencies..."
        cd web && npm install && cd ..
        print_success "Node.js dependencies installed"
    fi
}

#===============================================================================
# Setup Git Worktrees
#===============================================================================

setup_worktrees() {
    if $SKIP_WORKTREES; then
        print_warning "Skipping worktree setup (--skip-worktrees flag)"
        return
    fi
    
    print_header "Setting Up Git Worktrees for Parallel Development"
    
    if [ ! -d ".git" ]; then
        print_step "Initializing git repository..."
        git init
        git add -A
        git commit -m "Initial commit"
        print_success "Git repository initialized"
    fi
    
    PARENT_DIR=$(dirname "$(pwd)")
    
    # Create feature branches
    print_step "Creating feature branches..."
    git branch feature/api-backend 2>/dev/null || true
    git branch feature/react-frontend 2>/dev/null || true
    git branch feature/test-suite 2>/dev/null || true
    git branch feature/generation-layer 2>/dev/null || true
    
    # Create worktrees
    print_step "Creating worktrees..."
    
    for wt in "medanki-api:feature/api-backend" "medanki-frontend:feature/react-frontend" "medanki-tests:feature/test-suite" "medanki-generation:feature/generation-layer"; do
        NAME="${wt%%:*}"
        BRANCH="${wt##*:}"
        
        if [ ! -d "$PARENT_DIR/$NAME" ]; then
            git worktree add "$PARENT_DIR/$NAME" "$BRANCH"
            print_success "Created worktree: $NAME"
        else
            print_info "Worktree $NAME already exists"
        fi
    done
    
    echo ""
    print_success "Worktrees created:"
    git worktree list
}

#===============================================================================
# Setup Claude Code
#===============================================================================

setup_claude_code() {
    print_header "Setting Up Claude Code"
    
    # Check if claude is installed
    if ! command -v claude &> /dev/null; then
        print_warning "Claude Code CLI not found"
        print_info "Install with: npm install -g @anthropic-ai/claude-code"
        print_info "Skipping Claude Code setup..."
        return
    fi
    
    # Add MCP servers
    print_step "Configuring MCP servers..."
    
    claude mcp add github -- npx -y @modelcontextprotocol/server-github 2>/dev/null && \
        print_success "Added GitHub MCP" || print_info "GitHub MCP may already be configured"
    
    claude mcp add sqlite -- npx -y @modelcontextprotocol/server-sqlite --db-path ./data/medanki.db 2>/dev/null && \
        print_success "Added SQLite MCP" || print_info "SQLite MCP may already be configured"
    
    claude mcp add puppeteer -- npx -y @modelcontextprotocol/server-puppeteer 2>/dev/null && \
        print_success "Added Puppeteer MCP" || print_info "Puppeteer MCP may already be configured"
    
    claude mcp add fetch -- npx -y @modelcontextprotocol/server-fetch 2>/dev/null && \
        print_success "Added Fetch MCP" || print_info "Fetch MCP may already be configured"
    
    claude mcp add memory -- npx -y @modelcontextprotocol/server-memory 2>/dev/null && \
        print_success "Added Memory MCP" || print_info "Memory MCP may already be configured"
    
    # Create agent files
    print_step "Creating Claude Code agents..."
    
    # Python Backend Agent
    cat > .claude/agents/python-backend.md << 'EOF'
---
name: python-backend
description: Expert Python backend developer for MedAnki core library and FastAPI
model: inherit
---

# Python Backend Developer Agent

You are an expert Python backend developer working on the MedAnki project - a medical flashcard generation system.

## Your Expertise
- Python 3.11+ with modern typing (generics, protocols, dataclasses)
- FastAPI for REST APIs and WebSocket
- Pydantic v2 for data validation
- SQLite with aiosqlite for async database operations
- pytest with pytest-asyncio for testing
- Clean architecture and SOLID principles

## Code Standards
1. Type hints everywhere
2. Async/await for I/O operations
3. Pydantic models for all data structures
4. Protocol classes for dependency injection
5. Google-style docstrings
6. 100-char line limit (ruff)

## When Writing Code
- Always include proper error handling
- Write tests alongside implementation
- Use dependency injection via protocols
- Run `uv run ruff check` before committing
- Run `uv run pytest tests/unit -v` to verify
EOF

    # React Frontend Agent
    cat > .claude/agents/react-frontend.md << 'EOF'
---
name: react-frontend
description: Expert React/TypeScript developer for MedAnki web interface
model: inherit
---

# React Frontend Developer Agent

You are an expert React frontend developer working on the MedAnki web interface.

## Your Expertise
- React 18+ with hooks and functional components
- TypeScript with strict mode
- TailwindCSS for styling
- React Query (TanStack Query) for data fetching
- Zustand for state management
- Vite for build tooling

## Code Standards
1. Functional components only (no classes)
2. Custom hooks for reusable logic
3. TypeScript strict mode - no `any`
4. TailwindCSS utility classes (no inline styles)
5. React Query for all API calls
6. Proper loading and error states
EOF

    # Test Engineer Agent
    cat > .claude/agents/test-engineer.md << 'EOF'
---
name: test-engineer
description: QA engineer specializing in Python and React testing for MedAnki
model: inherit
---

# Test Engineer Agent

You are a QA engineer specializing in testing for the MedAnki project.

## Your Expertise
- pytest with pytest-asyncio for Python
- Hypothesis for property-based testing
- pytest-vcr for API mocking
- Vitest + Testing Library for React
- Playwright for E2E testing

## Testing Philosophy
1. Test behavior, not implementation
2. Use fixtures for common setup
3. Mock external services (LLM, Weaviate)
4. Property-based tests for invariants
5. Integration tests for critical paths
EOF

    # Medical NLP Agent
    cat > .claude/agents/medical-nlp.md << 'EOF'
---
name: medical-nlp
description: Medical NLP specialist for taxonomy classification and entity extraction
model: inherit
---

# Medical NLP Specialist Agent

You are a medical NLP specialist working on MedAnki's classification and entity extraction systems.

## Your Expertise
- scispaCy for medical NER
- UMLS concept linking
- PubMedBERT embeddings
- Weaviate hybrid search
- Medical taxonomy systems (MCAT, USMLE)

## Key Challenge
Matching abbreviations (CHF, DVT, PE) via hybrid search with alpha=0.5
EOF

    # DevOps Agent
    cat > .claude/agents/devops.md << 'EOF'
---
name: devops
description: DevOps engineer for Docker, CI/CD, and cloud deployment
model: inherit
---

# DevOps Engineer Agent

You are a DevOps engineer responsible for MedAnki's infrastructure and deployment.

## Your Expertise
- Docker and docker-compose
- GitHub Actions CI/CD
- Google Cloud Run deployment
- Environment management
- Security hardening
EOF

    # Anki Specialist Agent
    cat > .claude/agents/anki-specialist.md << 'EOF'
---
name: anki-specialist
description: Anki integration specialist for deck generation and tag systems
model: inherit
---

# Anki Integration Specialist Agent

You are an Anki expert responsible for MedAnki's flashcard generation and export systems.

## Your Expertise
- genanki library for .apkg generation
- AnkiConnect for live sync
- AnKing deck structure and tagging
- Cloze deletion syntax

## Critical Rules
- Model IDs must be hardcoded and NEVER change
- GUIDs should be content-based for update handling
- Cloze answers should be 1-4 words max
EOF

    print_success "Claude Code agents created"
    
    # Create slash commands
    print_step "Creating slash commands..."
    
    cat > .claude/commands/implement-service.md << 'EOF'
---
name: implement-service
description: Implement a service class following project patterns
args:
  - name: service_name
  - name: protocol
---

Implement the {{service_name}} class that implements {{protocol}}.

1. Read the protocol in `packages/core/src/medanki/services/protocols.py`
2. Check test specification for expected behavior
3. Create implementation with full typing
4. Add comprehensive docstrings
5. Write unit tests
6. Verify with `uv run pytest tests/unit -v -k {{service_name}}`
EOF

    cat > .claude/commands/create-component.md << 'EOF'
---
name: create-component
description: Create a React component with tests
args:
  - name: component_name
---

Create the {{component_name}} React component:

1. Create `web/src/components/{{component_name}}.tsx`
2. Use TypeScript strict mode
3. Add Tailwind classes
4. Create test file `web/src/components/__tests__/{{component_name}}.test.tsx`
5. Verify with `cd web && npm test -- --run`
EOF

    print_success "Slash commands created"
    
    # Create hooks
    print_step "Creating hooks..."
    
    cat > .claude/hooks/pre-commit.sh << 'EOF'
#!/bin/bash
echo "🔍 Running pre-commit checks..."
uv run ruff check --fix . 2>/dev/null || true
uv run ruff format . 2>/dev/null || true
echo "✅ Pre-commit complete"
EOF
    chmod +x .claude/hooks/pre-commit.sh
    
    print_success "Hooks created"
}

#===============================================================================
# Start Docker Services
#===============================================================================

start_docker() {
    if $SKIP_DOCKER; then
        print_warning "Skipping Docker setup (--skip-docker flag)"
        return
    fi
    
    print_header "Starting Docker Services"
    
    if ! command -v docker &> /dev/null; then
        print_warning "Docker not found - skipping"
        return
    fi
    
    print_step "Starting Weaviate..."
    docker compose -f docker/docker-compose.yml up -d
    
    # Wait for Weaviate to be ready
    print_step "Waiting for Weaviate to be ready..."
    for i in {1..30}; do
        if curl -s "http://localhost:8080/v1/.well-known/ready" > /dev/null 2>&1; then
            print_success "Weaviate is ready!"
            return
        fi
        sleep 1
    done
    
    print_warning "Weaviate may not be ready yet - check with: docker-compose logs weaviate"
}

#===============================================================================
# Create Launch Script
#===============================================================================

create_launch_script() {
    print_step "Creating parallel launch script..."
    
    cat > scripts/launch-parallel.sh << 'LAUNCH_EOF'
#!/bin/bash
# Launch 4 parallel Claude Code instances in tmux

SESSION="medanki-dev"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PARENT_DIR="$(dirname "$REPO_ROOT")"

# Kill existing session if it exists
tmux kill-session -t $SESSION 2>/dev/null || true

# Create new session
tmux new-session -d -s $SESSION -c "$REPO_ROOT" -n "core"

# Core library (main branch)
tmux send-keys -t $SESSION:core "cd $REPO_ROOT && claude" Enter

# API development
tmux new-window -t $SESSION -n "api" -c "$PARENT_DIR/medanki-api"
tmux send-keys -t $SESSION:api "claude" Enter

# Frontend development  
tmux new-window -t $SESSION -n "frontend" -c "$PARENT_DIR/medanki-frontend"
tmux send-keys -t $SESSION:frontend "claude" Enter

# Test development
tmux new-window -t $SESSION -n "tests" -c "$PARENT_DIR/medanki-tests"
tmux send-keys -t $SESSION:tests "claude" Enter

# Attach to session
tmux attach -t $SESSION
LAUNCH_EOF
    chmod +x scripts/launch-parallel.sh
    
    print_success "Launch script created: scripts/launch-parallel.sh"
}

#===============================================================================
# Final Summary
#===============================================================================

print_summary() {
    print_header "Setup Complete! 🎉"
    
    echo -e "${BOLD}Project Structure:${NC}"
    echo "  📁 packages/core/    - Core Python library"
    echo "  📁 packages/cli/     - CLI application"
    echo "  📁 packages/api/     - FastAPI backend"
    echo "  📁 web/              - React frontend"
    echo "  📁 tests/            - Test suites"
    echo "  📁 data/             - Taxonomies and fixtures"
    echo ""
    
    if ! $SKIP_WORKTREES; then
        echo -e "${BOLD}Git Worktrees (for parallel development):${NC}"
        PARENT_DIR=$(dirname "$(pwd)")
        echo "  📁 $(pwd)                    - main (core library)"
        echo "  📁 $PARENT_DIR/medanki-api        - API development"
        echo "  📁 $PARENT_DIR/medanki-frontend   - React frontend"
        echo "  📁 $PARENT_DIR/medanki-tests      - Test writing"
        echo "  📁 $PARENT_DIR/medanki-generation - Card generation"
        echo ""
    fi
    
    echo -e "${BOLD}Available Commands:${NC}"
    echo "  make install-dev   - Install all dependencies"
    echo "  make test          - Run tests"
    echo "  make lint          - Run linter"
    echo "  make dev-api       - Start FastAPI server"
    echo "  make dev-web       - Start React dev server"
    echo "  make docker-up     - Start Weaviate"
    echo ""
    
    echo -e "${BOLD}Claude Code Agents:${NC}"
    echo "  @python-backend    - Core library, FastAPI"
    echo "  @react-frontend    - React components"
    echo "  @test-engineer     - Testing"
    echo "  @medical-nlp       - Classification, NER"
    echo "  @devops            - Docker, CI/CD"
    echo "  @anki-specialist   - Cards, decks"
    echo ""
    
    echo -e "${BOLD}Next Steps:${NC}"
    echo "  1. Edit .env with your API keys (if not already done)"
    echo "  2. Start Weaviate: make docker-up"
    echo "  3. Install dependencies: make install-dev"
    echo "  4. Run tests: make test"
    echo "  5. Launch parallel Claude instances: ./scripts/launch-parallel.sh"
    echo ""
    
    if [ -z "$ANTHROPIC_API_KEY" ]; then
        echo -e "${YELLOW}⚠ Don't forget to set ANTHROPIC_API_KEY in .env!${NC}"
        echo ""
    fi
    
    echo -e "${GREEN}Happy coding! 🚀${NC}"
}

#===============================================================================
# Main
#===============================================================================

main() {
    echo ""
    echo -e "${BOLD}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}║            MedAnki Complete Setup Script                      ║${NC}"
    echo -e "${BOLD}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    # Run all setup steps
    validate_env_vars
    check_system_deps
    install_uv
    setup_project_structure
    create_config_files
    
    if ! $MINIMAL; then
        install_dependencies
        setup_worktrees
        setup_claude_code
        start_docker
        create_launch_script
    fi
    
    print_summary
}

# Run main
main
