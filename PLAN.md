# Telegram Video Generation Bot - Project Plan

## Overview
Telegram bot that generates videos using Google Veo API. Regular messages are treated as prompts. Slash commands configure settings. Settings stored in-memory. Tracks each message individually with user, timestamp, tokens, model, cost, etc. (no prompts/videos stored).

## Features

### Commands
- `/start` - Welcome message
- `/help` - Usage instructions
- `/settings` - View current settings
- `/setmodel <model>` - Set Veo model (e.g., `veo-3.1`)
- `/setduration <seconds>` - Set video duration - **Do not implement for now**
- `/setresolution <width>x<height>` - Set resolution - **Do not implement for now**
- `/reset` - Reset to defaults
- `/stats` - View usage stats (shared across all users - shows stats of all users)

### Message Flow
1. User sends regular message → treated as prompt
2. Bot calls Veo API with prompt + user settings
3. Bot downloads generated video
4. Bot uploads video to Telegram
5. Bot sends video to user
6. Temporary files cleaned up

## Tech Stack
- Python 3.13
- `aiogram`
- `google-cloud-aiplatform` for Veo API
- In-memory storage: SQLite

## Project Structure
```
telegram-video-gen/
├── bot/
│   ├── main.py             # Bot entry point
│   ├── handlers/
│   │   ├── commands.py     # Slash command handlers
│   │   └── messages.py     # Regular message handler
├── veo/
│   └── client.py           # Veo API wrapper
├── database/
│   ├── settings.py         # In-memory settings storage
│   └── messages.py         # Track individual messages with details
├── storage/
│   └── manager.py          # Temp file handling
├── config/
│   └── settings.py         # Config management
└── requirements.txt
```

## Data Models

### Settings (in-memory)
```python
{user_id: int, model: str, duration: int, resolution: str}
```

### Messages (in-memory)
```python
{
    id: int,                    # Message ID
    user_id: int,              # Telegram user ID
    username: str,              # Telegram username (e.g., "Marco")
    timestamp: datetime,        # When message was sent
    prompt_tokens: int,        # Input prompt tokens
    output_prompt_tokens: int, # Output prompt tokens (if enhanced)
    model: str,                 # Model used (e.g., "veo-3.1-generate-001")
    cost: float,               # Generation cost
    duration_seconds: int,      # Video duration
    resolution: str,            # Video resolution
    status: str                # "success", "failed", etc.
}
```

**Note**: Prompts and videos are NOT stored. Each message is tracked individually.

## Implementation Steps

1. **Setup**
   - Project structure
   - Google Cloud credentials
   - Veo API client

2. **Telegram Bot**
   - Basic bot with `/start`, `/help`
   - Route messages vs commands

3. **Video Generation**
   - Message handler → Veo API → download → upload to Telegram

4. **Settings**
   - In-memory storage
   - Commands: `/settings`, `/setmodel`, `/setduration`, `/setresolution`, `/reset`

5. **Usage Tracking**
   - Store each message as individual record with user, timestamp, tokens, model, cost, etc.
   - `/stats` command (shows stats of all users, shared across users)

## Environment Variables
```bash
TELEGRAM_BOT_TOKEN=...
GOOGLE_CLOUD_PROJECT_ID=...
GOOGLE_APPLICATION_CREDENTIALS=path/to/key.json
```
