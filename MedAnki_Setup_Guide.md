# MedAnki Complete Setup Guide
## From Zero to Fully Configured Development Environment

This guide walks you through setting up MedAnki with all optimizations for Claude Code parallel development.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [API Keys Reference](#api-keys-reference)
3. [Quick Start (TL;DR)](#quick-start-tldr)
4. [Detailed Setup Steps](#detailed-setup-steps)
5. [Verifying Your Setup](#verifying-your-setup)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

| Software | Minimum Version | Installation |
|----------|-----------------|--------------|
| **Python** | 3.11+ | [python.org](https://python.org) or `brew install python@3.11` |
| **Node.js** | 18+ | [nodejs.org](https://nodejs.org) or `brew install node` |
| **Git** | 2.x | [git-scm.com](https://git-scm.com) |
| **Docker** | 20+ | [docker.com](https://docs.docker.com/get-docker/) |

### Recommended Software

| Software | Purpose | Installation |
|----------|---------|--------------|
| **tmux** | Parallel terminal sessions | `brew install tmux` or `apt install tmux` |
| **Tesseract** | PDF OCR | `brew install tesseract` or `apt install tesseract-ocr` |
| **FFmpeg** | Audio processing | `brew install ffmpeg` or `apt install ffmpeg` |
| **Claude Code** | AI-assisted development | `npm install -g @anthropic-ai/claude-code` |

---

## API Keys Reference

### 🔴 Required (Setup Will Fail Without These)

#### Anthropic API Key
- **Purpose:** Powers all flashcard generation via Claude
- **Get it:** https://console.anthropic.com/settings/keys
- **Format:** `sk-ant-api03-xxxxx`
- **Cost:** ~$3-15 per million tokens (expect ~$0.03-0.05 per lecture)

```bash
export ANTHROPIC_API_KEY=sk-ant-api03-xxxxx
```

---

### 🟡 Optional (Enhanced Features)

#### OpenAI API Key
- **Purpose:** 
  - Whisper API for audio transcription (alternative to local model)
  - Marker LLM mode for better PDF table extraction
- **Get it:** https://platform.openai.com/api-keys
- **Format:** `sk-xxxxx`
- **Cost:** $0.006/minute audio, varies for GPT calls
- **Alternative:** Run Whisper locally (requires ~6GB VRAM)

```bash
export OPENAI_API_KEY=sk-xxxxx
```

#### GitHub Personal Access Token
- **Purpose:** GitHub MCP for Claude Code (create issues, PRs directly)
- **Get it:** https://github.com/settings/tokens
- **Required scopes:** `repo`, `read:org`
- **Format:** `ghp_xxxxx` or `github_pat_xxxxx`

```bash
export GITHUB_PERSONAL_ACCESS_TOKEN=ghp_xxxxx
```

#### Hugging Face Token
- **Purpose:** Access gated models (some specialized medical models)
- **Get it:** https://huggingface.co/settings/tokens
- **Format:** `hf_xxxxx`
- **Cost:** Free

```bash
export HF_TOKEN=hf_xxxxx
```

#### UMLS API Key
- **Purpose:** Full UMLS concept linking in scispaCy for richer entity extraction
- **Get it:** https://uts.nlm.nih.gov/uts/signup-login
- **Note:** Requires NLM account approval (~1 day, free)
- **Without it:** Basic medical NER still works, just no UMLS linking

```bash
export UMLS_API_KEY=xxxxx
```

---

### 🟢 Infrastructure (Has Defaults)

#### Weaviate
- **Purpose:** Vector database for hybrid search
- **Default:** `http://localhost:8080` (local Docker)
- **Cloud option:** https://console.weaviate.cloud (free tier available)

```bash
# Local Docker (default - no key needed)
export WEAVIATE_URL=http://localhost:8080

# Cloud (if using Weaviate Cloud)
export WEAVIATE_URL=https://your-cluster.weaviate.network
export WEAVIATE_API_KEY=xxxxx
```

---

## Quick Start (TL;DR)

```bash
# 1. Clone repository
git clone https://github.com/yourusername/medanki.git
cd medanki

# 2. Set required API key
export ANTHROPIC_API_KEY=sk-ant-api03-xxxxx

# 3. Run setup script
chmod +x setup.sh
./setup.sh

# 4. Launch parallel Claude Code instances
./scripts/launch-parallel.sh
```

That's it! The setup script handles everything else.

---

## Detailed Setup Steps

### Step 1: Clone or Create Repository

```bash
# Option A: Clone existing repo
git clone https://github.com/yourusername/medanki.git
cd medanki

# Option B: Create new repo
mkdir medanki && cd medanki
git init
```

### Step 2: Create Environment File

Create `.env` in the project root:

```bash
# Create from example (setup script does this too)
cat > .env << 'EOF'
#===============================================================================
# MedAnki Environment Configuration
#===============================================================================

#-------------------------------------------------------------------------------
# REQUIRED - Claude API for flashcard generation
#-------------------------------------------------------------------------------
ANTHROPIC_API_KEY=sk-ant-api03-YOUR_KEY_HERE

#-------------------------------------------------------------------------------
# OPTIONAL - OpenAI (for Whisper transcription and Marker LLM mode)
#-------------------------------------------------------------------------------
# OPENAI_API_KEY=sk-YOUR_KEY_HERE

#-------------------------------------------------------------------------------
# OPTIONAL - GitHub (for Claude Code GitHub MCP)
#-------------------------------------------------------------------------------
# GITHUB_PERSONAL_ACCESS_TOKEN=ghp_YOUR_TOKEN_HERE

#-------------------------------------------------------------------------------
# OPTIONAL - Hugging Face (for gated models)
#-------------------------------------------------------------------------------
# HF_TOKEN=hf_YOUR_TOKEN_HERE

#-------------------------------------------------------------------------------
# OPTIONAL - UMLS (for full medical entity linking)
#-------------------------------------------------------------------------------
# UMLS_API_KEY=YOUR_KEY_HERE

#-------------------------------------------------------------------------------
# INFRASTRUCTURE - Weaviate Vector Database
#-------------------------------------------------------------------------------
WEAVIATE_URL=http://localhost:8080

#-------------------------------------------------------------------------------
# APPLICATION SETTINGS
#-------------------------------------------------------------------------------
MEDANKI_DEBUG=false
MEDANKI_LOG_LEVEL=INFO
MEDANKI_ENABLE_VIGNETTES=true
MEDANKI_ENABLE_HALLUCINATION_CHECK=true
MEDANKI_MAX_CARDS_PER_CHUNK=5
EOF
```

**Edit the file** and add your API keys.

### Step 3: Download Setup Files

Download the setup script and CLAUDE.md:

```bash
# Download setup.sh (from the files I created)
# Make it executable
chmod +x setup.sh

# Download CLAUDE.md to project root
# This is automatically read by Claude Code
```

### Step 4: Run Setup Script

```bash
./setup.sh
```

The script will:
1. ✅ Validate all API keys
2. ✅ Check system dependencies
3. ✅ Install uv package manager
4. ✅ Create project structure
5. ✅ Create configuration files
6. ✅ Install Python dependencies
7. ✅ Download scispaCy medical model (~400MB)
8. ✅ Create git worktrees for parallel development
9. ✅ Configure Claude Code MCPs and agents
10. ✅ Start Weaviate Docker container

### Step 5: Verify Setup

```bash
# Check Weaviate is running
curl http://localhost:8080/v1/.well-known/ready

# Run tests
make test-unit

# Check Claude Code agents
ls .claude/agents/
```

### Step 6: Launch Parallel Development

```bash
# Option A: Use the launch script (requires tmux)
./scripts/launch-parallel.sh

# Option B: Open 4 terminals manually
# Terminal 1: cd ~/projects/medanki && claude
# Terminal 2: cd ~/projects/medanki-api && claude
# Terminal 3: cd ~/projects/medanki-frontend && claude
# Terminal 4: cd ~/projects/medanki-tests && claude
```

---

## Verifying Your Setup

### API Key Validation

The setup script validates API keys, but you can also test manually:

```bash
# Test Anthropic API
curl -X POST https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-sonnet-4-5-20250514","max_tokens":10,"messages":[{"role":"user","content":"Hi"}]}'

# Test OpenAI API (if configured)
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# Test Weaviate
curl http://localhost:8080/v1/.well-known/ready
```

### Project Structure Verification

After setup, your directory should look like:

```
medanki/
├── .claude/
│   ├── agents/
│   │   ├── python-backend.md
│   │   ├── react-frontend.md
│   │   ├── test-engineer.md
│   │   ├── medical-nlp.md
│   │   ├── devops.md
│   │   └── anki-specialist.md
│   ├── commands/
│   │   ├── implement-service.md
│   │   └── create-component.md
│   └── hooks/
│       └── pre-commit.sh
├── packages/
│   ├── core/
│   │   ├── pyproject.toml
│   │   └── src/medanki/
│   ├── cli/
│   │   ├── pyproject.toml
│   │   └── src/medanki_cli/
│   └── api/
│       ├── pyproject.toml
│       └── src/medanki_api/
├── web/
│   └── src/
├── data/
│   ├── taxonomies/
│   ├── cache/
│   └── test_fixtures/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── docker/
│   └── docker-compose.yml
├── scripts/
│   └── launch-parallel.sh
├── .env
├── .env.example
├── .gitignore
├── CLAUDE.md
├── Makefile
├── pyproject.toml
├── README.md
└── setup.sh
```

### Worktree Verification

```bash
# List all worktrees
git worktree list

# Should show:
# /path/to/medanki           [main]
# /path/to/medanki-api       [feature/api-backend]
# /path/to/medanki-frontend  [feature/react-frontend]
# /path/to/medanki-tests     [feature/test-suite]
# /path/to/medanki-generation [feature/generation-layer]
```

---

## Troubleshooting

### "ANTHROPIC_API_KEY is not set"

```bash
# Make sure .env exists and has the key
cat .env | grep ANTHROPIC

# Make sure it's exported
export ANTHROPIC_API_KEY=sk-ant-api03-xxxxx

# Or source the .env file
source .env
```

### "Weaviate connection refused"

```bash
# Check if Docker is running
docker ps

# Start Weaviate
make docker-up

# Check logs
docker-compose -f docker/docker-compose.yml logs weaviate
```

### "scispaCy model not found"

```bash
# Download the model manually
make setup-scispacy

# Or directly:
uv run pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_lg-0.5.4.tar.gz
```

### "Claude Code command not found"

```bash
# Install Claude Code CLI
npm install -g @anthropic-ai/claude-code

# Verify installation
claude --version
```

### "Worktree already exists"

```bash
# Remove existing worktree
git worktree remove ../medanki-api

# Or prune stale references
git worktree prune

# Then re-run setup
./setup.sh
```

### "Permission denied" on setup.sh

```bash
chmod +x setup.sh
./setup.sh
```

### Python dependency conflicts

```bash
# Clear and reinstall
rm -rf .venv
uv sync --all-extras
```

---

## Environment Variables Summary

### Complete .env Template

```bash
#===============================================================================
# REQUIRED
#===============================================================================
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx

#===============================================================================
# OPTIONAL - Enhanced Features
#===============================================================================
# OpenAI - for Whisper API and Marker LLM mode
# OPENAI_API_KEY=sk-xxxxx

# GitHub - for Claude Code GitHub MCP
# GITHUB_PERSONAL_ACCESS_TOKEN=ghp_xxxxx

# Hugging Face - for gated models
# HF_TOKEN=hf_xxxxx

# UMLS - for full medical entity linking
# UMLS_API_KEY=xxxxx

#===============================================================================
# INFRASTRUCTURE
#===============================================================================
WEAVIATE_URL=http://localhost:8080
# WEAVIATE_API_KEY=xxxxx  # Only for Weaviate Cloud

#===============================================================================
# APPLICATION SETTINGS
#===============================================================================
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
```

---

## What's Next?

After setup is complete:

1. **Start implementing!** Use the implementation plan to guide your work
2. **Launch parallel instances** with `./scripts/launch-parallel.sh`
3. **Use agents** like `@python-backend` for specialized help
4. **Check the CLAUDE.md** - it provides project context to Claude Code automatically

See the following documents for detailed guidance:
- `MedAnki_Implementation_Plan.md` - Chunked work breakdown
- `MedAnki_Advanced_Claude_Workflows.md` - Power-user techniques
- `MedAnki_Claude_Agents.md` - Agent definitions and usage

---

*Document version: 1.0 | Last updated: December 2025*
