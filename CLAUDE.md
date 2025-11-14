# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**igles-ia** (iglesia + IA) is an automated platform that scrapes papal documents from the Vatican website, analyzes them using AI, generates podcasts with text-to-speech, and publishes a weekly static website with RSS feeds.

The system is built around a data pipeline architecture that transforms raw Vatican content into multiple distribution formats (website, podcast feeds, email newsletters).

## Technology Stack

- **Python 3.12** (required) with UV package manager
- **Backend**: Flask, CrewAI (multi-agent AI), SQLAlchemy
- **Data Processing**: Pandas, BeautifulSoup (scraping)
- **Audio**: Amazon Polly (text-to-speech), AWS S3 (storage)
- **Database**: Supabase (PostgreSQL)
- **AI/LLM**: OpenAI GPT-4 mini via CrewAI agents
- **Email**: Brevo/Sendinblue API
- **Authentication**: AWS Cognito
- **Frontend**: Flask with Jinja2 templates, Flask-Frozen for static site generation
- **Testing**: Pytest
- **Linting**: Ruff

## Core Architecture

The system follows a **pipeline architecture** with these layers:

```
Vatican.va → Scraping (BeautifulSoup) → AI Analysis (CrewAI) →
Audio Generation (Azure TTS) → Storage (S3 + Supabase) →
Web Publishing (Flask-Frozen) → Static Site (GitHub Pages)
```

### Key Modules

