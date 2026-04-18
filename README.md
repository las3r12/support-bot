# Support Bot

An AI-powered customer support chatbot platform. Deploy customizable support bots on your website using a knowledge base built from your own documentation and web content.

## Features

- **Embeddable widget** — drop a `<script>` tag on any site to add a chatbot
- **Knowledge base** — add text sources manually or by web scraping (depth 0–2)
- **Semantic search** — vector embeddings (all-MiniLM-L6-v2) via PostgreSQL pgvector
- **LLM responses** — powered by OpenRouter (default: Nvidia Nemotron-3 Nano-30B)
- **Multi-bot support** — create multiple bots per account, each with its own token
- **Credit system** — each question costs 1 credit; admin can manage balances
- **Prompt injection protection** — nonce-based DATA tags in the system prompt

## Tech Stack

- **Backend:** Flask 3, Python 3.12
- **Database:** PostgreSQL + pgvector
- **Embeddings:** SentenceTransformers (all-MiniLM-L6-v2)
- **LLM API:** OpenRouter
- **Auth:** Argon2 password hashing, session-based login
- **Frontend:** Jinja2 templates, vanilla JS widget (shadow DOM)

## Setup

### Prerequisites

- Python 3.12
- PostgreSQL with the [pgvector](https://github.com/pgvector/pgvector) extension installed

### 1. Create the database

```bash
createdb bot_db
createuser cyber_user
psql -c "ALTER USER cyber_user WITH PASSWORD 'your_password';"
psql -c "GRANT ALL PRIVILEGES ON DATABASE bot_db TO cyber_user;"
```

### 2. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure

Edit `resources/config.json`:

```json
{
  "llm_key": "your-openrouter-api-key",
  "db_name": "bot_db",
  "db_user": "cyber_user",
  "db_password": "your_password",
  "max_context_len": 300000,
  "no_credits_msg": "You have run out of credits."
}
```

### 4. Run

```bash
python app.py
```

The app starts at `http://localhost:5000`. Database tables are created automatically on first run.

## Embedding the Widget

After creating a bot in the dashboard, copy the embed snippet from the widget page:

```html
<script src="http://your-server/static/widget.js"
        data-token="your-bot-token"
        data-url="http://your-server">
</script>
```

Add it to any HTML page. The widget renders as a floating chat button with full conversation history.

## Project Structure

```
support-bot/
├── app.py              # Flask routes (auth, bot management, admin)
├── api.py              # OpenRouter LLM client
├── db_pool.py          # PostgreSQL connection pool and all queries
├── content.py          # Threaded web scraper
├── embedder.py         # Text chunking and vector embedding
├── resources/
│   ├── config.json     # API keys and database credentials
│   ├── schema.sql      # Database schema
│   └── prompt.txt      # LLM system prompt
├── static/
│   └── widget.js       # Embeddable chatbot widget
└── templates/          # Jinja2 HTML templates
```