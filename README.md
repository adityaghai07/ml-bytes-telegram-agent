# ML Bytes Telegram Bot

Agentic community management bot with auto-moderation, FAQ matching, and mentor routing.

## Features

- Auto-moderation with LLM-based spam/content filtering
- Smart FAQ responses using semantic similarity (RAG)
- Automatic mentor tagging for domain-specific questions

## Setup

```bash
# Install
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your tokens and credentials

# Initialize data
python -m bot.utils.load_faqs      # Load FAQs
python -m bot.utils.sync_mentors   # Sync mentors

# Run
python -m bot.main
```

## Configuration

Required in `.env`:
- `TELEGRAM_BOT_TOKEN` - From @BotFather
- `DATABASE_URL` - PostgreSQL connection
- `LLM_PROVIDER` - openai/anthropic/gemini
- `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `GEMINI_API_KEY`
- `ADMIN_IDS` - Comma-separated Telegram user IDs
- `MENTOR_DOMAINS` - JSON: `{"domain": [user_id1, user_id2]}`

## Architecture Overview

### Message Processing Flow

```mermaid
flowchart TD
    Start([User sends message]) --> Receive[Bot receives message]
    Receive --> GetUser[Get/Create user in DB]
    GetUser --> CheckElevated{Is Admin or Mentor?}

    CheckElevated -->|Yes| Skip[Skip processing]
    Skip --> End([End])

    CheckElevated -->|No| Store[Store message in DB]
    Store --> Moderate[LLM Moderation Check]

    Moderate --> IsSpam{Is spam/inappropriate?}
    IsSpam -->|Yes| Delete[Delete message]
    IsSpam -->|Yes| LogMod[Log to moderation_logs]
    Delete --> End
    LogMod --> End

    IsSpam -->|No| FAQ[FAQ Similarity Search]
    FAQ --> HasMatch{Match found?}

    HasMatch -->|Yes| ReplyFAQ[Reply with FAQ answer]
    HasMatch -->|Yes| UpdateCount[Increment times_matched]
    ReplyFAQ --> End
    UpdateCount --> End

    HasMatch -->|No| Route[LLM Routing Analysis]
    Route --> ShouldTag{Should tag mentors?}

    ShouldTag -->|No| End
    ShouldTag -->|Yes| FindMentors[Find mentors by domain]
    FindMentors --> TagMentors[Tag mentors in reply]
    TagMentors --> LogTag[Log to mentor_tags]
    LogTag --> End

    style Start fill:#e1f5ff
    style End fill:#e1f5ff
    style Delete fill:#ffe1e1
    style ReplyFAQ fill:#e1ffe1
    style TagMentors fill:#fff4e1
```

### Database Schema

```mermaid
erDiagram
    users ||--o{ messages : creates
    users ||--o{ faqs : creates
    users ||--o{ mentor_tags : "tagged in"
    messages ||--o{ mentor_tags : "has tags"
    messages ||--o{ moderation_logs : "has logs"
    users ||--o{ moderation_logs : "moderated"

    users {
        int id PK
        bigint telegram_id UK
        string username
        string first_name
        string last_name
        boolean is_admin
        boolean is_mentor
        array expertise_domains
        datetime joined_at
        datetime last_active
    }

    messages {
        int id PK
        int user_id FK
        text text
        bigint telegram_message_id
        boolean is_deleted
        string deletion_reason
        datetime sent_at
    }

    faqs {
        int id PK
        text question
        text answer
        string category
        array embedding
        int created_by FK
        datetime created_at
        datetime updated_at
        int times_matched
    }

    mentor_tags {
        int id PK
        int message_id FK
        int mentor_id FK
        string reason
        datetime tagged_at
        boolean responded
        datetime responded_at
    }

    moderation_logs {
        int id PK
        int message_id FK
        int user_id FK
        string action
        string reason
        float confidence
        text message_text
        datetime moderated_at
        string llm_provider
    }
```

## Project Structure

```
bot/
├── handlers/       # Telegram update handlers
├── services/       # Business logic (moderation, FAQ, routing)
├── llm/           # LLM provider wrappers
├── db/            # Database models
└── utils/         # Config, logging, utilities
```

## Tech Stack

python-telegram-bot • SQLAlchemy • pgvector • OpenAI/Anthropic/Gemini