| Module | Purpose |
|--------|---------|
| **iglesia/agents.py** | CrewAI multi-agent setup for document analysis (summaries, key ideas, tags) |
| **iglesia/utils.py** | Web scraping utilities (legacy: contains `obtener_todos_los_textos()`, `extraer_homilia()`) |
| **iglesia/audio_utils.py** | TTS and podcast generation with metadata handling |
| **iglesia/email_utils_3.py** | Newsletter distribution via Brevo API |
| **iglesia/cognito_utils.py** | AWS Cognito integration for subscriber management |
| **iglesia/clean_text.py** | Text preprocessing and markdown handling |
| **web/app.py** | Flask application and Flask-Frozen site generation |
| **vatican-archiver/** | Specialized scrapers for Vatican document enrichment |
| **superbase/** | Database seeding and metadata enrichment scripts |

### Data Flow

1. **Scraping**:
   - **Legacy route** (main.py): `obtener_todos_los_textos()` from iglesia/utils.py scrapes Vatican via hardcoded URLs
   - **New route** (vatican-archiver): `VaticanArchiver` class provides robust scraping with caching and retry logic
2. **Link Enrichment**: `vatican-archiver/vatican_archive_enriquecer_episodios.py` extracts document text and generates metadata with LLM
3. **AI Analysis**: CrewAI agents (agents.py) process each document to generate summaries, key ideas, and tags
4. **JSON Storage**: Results stored in `json-rss/{date}/filename.json` with frontmatter metadata
5. **Audio Generation**: `main.py generar-audios` creates TTS MP3s and uploads to S3
6. **RSS Generation**: `generar_rss.py` aggregates episode metadata into `podcast.xml`
7. **Web Generation**: `make freeze` runs Flask-Frozen to generate static HTML in `web/build/`
8. **Deployment**: Copy `web/build/` to `docs/` and push to GitHub Pages

## Common Commands

### Development

```bash
# Start Flask dev server on port 5000
make run-web

# Run linter
uv run ruff check iglesia/

# Run tests
uv run pytest iglesia/tests/

# Run single test
uv run pytest iglesia/tests/test_file.py::test_function -v
```

### Data Pipeline

```bash
# Scrape Vatican content and run AI agents for a specific date
uv run main.py pipeline-date --run-date "2025-11-10"

# Process audio generation for a specific date (with options)
uv run main.py generar-audios --run-date "2025-11-10"
uv run main.py generar-audios --run-date "2025-11-10" --only-metadata
uv run main.py generar-audios --run-date "2025-11-10" --force-create-audio

# Daily audio preparation (runs agents if needed)
uv run main.py preparar-datos-audio --run-date="2025-11-10"

# Vatican archiver (enriches existing JSON with additional metadata)
make vatican_archiver

# Sync database with latest metadata
make update_superbase
```

### Deployment

```bash
# Generate static website and deploy
make freeze

# Full audio creation pipeline (scrape + agents + audio + freeze)
make create_audio
```

## Configuration & Secrets

The project uses `.env` file for environment variables (not committed):

```
OPENAI_API_KEY              # For CrewAI/GPT-4
BREVO_TOKEN                 # Brevo email API
SUPABASE_URL               # PostgreSQL backend
SUPABASE_KEY               # DB authentication key
AWS_ACCESS_KEY_ID          # S3 bucket access
AWS_SECRET_ACCESS_KEY      # S3 bucket access
AZURE_SPEECH_KEY           # Azure TTS service
AZURE_SPEECH_REGION        # Azure region (e.g., "eastus")
COGNITO_CLIENT_ID          # AWS Cognito
COGNITO_USER_POOL_ID       # AWS Cognito pool
AWS_S3_BUCKET              # S3 bucket name ("igles-ia-spotify")
```

See `main.py:URLS_VATICANO` for the Vatican scraping URLs (hardcoded, may need updates for new years/months).

## Vatican Archiver System (Migration in Progress)

The `vatican-archiver/` folder contains a modern, production-grade scraping system that's gradually replacing the legacy `obtener_todos_los_textos()` function.

### Key Components

- **vatican_archiver.py**: Main class `VaticanArchiver` that provides:
  - Robust scraping with retry logic and rate limiting
  - Built-in caching to avoid re-downloading pages
  - URL discovery and link extraction
  - Support for multiple popes and languages
  - Three-step pipeline: find links → merge to CSV → download documents

- **vatican_archive_enriquecer_episodios.py**: Enrichment script that:
  - Takes raw documents from all_links.csv
  - Extracts clean text using `iglesia/clean_text.py`
  - Generates metadata with LLM (titles, descriptions, social media content)
  - Stores enriched episodes in `links_enriched/all_links_enriched.json`
  - Uses `extraer_homilia()` from iglesia/utils.py for text extraction

### Current Usage

- **Legacy code still uses**: `obtener_todos_los_textos()` in main.py for pipeline-date command
- **Vatican Archiver is used for**: `make vatican_archiver` which generates enriched metadata
- **Streams that depend on obtener_todos_los_textos()**: Check main.py for active usage in CLI commands

### Migration Path

When replacing `obtener_todos_los_textos()`:
1. Use `VaticanArchiver.run_full_archive()` to download links and documents
2. Run `enriquecer_episodios()` to extract text and generate metadata
3. Update main.py to read from `links_enriched/all_links_enriched.json` instead of scraping live
4. Ensure all CSV/JSON output is compatible with existing downstream processes

## Important Directories

- **json-rss/{date}/**: Output from scraping and AI analysis. Each date folder contains:
  - `episodes.json`: Metadata for podcast episodes
  - Individual `.json` files per document with structure: `fuente_documento`, `tipo_documento`, `url_original`, `resumen_general`, `ideas_clave`, `tags_sugeridos`
- **web/templates/**: Jinja2 HTML templates
- **web/static/**: CSS, JavaScript, PWA manifest, service worker
- **web/build/**: Generated Flask-Frozen output (intermediate)
- **docs/**: Final deployed static site (copy of web/build/)
- **vatican-archiver/**: Additional scraping and enrichment scripts
- **superbase/**: Database population and metadata scripts (1_seed → 5_update_audio_urls)
- **cache/**: Local Vatican content cache to avoid re-scraping

## Important Notes

### Date Handling

- The pipeline operates on **Monday-based weekly dates**
- When a date is provided that isn't Monday, the system adjusts to the next Monday
- Data is filtered to documents from the past 7 days before that Monday
- This ensures consistent weekly aggregation

### AI Analysis

- CrewAI setup in `agents.py:create_iglesia_content_crew()`
- Uses GPT-4 mini for cost-effective analysis
- Analyzes: summaries (resumen_general), key ideas (ideas_clave), suggested tags (tags_sugeridos)
- Each agent has specific prompts and focus areas

### Audio Generation

- Uses Azure Cognitive Services for text-to-speech (preferred)
- Has fallback to AWS Polly (alternative TTS)
- MP3 files uploaded directly to S3 after generation
- Episode metadata includes podcast numbering scheme: `[pontificate_week.episode_number]`

### Static Site Generation

- Uses Flask-Frozen: converts dynamic Flask routes to static HTML files
- No runtime overhead in production (served directly from GitHub Pages)
- RSS feed (`podcast.xml`) also generated statically
- CSS includes PWA styling and service worker registration

### Database

- Supabase PostgreSQL manages enriched episode metadata
- Separate scripts for different data updates (seeds, links, translations, audio URLs)
- `superbase/` folder contains ordered scripts that must run in sequence

## Development Workflow Tips

1. **Making changes to Flask templates**: Edit `web/templates/`, then `make run-web` to test, then `make freeze` to deploy
2. **Adding new scraping sources**: Update `URLS_VATICANO` in `main.py` and adjust month URLs as needed
3. **Modifying AI analysis**: Edit prompts in `agents.py` and test with `uv run main.py pipeline-date --run-date "YYYY-MM-DD"`
4. **Audio pipeline**: Audio generation can take significant time for large date ranges. Use `--only-metadata` to skip TTS for testing
5. **Testing email**: Use `iglesia/email_utils_3.py` functions directly in notebooks before integrating into CLI

## Debugging

- **Scraping issues**:
  - Legacy: Check `cache/` folder and Vatican URLs in `main.py:URLS_VATICANO`
  - Vatican Archiver: Check `cache/{pope_slug}/{language}/` for cached pages; use `force_refresh=True` to bypass cache
- **Vatican Archiver enrichment**: Check `vatican-archiver/documents/links/` for extracted links and `vatican-archiver/documents/links_enriched/` for processed metadata
- **extraer_homilia() failures**: Verify HTML structure in Vatican pages hasn't changed; check `testo` div and `text` class selectors
- **AI analysis errors**: Check CrewAI logs and OpenAI API quota
- **Audio generation**: Azure TTS character limits (~5000 chars per request), long documents may need splitting
- **Database sync**: Run superbase scripts in order (1 → 5), check Supabase console for errors
- **Static site generation**: Check `web/build/` output and Flask template errors

## Deployment Checklist

Before pushing to GitHub:

1. Ensure all `.env` variables are set and valid
2. Run `uv run ruff check iglesia/` and fix linting issues
3. Run `uv run pytest iglesia/tests/` and ensure all tests pass
4. Test locally with `make run-web` before freezing
5. Run `make freeze` to generate final static site
6. Verify `docs/` folder contains updated HTML files
7. Commit and push to main branch (GitHub Pages watches `docs/` folder)

## Learning Resources in Codebase

- **Jupyter Notebooks**: `dev_notebooks/` contains audio generation experiments
- **Makefile**: Shows command sequences and workflows
- **main.py**: Entry point with all CLI commands documented
- **Test files**: `iglesia/tests/` has examples of testing utilities

## Migration Notes: obtener_todos_los_textos()

The `obtener_todos_los_textos()` function in `iglesia/utils.py` is being gradually migrated to the Vatican Archiver system.

### What it does currently:
- Takes a dictionary of document type URLs (homilias, angelus, speeches, etc.)
- Scrapes the Vatican website using BeautifulSoup
- Extracts document titles, URLs, and text content
- Returns a Pandas DataFrame with columns: `tipo`, `fecha`, `titulo`, `url`, `texto`

### Where it's used:
- `main.py:generar_audios_diarios()`: Scrapes content for weekly audio generation
- `main.py:pipeline_date()`: Part of the main scraping pipeline
- Any CLI command that calls functions importing from `iglesia.utils`

### Streams that depend on it:
1. Check `main.py` for all `@app.command()` functions that call `obtener_todos_los_textos()`
2. Check if any other modules import this function directly

### Notes for migration:
- **Key functions in iglesia/utils.py to migrate**:
  - `obtener_homilias_vaticano(url)`: Scrapes a single index page
  - `extraer_homilia(homilia)`: Extracts text from a document (still used by vatican_archive_enriquecer_episodios.py)
  - `obtener_todos_los_textos(urls)`: Main aggregation function (main migration target)
- **Replacement strategy**: Use `VaticanArchiver` + `enriquecer_episodios()` output instead of live scraping
- **Breaking change risk**: Ensure all downstream processors can read from the enriched JSON format
