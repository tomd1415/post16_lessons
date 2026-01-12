# System Architecture

## Tech Stack

### Backend
- **Language**: Python 3.11+
- **Framework**: FastAPI (async, high performance, automatic OpenAPI docs)
- **Database**: PostgreSQL 15+ with psycopg (async driver)
- **ORM**: SQLAlchemy 2.0 (async mode)
- **Migrations**: Alembic
- **AI Integration**: OpenAI Python SDK (`openai` package)
- **Document Processing**: `python-docx`, `python-pptx`
- **Validation**: Pydantic v2

### Frontend
- **Approach**: Vanilla JavaScript (no frameworks)
- **Styling**: CSS with CSS variables for theming
- **Build**: No build step required (serves static files)
- **Compatibility**: Must work on Chrome (Chromebooks), also Firefox, Edge

### Infrastructure
- **Containerisation**: Docker with Docker Compose
- **Reverse Proxy**: Caddy (automatic HTTPS, simple config)
- **Target Deployment**: Single Debian 12 VM on school network

## Project Structure

```
ks3-assessment/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app, middleware, startup
│   │   ├── config.py               # Environment configuration
│   │   ├── db.py                   # Database connection, session management
│   │   │
│   │   ├── models/                 # SQLAlchemy models
│   │   │   ├── __init__.py
│   │   │   ├── user.py             # Teacher, Pupil, Admin models
│   │   │   ├── assessment.py       # Assessment, Question, Attempt models
│   │   │   ├── unit.py             # Unit, Topic, LearningObjective models
│   │   │   └── result.py           # Result, Answer, Analytics models
│   │   │
│   │   ├── schemas/                # Pydantic request/response schemas
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── assessment.py
│   │   │   ├── question.py
│   │   │   └── analytics.py
│   │   │
│   │   ├── routers/                # API route handlers
│   │   │   ├── __init__.py
│   │   │   ├── auth.py             # Login, logout, session management
│   │   │   ├── assessments.py      # CRUD assessments
│   │   │   ├── questions.py        # Question management
│   │   │   ├── attempts.py         # Pupil attempts and answers
│   │   │   ├── analytics.py        # Teacher analytics endpoints
│   │   │   ├── generation.py       # AI generation endpoints
│   │   │   └── documents.py        # Document upload and processing
│   │   │
│   │   ├── services/               # Business logic
│   │   │   ├── __init__.py
│   │   │   ├── auth_service.py
│   │   │   ├── assessment_service.py
│   │   │   ├── ai_generator.py     # OpenAI integration
│   │   │   ├── document_parser.py  # .docx/.pptx parsing
│   │   │   ├── marker.py           # Auto-marking logic
│   │   │   └── analytics_service.py
│   │   │
│   │   └── utils/                  # Helpers
│   │       ├── __init__.py
│   │       ├── security.py         # Password hashing, session tokens
│   │       └── feedback.py         # Encouraging feedback generator
│   │
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py             # pytest fixtures
│   │   ├── test_auth.py
│   │   ├── test_assessments.py
│   │   ├── test_generation.py
│   │   └── test_marking.py
│   │
│   ├── alembic/                    # Database migrations
│   │   ├── versions/
│   │   └── env.py
│   │
│   ├── requirements.txt
│   ├── Dockerfile
│   └── alembic.ini
│
├── web/                            # Frontend static files
│   ├── index.html                  # Login page
│   ├── css/
│   │   ├── main.css
│   │   ├── variables.css           # Theme variables
│   │   ├── components.css
│   │   └── accessibility.css
│   │
│   ├── js/
│   │   ├── app.js                  # Main app, routing
│   │   ├── api.js                  # API client
│   │   ├── auth.js                 # Authentication
│   │   │
│   │   ├── teacher/                # Teacher-specific JS
│   │   │   ├── dashboard.js
│   │   │   ├── create-assessment.js
│   │   │   ├── review-questions.js
│   │   │   ├── analytics.js
│   │   │   └── pupil-view.js
│   │   │
│   │   ├── pupil/                  # Pupil-specific JS
│   │   │   ├── dashboard.js
│   │   │   ├── assessment.js
│   │   │   ├── question-renderer.js
│   │   │   └── results.js
│   │   │
│   │   └── components/             # Reusable components
│   │       ├── question-types/     # One file per question type
│   │       │   ├── multiple-choice.js
│   │       │   ├── python-code.js
│   │       │   ├── matching.js
│   │       │   ├── parsons.js
│   │       │   ├── text-input.js
│   │       │   └── ...
│   │       ├── modal.js
│   │       ├── toast.js
│   │       └── chart.js
│   │
│   ├── teacher/                    # Teacher HTML pages
│   │   ├── dashboard.html
│   │   ├── create-assessment.html
│   │   ├── review-questions.html
│   │   ├── class-results.html
│   │   └── pupil-detail.html
│   │
│   └── pupil/                      # Pupil HTML pages
│       ├── dashboard.html
│       ├── assessment.html
│       └── results.html
│
├── docker/
│   ├── Caddyfile                   # Reverse proxy config
│   ├── Dockerfile.api
│   └── certs/                      # TLS certificates (gitignored)
│
├── docs/                           # Documentation
│   └── ...
│
├── assessment_prompts/             # These prompt documents
│   └── ...
│
├── compose.yml                     # Docker Compose for development
├── compose.prod.yml                # Docker Compose for production
├── .env.example
├── .gitignore
└── README.md
```

