# Matcha AI

Job matching assistant powered by a ReAct supervisor agent. Helps job seekers create profiles through conversational AI via WhatsApp or web interface.

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
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      SUPERVISOR AGENT                                    │
│                   app/assistant/supervisor.py                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   ReAct Agent Loop (max 5 iterations)                                    │
│   ┌─────────┐    ┌─────────────┐    ┌─────────────┐                     │
│   │  LLM    │ ─► │ Tool Calls? │ ─► │  Execute    │                     │
│   │ Reason  │    │             │    │  Tools      │                     │
│   └─────────┘    └──────┬──────┘    └──────┬──────┘                     │
│        ▲                │ No               │                             │
│        └────────────────┴──────────────────┘                             │
│                                                                          │
│   - Model: gpt-4o-mini                                                   │
│   - Memory: Windowed (last 10 messages)                                  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           TOOLS                                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  PROFILE TOOLS              DOCUMENT TOOLS         Q&A TOOLS             │
│  ─────────────              ──────────────         ─────────             │
│  get_profile()              parse_cv()             get_service_info()    │
│  update_profile_field()     - Markitdown extract   - About, process      │
│  get_missing_fields()       - LLM JSON parsing     - Privacy, help       │
│  validate_profile()         - Auto profile update                        │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      CV PARSING CHAIN                                    │
│                   app/documents/parsing.py                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   Document → Markitdown → LLM Chain → JSON Profile                       │
│                                                                          │
│   Supported: PDF, DOCX, DOC                                              │
│   Output: name, email, work_experience, education, skills, etc.          │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Components

| Component | Type | Purpose |
|-----------|------|---------|
| **Supervisor** | ReAct Agent | Orchestrates conversation, decides which tools to call |
| **Profile Tools** | @tool functions | CRUD operations for user profile data |
| **Document Tool** | @tool function | CV parsing and data extraction |
| **Q&A Tool** | @tool function | Service information and FAQs |
| **CV Chain** | LCEL Chain | Prompt → LLM → JSON Parser |

## Tech Stack

- **Runtime**: Python 3.13
- **Agent Framework**: LangChain 0.3 with ReAct pattern
- **LLM**: OpenAI gpt-4o-mini
- **Document Processing**: Markitdown (PDF, DOCX)
- **Web UI**: Chainlit 2.9
- **API**: FastAPI
- **Database**: Supabase (planned)
- **Deployment**: Fly.io

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
    supervisor.py    # ReAct supervisor agent
    handler.py       # WhatsApp message handler
    prompts.py       # CV extraction prompt
    tools/
      profile.py     # Profile management tools
      documents.py   # Document parsing tool
      qa.py          # Service Q&A tool
  documents/
    parsing.py       # Markitdown + LLM extraction
  api/
    routes.py        # REST API endpoints
  whatsapp/
    webhook.py       # WhatsApp webhook handler
  config.py          # Settings from .env
  llm.py             # OpenAI client factory
  utils.py           # Shared utilities
chainlit_app.py      # Chainlit web UI
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
- ReAct supervisor agent with tool calling
- Profile management (get, update, validate)
- CV parsing (PDF, DOCX) with structured extraction
- WhatsApp message handling
- REST API

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

```bash
fly auth login
fly launch
fly secrets set OPENAI_API_KEY=sk-...
fly deploy
```

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
