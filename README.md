# Matcha AI

Job matching assistant powered by LangGraph. Helps job seekers create profiles through conversational AI via WhatsApp or web interface.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          ENTRY POINTS                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│   │  Chainlit    │    │  FastAPI     │    │  WhatsApp    │              │
│   │  Web UI      │    │  REST API    │    │  Webhook     │              │
│   │  :8000       │    │  :8080       │    │              │              │
│   └──────┬───────┘    └──────┬───────┘    └──────┬───────┘              │
│          │                   │                   │                       │
│          └───────────────────┼───────────────────┘                       │
│                              ▼                                           │
│                         thread_id                                        │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      SUPERVISOR AGENT                                    │
│                   app/assistant/supervisor.py                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   LangGraph create_react_agent                                           │
│   ┌─────────────────────────────────────────────────────────────┐       │
│   │  MemorySaver Checkpointer (thread-based persistence)        │       │
│   │  Token-based message trimming (tiktoken, 30k tokens)        │       │
│   └─────────────────────────────────────────────────────────────┘       │
│                                                                          │
│   - Model: gpt-4o-mini                                                   │
│   - Persistence: InMemory (per session)                                  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                              │
               ┌──────────────┼──────────────┐
               ▼              ▼              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           TOOLS                                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  PROFILE TOOLS              PARSING STATUS         Q&A TOOLS             │
│  ─────────────              ──────────────         ─────────             │
│  get_profile()              check_cv_status()      get_service_info()    │
│  update_profile_field()     get_parsed_cv_data()   - About, process      │
│  get_missing_fields()       is_parsing_active()    - Privacy, help       │
│  validate_profile()                                                      │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    CV PARSING SUBGRAPH                                   │
│                app/assistant/cv_parsing_graph.py                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   LangGraph StateGraph (runs in background)                              │
│   ┌─────────┐    ┌─────────────┐    ┌─────────────┐                     │
│   │  START  │ ─► │   parse     │ ─► │  should_    │                     │
│   │         │    │  document   │    │  retry?     │                     │
│   └─────────┘    └─────────────┘    └──────┬──────┘                     │
│                        ▲                   │                             │
│                        └───── wait_retry ──┘                             │
│                                                                          │
│   Supported: PDF, DOCX, DOC                                              │
│   Output: name, email, work_experience, education, skills, etc.          │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Components

| Component | Type | Purpose |
|-----------|------|---------|
| **Supervisor** | LangGraph Agent | `create_react_agent` with checkpointer for session persistence |
| **CV Parser** | LangGraph Subgraph | Background document processing with retry logic |
| **Profile Tools** | @tool functions | CRUD operations for user profile data |
| **Parsing Tools** | @tool functions | Check CV parsing status and results |
| **Q&A Tool** | @tool function | Service information and FAQs |
| **Message Manager** | Module | Token-based trimming with tiktoken |

## Tech Stack

- **Runtime**: Python 3.13
- **Agent Framework**: LangGraph 0.2 with `create_react_agent`
- **LLM**: OpenAI gpt-4o-mini
- **Token Counting**: tiktoken
- **Document Processing**: Markitdown (PDF, DOCX)
- **Web UI**: Chainlit 2.9
- **API**: FastAPI
- **Database**: Supabase (planned)
- **Deployment**: Fly.io (Singapore region)

## Quick Start

### Prerequisites

- Python 3.13+
- Poetry
- OpenAI API key

### Setup

```bash
# Install dependencies
poetry install

# Configure environment
cp .env.example .env
# Add your OPENAI_API_KEY to .env

# Run both services
poetry run uvicorn app.main:app --port 8080 &
poetry run chainlit run chainlit_app.py -w
```

Open http://localhost:8000 to:
- Chat with the AI assistant
- Upload PDF/DOCX CVs for parsing
- Build your job seeker profile

## Project Structure

```
app/
  assistant/
    supervisor.py          # LangGraph create_react_agent supervisor
    cv_parsing_graph.py    # LangGraph subgraph for CV parsing
    message_management.py  # Token-based message trimming
    handler.py             # WhatsApp message handler
    prompts.py             # System prompts
    tools/
      __init__.py          # Tool factory (create_all_tools)
      profile.py           # Profile management tools
      parsing_status.py    # CV parsing status tools
      qa.py                # Service Q&A tool
  documents/
    parsing.py             # Markitdown + LLM extraction
  api/
    routes.py              # REST API endpoints
  whatsapp/
    webhook.py             # WhatsApp webhook handler
  config.py                # Settings from .env
  constants.py             # Shared constants
  utils.py                 # Shared utilities
chainlit_app.py            # Chainlit web UI
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat` | Send chat message |
| POST | `/api/parse-cv` | Upload and parse CV |
| GET | `/api/profile/{user_id}` | Get user profile |
| POST | `/api/profile/{user_id}` | Update user profile |
| POST | `/whatsapp/webhook` | WhatsApp webhook |

## Current Status

### Working
- Chainlit web interface
- LangGraph supervisor agent with `create_react_agent`
- Session persistence via MemorySaver checkpointer
- Token-based message trimming (prevents context overflow)
- Profile management (get, update, validate)
- CV parsing (PDF, DOCX) via LangGraph subgraph
- Background document processing (non-blocking)
- WhatsApp message handling
- REST API
- Deployed on Fly.io

### TODO
- Database persistence (Supabase)
- WhatsApp media download for CV uploads
- Job matching algorithm
- Multi-language support

## Development

### Running Tests

```bash
poetry run pytest tests/
```

### Benchmarks

CV parsing benchmarks are in `/benchmarks/`:
- `cv_comparison_test.py` - Compare extraction methods
- `pymupdf_vs_markitdown_test.py` - Parser comparison

## Deployment

### Fly.io

Two separate apps for API and UI:

```bash
# Deploy backend API
fly deploy -c fly.api.toml
fly secrets set OPENAI_API_KEY=sk-... -a matcha-ai-api

# Deploy frontend UI
fly deploy -c fly.ui.toml
```

**Live URLs:**
- UI: https://matcha-ai-ui.fly.dev
- API: https://matcha-ai-api.fly.dev

## Environment Variables

```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
OPENAI_TEMPERATURE=0.7

# Optional
SUPABASE_URL=https://...
SUPABASE_KEY=...
WHATSAPP_TOKEN=...
WHATSAPP_PHONE_NUMBER_ID=...
WHATSAPP_VERIFY_TOKEN=...
```

## License

Proprietary