## Environment Variables

```bash
# .env.example

# Database
POSTGRES_USER=assessment_user
POSTGRES_PASSWORD=change_me_in_production
POSTGRES_DB=ks3_assessment
DATABASE_URL=postgresql+psycopg://assessment_user:change_me_in_production@db:5432/ks3_assessment

# Session
SESSION_SECRET=generate_a_random_32_byte_string
SESSION_TTL_MINUTES=480

# OpenAI API
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4-turbo
OPENAI_MAX_TOKENS=4096

# Document Processing
MAX_UPLOAD_SIZE_MB=50
ALLOWED_EXTENSIONS=.docx,.pptx,.pdf

# Rate Limiting
RATE_LIMIT_GENERATION=10  # AI generations per hour per teacher
RATE_LIMIT_ATTEMPTS=100   # Assessment attempts per hour per pupil

# Feature Flags
ENABLE_PYTHON_RUNNER=true
ENABLE_IMMEDIATE_FEEDBACK=true
```

## Docker Compose (Development)

```yaml
# compose.yml
version: '3.8'

services:
  proxy:
    image: caddy:2-alpine
    ports:
      - "8080:8080"
      - "8443:8443"
    volumes:
      - ./docker/Caddyfile:/etc/caddy/Caddyfile:ro
      - ./web:/srv:ro
    depends_on:
      - api
    networks:
      - assessment-network

  api:
    build:
      context: ./backend
      dockerfile: Dockerfile
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - SESSION_SECRET=${SESSION_SECRET}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - OPENAI_MODEL=${OPENAI_MODEL:-gpt-4-turbo}
    volumes:
      - ./backend/app:/app/app:ro
      - uploads:/app/uploads
    depends_on:
      db:
        condition: service_healthy
    networks:
      - assessment-network

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - assessment-network

networks:
  assessment-network:

volumes:
  postgres_data:
  uploads:
```

## Caddyfile

```caddyfile
{
    admin off
}

http://:8080 {
    redir https://{host}:8443{uri}
}

https://:8443 {
    tls internal {
        on_demand
    }

    # Security headers
    header {
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        X-XSS-Protection "1; mode=block"
        Referrer-Policy "strict-origin-when-cross-origin"
        Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self'; connect-src 'self'; frame-ancestors 'none';"
    }

    # API routes
    handle /api/* {
        reverse_proxy api:8000 {
            header_up X-Real-IP {remote_host}
            header_up X-Forwarded-For {remote_host}
            header_up X-Forwarded-Proto {scheme}
        }
    }

    # Static files
    handle {
        root * /srv
        file_server
        try_files {path} /index.html
    }
}
```

## Backend Dockerfile

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Run with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Requirements

```txt
# backend/requirements.txt
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
sqlalchemy>=2.0.25
psycopg[binary]>=3.1.17
alembic>=1.13.1
pydantic>=2.5.3
pydantic-settings>=2.1.0
python-multipart>=0.0.6
python-docx>=1.1.0
python-pptx>=0.6.23
openai>=1.10.0
bcrypt>=4.1.2
pytest>=7.4.4
pytest-asyncio>=0.23.3
httpx>=0.26.0
```

## Key Configuration Notes

### OpenAI Integration
- Use the `openai` Python package v1.x+
- Use `client.responses.create()` for structured output (if using responses endpoint)
- Or use `client.chat.completions.create()` for standard chat completions
- Always set `max_tokens` to control costs
- Implement retry logic for rate limits

### Database Connections
- Use async SQLAlchemy with `psycopg` driver
- Configure connection pool for concurrent access (30+ pupils)
- Use read replicas if scaling beyond single VM

### File Uploads
- Store uploaded documents temporarily for processing
- Extract content, then delete original files
- Never expose uploaded files directly to web

### Session Management
- Server-side sessions stored in database
- Secure HTTP-only cookies
- CSRF protection on state-changing endpoints

## Next Steps

After setting up the basic structure:
1. See `02-question-types.md` for question specifications
2. See `04-database-schema.md` for database design
3. See `05-api-endpoints.md` for API routes
