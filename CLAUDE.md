# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python Discord bot called "Rose Ashcombe" - an AI-powered executive assistant that integrates with Google Calendar, Gmail, Weather APIs, and OpenAI Assistant. The bot provides comprehensive calendar management, email handling, weather briefings, and productivity assistance through Discord.

## Development Commands

### Running the Bot
```bash
python main.py
```

### Installing Dependencies
```bash
pip install -r requirements.txt
```

### Testing Weather Integration
The bot includes built-in weather testing that runs on startup when `WEATHER_API_KEY` is configured.

## Architecture Overview

### Core Files
- **main.py** - Primary bot implementation with full functionality
- **main_calendar.py** - Duplicate/backup of main.py 
- **main_Stable_Jul 27.py** - Backup version from July 27
- **rose_calendar_functions.py** - Extracted Google Calendar functions
- **requirements.txt** - Python dependencies

### Key Components

#### 1. Discord Bot Framework
- Uses discord.py with command prefix `!`
- Supports both commands and AI assistant chat via mentions
- Channel restrictions: `['life-os', 'calendar', 'planning-hub', 'general']`

#### 2. Google Services Integration
- **Calendar Service**: Service account authentication for multi-calendar access
- **Gmail Service**: OAuth2 authentication for email management
- Supports multiple calendars: Personal, Work, Tasks, and shared calendars

#### 3. AI Assistant Integration
- OpenAI Assistant API integration with function calling
- Persistent conversation threads per user
- Function handlers for calendar and email operations

#### 4. External APIs
- WeatherAPI.com integration for weather data
- Brave Search API for web search capabilities
- Timezone handling for Toronto/Eastern time

### Environment Variables Required

#### Critical Variables
- `DISCORD_TOKEN` or `ROSE_DISCORD_TOKEN` - Discord bot token
- `OPENAI_API_KEY` - OpenAI API key  
- `ROSE_ASSISTANT_ID` or `ASSISTANT_ID` - OpenAI Assistant ID

#### Google Services
- `GOOGLE_SERVICE_ACCOUNT_JSON` - Service account credentials (JSON string)
- `GMAIL_OAUTH_JSON` - Gmail OAuth client config
- `GMAIL_TOKEN_JSON` - Gmail OAuth tokens
- `GOOGLE_CALENDAR_ID`, `GOOGLE_TASKS_CALENDAR_ID`, etc. - Calendar IDs

#### Optional Services
- `WEATHER_API_KEY` - WeatherAPI.com key
- `BRAVE_API_KEY` - Brave Search API key
- `USER_CITY`, `USER_LAT`, `USER_LON` - Location for weather

### Function Capabilities

The bot supports these main function categories:

#### Calendar Functions (main.py:359-763)
- `create_gcal_event()` - Create calendar events
- `update_gcal_event()` - Modify existing events  
- `delete_gcal_event()` - Remove events
- `list_gcal_events()` - Query events with filters
- `fetch_gcal_event()` - Get event details
- `find_free_time()` - Check availability across calendars

#### Email Functions (main.py:768-977)
- `get_recent_emails()` - Fetch recent/unread emails
- `search_emails()` - Query emails with filters
- `get_email_stats()` - Email analytics
- `delete_emails_from_sender()` - Bulk email deletion

#### Discord Commands (main.py:1491-1767)
- `!briefing` - Morning briefing with weather and calendar
- `!weather` - Current weather conditions
- `!schedule` - Today's calendar
- `!upcoming [days]` - Future events
- `!emails [count]` - Recent emails
- `!unread [count]` - Unread emails only
- Administrative commands: `!ping`, `!status`, `!help`

### Error Handling

The codebase includes comprehensive error handling:
- Google API authentication and access errors
- Discord rate limiting and message size limits
- OpenAI Assistant timeout and function call errors
- Graceful degradation when services are unavailable

### Security Considerations

- OAuth2 tokens and service account credentials are stored as environment variables
- Email deletion operations require user confirmation via Discord reactions
- Rate limiting prevents abuse of AI assistant features
- Channel restrictions limit bot access to authorized Discord channels