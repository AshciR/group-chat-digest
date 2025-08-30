# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Telegram bot called "Chat Nuff Bot" that summarizes group chat messages using OpenAI's GPT models. The bot stores the last 200 messages from whitelisted chats in Redis and can generate summaries in paragraph or bullet point format, optionally as voice messages.

## Development Commands

### Using uv (Recommended)
- `uv sync` - Initialize virtual environment and install dependencies
- `docker-compose up -d` - Start the application with Docker Compose (detached mode)
- `docker-compose up -d --build` - Build and start with Docker Compose (--build flag)
- `docker-compose down` - Stop Docker containers
- `docker-compose up -d redis` - Start only the Redis container
- `uv run pytest -n auto tests --spec` - Run tests with pytest in parallel
- `uv run ruff check src/` - Run Ruff linter on source code

### Alternative Commands
- `docker-compose up -d` - Start application without building
- `docker-compose up -d --build` - Build and start application
- `pytest -n auto tests --spec` - Run tests directly with pytest

## Code Architecture

### Core Components

**main.py**: Entry point that starts both the Telegram bot and web server concurrently using asyncio.

**telegram_bot.py**: Contains all bot command handlers and the main application setup. Key handler types:
- User commands: `/start`, `/summary`, `/gist`, `/whisper`, `/whspr`, `/help`, `/privacy`
- Admin commands: `/replay`, `/status`, `/alert`, `/analytics`
- Message listener that stores all non-spoiler messages

**models.py**: Contains shared data models, primarily the Message dataclass used throughout the application.

**message_storage.py**: Manages Redis operations for message persistence. Implements FIFO storage limited to 200 messages per chat with integrated encryption support.

**encryption_utils.py**: Handles application-level encryption for message content using Fernet symmetric encryption. Provides backward compatibility for unencrypted messages during migration.

**openai_utils.py**: Handles OpenAI API integration for text summarization and text-to-speech conversion using GPT-4o-mini model.

**server.py**: Simple Starlette web server providing health check endpoint at `/status`.

**white_list.py**: Manages chat and user access control (not examined but referenced throughout).

### Message Flow
1. Telegram messages are received via webhook/polling
2. Messages are optionally encrypted (if enabled) and stored in Redis with chat_id as key
3. Summary commands retrieve N messages, decrypt them if needed, format them, and send to OpenAI
4. Responses can be text or voice messages delivered publicly or privately

### Key Configuration
- Redis connection configured via environment variables (host, port, TLS, timeout)
- OpenAI API key required for summarization and TTS features
- Telegram bot token required for bot functionality
- Message encryption configured via ENCRYPTION_ENABLED and ENCRYPTION_KEY env vars
- Supports local development mode via LOCAL env var

## Environment Setup

Copy `.env.template` to `.env` and configure:
- `TELEGRAM_API_KEY` - Bot token from BotFather
- `OPENAI_API_KEY` - OpenAI API key for GPT and TTS
- Redis connection settings (defaults work for local development)
- `ENCRYPTION_KEY` - Base64-encoded encryption key (generate with `python generate_encryption_key.py`)
- `ENCRYPTION_ENABLED` - Set to True to enable message content encryption

## Testing

The project uses pytest with parallel execution and pytest-spec for readable output. Tests use fakeredis for Redis mocking and pytest-mock for other mocking needs.

## Deployment

Application is containerized with Docker and includes GitHub Actions CI that runs tests on Python 3.12. The production deployment likely uses Redis with TLS enabled.

## Message Storage Limits

- Maximum 200 messages stored per chat (MAX_MESSAGE_STORAGE)
- Default summary length is 100 messages (DEFAULT_MESSAGE_STORAGE)
- Messages with spoiler entities are automatically excluded from storage