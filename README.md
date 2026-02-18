# Knowledge Base Overnight Enrichment Demo

**Demo: Azure AI Content Understanding for knowledge base enrichment**

Enterprises with reserved PTU capacity often have idle compute during off-hours. This demo shows how Azure AI Content Understanding can enrich document knowledge bases overnight — extracting metadata, structure, and semantic fields — resulting in dramatically better RAG answers.

## The Demo Story

1. **Upload** a corpus of GAO cybersecurity reports (20 PDFs)
2. **Baseline pipeline** — extract text, chunk, embed, index (standard RAG)
3. **Enhanced pipeline** — use CU custom analyzers to extract report metadata (titles, agencies, categories, findings), then chunk, embed, and index with that metadata
4. **Compare** — ask the same questions to both indexes side-by-side and see the quality difference

## Quick Start

### Prerequisites

- Python 3.12 (pinned in `.python-version`)
- [uv](https://docs.astral.sh/uv/) package manager
- Azure subscription with: AI Content Understanding, AI Search, Azure OpenAI, Blob Storage

### Setup

```bash
# Install dependencies
uv sync

# Configure environment
cp .env.template .env
# Edit .env with your Azure resource endpoints and keys

# Run tests
uv run pytest -v

# Start the server
uv run uvicorn enrichment.server:app --reload
```

Open http://localhost:8080 for the side-by-side comparison UI.

### Run the Enrichment Pipelines

```bash
# Download the GAO corpus (requires browser — see scripts/download_corpus.py)
# Then run both pipelines:
uv run python scripts/run_pipelines.py --corpus-dir data/corpus

# Or run one at a time:
uv run python scripts/run_pipelines.py --pipeline baseline
uv run python scripts/run_pipelines.py --pipeline enhanced
```

### Docker

```bash
docker build -t enrichment .
docker run -p 8080:8080 --env-file .env enrichment
```

## Architecture

```
┌──────────────┐     ┌───────────────────┐     ┌──────────────────┐
│   PDF Corpus │────▶│  Content          │────▶│  Azure AI Search │
│  (Blob Store)│     │  Understanding    │     │  (2 indexes)     │
└──────────────┘     └───────────────────┘     └──────────────────┘
                           │                          │
                     ┌─────┴─────┐              ┌─────┴─────┐
                     │ Baseline  │              │ Enhanced  │
                     │ (text     │              │ (metadata │
                     │  only)    │              │  + text)  │
                     └───────────┘              └───────────┘
                           │                          │
                     ┌─────┴──────────────────────────┴─────┐
                     │      Side-by-Side Comparison UI       │
                     │  ┌─────────────┐  ┌────────────────┐  │
                     │  │  Baseline   │  │  CU-Enhanced   │  │
                     │  │    RAG      │  │     RAG        │  │
                     │  └─────────────┘  └────────────────┘  │
                     └──────────────────────────────────────┘
```

### Pipeline Details

**Baseline**: CU prebuilt-layout → paragraph chunking → text-embedding-3-small → AI Search (text + vector)

**Enhanced**: CU custom analyzer → same chunking → same embeddings → AI Search (text + vector + report_title, report_number, topic_category, executive_summary, agencies, section_title)

The enhanced index lets RAG answers cite specific reports, filter by agency or topic, and use executive summaries for better context.

## Project Structure

```text
├── src/enrichment/
│   ├── server.py                 # FastAPI app (API + static UI)
│   ├── config.py                 # Pydantic settings from .env
│   ├── models/                   # Pydantic data models
│   ├── services/
│   │   ├── content_understanding.py  # CU SDK integration
│   │   ├── search.py                 # AI Search index management
│   │   ├── embedding.py              # Azure OpenAI embeddings
│   │   ├── chunking.py               # Paragraph-aware text splitter
│   │   ├── chat.py                   # RAG chat (baseline + enhanced)
│   │   └── storage.py                # Blob storage operations
│   ├── pipeline/
│   │   ├── baseline.py               # Baseline enrichment pipeline
│   │   └── enhanced.py               # CU-enhanced pipeline
│   └── static/                       # Comparison UI (HTML/CSS/JS)
├── scripts/
│   ├── download_corpus.py            # GAO report downloader
│   └── run_pipelines.py              # Pipeline runner
├── tests/                            # 86 tests, 85% coverage
├── data/corpus/                      # Downloaded PDFs (gitignored)
├── Dockerfile
├── pyproject.toml
└── .env.template
```

## Development

```bash
uv run pytest -v              # Run tests (80% coverage minimum)
uv run ruff check .           # Lint
uv run ruff format .          # Format
uv run pyright                # Type check
uv run pre-commit run --all-files  # All checks
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| **AI Extraction** | Azure AI Content Understanding |
| **Search** | Azure AI Search (hybrid: keyword + vector) |
| **Embeddings** | Azure OpenAI text-embedding-3-small |
| **Chat** | Azure OpenAI GPT-4o |
| **Runtime** | Python 3.12, FastAPI, uvicorn |
| **Package Manager** | uv |
| **Testing** | pytest (85% coverage) |
| **Quality** | Ruff, Pyright, Snyk, detect-secrets |

## License

MIT
