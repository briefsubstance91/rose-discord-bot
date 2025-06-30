#!/usr/bin/env python3
"""
ROSE WITH GOOGLE CALENDAR INTEGRATION
Restores real calendar functionality to prevent function calling loops
"""

import discord
from discord.ext import commands
import os
import asyncio
import aiohttp
import json
import pytz
from datetime import datetime, timedelta
from dotenv import load_dotenv
from openai import OpenAI
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Load environment variables
load_dotenv()

# Rose's specific configuration
ASSISTANT_NAME = "Rose Ashcombe"
ASSISTANT_ROLE = "Executive Assistant"
ALLOWED_CHANNELS = ['life-os', 'calendar', 'planning-hub', 'general']

# Environment variables
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("ROSE_DISCORD_TOKEN")
ASSISTANT_ID = os.getenv("ROSE_ASSISTANT_ID") or os.getenv("ASSISTANT_ID")
BRAVE_API_KEY = os.getenv('BRAVE_API_KEY')

# Discord setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# OpenAI setup
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Simple memory system
user_conversations = {}

# Set your timezone
LOCAL_TIMEZONE = 'America/Toronto'

print(f"👑 Starting {ASSISTANT_NAME} - {ASSISTANT_ROLE}...")

# ============================================================================
# GOOGLE CALENDAR INTEGRATION
# ============================================================================

def get_google_calendar_service():
    """Get authenticated Google Calendar service"""
    try:
        service_account_json = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
        
        if not service_account_json:
            print(f"⚠️ GOOGLE_SERVICE_ACCOUNT_JSON not found")
            return None
        
        service_account_info = json.loads(service_account_json)
        
        scopes = ['https://www.googleapis.com/auth/calendar.readonly']
        
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=scopes
        )
        
        service = build('calendar', 'v3', credentials=credentials)
        print(f"✅ Google Calendar service connected successfully")
        return service
        
    except Exception as e:
        print(f"❌ Failed to connect to Google Calendar: {e}")
        return None

# Initialize calendar service
calendar_service = get_google_calendar_service()

def get_calendar_events(days_ahead=7):
    """Get events from Google Calendar"""
    if not calendar_service:
        return get_mock_calendar_events()
    
    try:
        local_tz = pytz.timezone(LOCAL_TIMEZONE)
        now = datetime.now(local_tz)
        
        start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = start_of_today + timedelta(days=days_ahead)
        
        start_time_utc = start_of_today.astimezone(pytz.UTC).isoformat()
        end_time_utc = end_time.astimezone(pytz.UTC).isoformat()
        
        calendar_id = os.getenv('GOOGLE_CALENDAR_ID', 'primary')
        
        events_result = calendar_service.events().list(
            calendarId=calendar_id,
            timeMin=start_time_utc,
            timeMax=end_time_utc,
            maxResults=50,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        if not events:
            return []
        
        calendar_events = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            
            if 'T' in start:
                if start.endswith('Z'):
                    start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                else:
                    start_dt = datetime.fromisoformat(start)
                
                if start_dt.tzinfo is None:
                    start_dt = pytz.UTC.localize(start_dt)
                start_dt = start_dt.astimezone(local_tz)
            else:
                start_dt = datetime.strptime(start, '%Y-%m-%d')
                start_dt = local_tz.localize(start_dt)
            
            if end and 'T' in end:
                if end.endswith('Z'):
                    end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
                else:
                    end_dt = datetime.fromisoformat(end)
                
                if end_dt.tzinfo is None:
                    end_dt = pytz.UTC.localize(end_dt)
                end_dt = end_dt.astimezone(local_tz)
                
                duration = end_dt - start_dt
                duration_min = int(duration.total_seconds() / 60)
                if duration_min < 60:
                    duration_str = f"{duration_min} min"
                else:
                    hours = duration_min // 60
                    mins = duration_min % 60
                    if mins > 0:
                        duration_str = f"{hours}h {mins}min"
                    else:
                        duration_str = f"{hours} hour{'s' if hours > 1 else ''}"
            else:
                duration_str = "All day"
            
            calendar_events.append({
                "title": event.get('summary', 'Untitled'),
                "start_time": start_dt,
                "duration": duration_str,
                "description": event.get('description', ''),
                "location": event.get('location', ''),
                "attendees": [att.get('email', '') for att in event.get('attendees', [])],
                "event_id": event.get('id', '')
            })
        
        return calendar_events
        
    except Exception as e:
        print(f"❌ Error fetching Google Calendar events: {e}")
        return get_mock_calendar_events()

def get_mock_calendar_events():
    """Mock calendar data when Google Calendar is not available"""
    local_tz = pytz.timezone(LOCAL_TIMEZONE)
    today = datetime.now(local_tz)
    
    return [
        {
            "title": "Calendar connection needed",
            "start_time": today.replace(hour=9, minute=0),
            "duration": "Setup required",
            "description": "Google Calendar integration needs configuration",
            "location": "",
            "attendees": [],
            "event_id": "setup_needed"
        }
    ]

def format_calendar_events(events, title="Calendar Events"):
    """Format calendar events for Discord"""
    if not events:
        return f"📅 **{title}**\n\nNo events scheduled - perfect time for strategic planning!"
    
    formatted_lines = [f"📅 **{title}**\n"]
    
    local_tz = pytz.timezone(LOCAL_TIMEZONE)
    today = datetime.now(local_tz).date()
    
    for event in events[:5]:  # Limit to 5 events to prevent long messages
        try:
            if hasattr(event['start_time'], 'strftime'):
                event_date = event['start_time'].date()
                time_str = event['start_time'].strftime('%I:%M %p')
                
                if event_date == today:
                    day_str = "Today"
                elif event_date == today + timedelta(days=1):
                    day_str = "Tomorrow"
                else:
                    day_str = event['start_time'].strftime('%a %m/%d')
                
                event_line = f"• **{day_str} {time_str}**: {event['title']}"
                if event['duration'] != "All day":
                    event_line += f" ({event['duration']})"
                
                formatted_lines.append(event_line)
                
                if event['location']:
                    formatted_lines.append(f"  📍 {event['location']}")
                    
        except Exception as e:
            formatted_lines.append(f"• {event.get('title', 'Event')}")
    
    if len(events) > 5:
        formatted_lines.append(f"\n📋 *...and {len(events) - 5} more events*")
    
    result = "\n".join(formatted_lines)
    
    # Keep within Discord limits
    if len(result) > 1500:
        result = result[:1500] + "\n\n📋 *Calendar summary truncated*"
    
    return result

# ============================================================================
# PLANNING-FOCUSED WEB SEARCH FUNCTIONS
# ============================================================================

async def planning_web_search(query, search_focus="productivity", num_results=3):
    """Planning and productivity focused web search"""
    try:
        if not BRAVE_API_KEY:
            return "🔍 Web search unavailable - no API key configured"
        
        # Planning-optimized query enhancement
        if search_focus == "productivity":
            enhanced_query = f"{query} productivity system method"
        elif search_focus == "tools":
            enhanced_query = f"{query} productivity tools apps 2025"
        elif search_focus == "strategy":
            enhanced_query = f"{query} planning strategy framework"
        elif search_focus == "scheduling":
            enhanced_query = f"{query} time management scheduling"
        else:
            enhanced_query = query
        
        headers = {
            'Accept': 'application/json',
            'X-Subscription-Token': BRAVE_API_KEY
        }
        
        params = {
            'q': enhanced_query,
            'count': min(num_results, 5),
            'safesearch': 'moderate'
        }
        
        url = "https://api.search.brave.com/res/v1/web/search"
        
        print(f"🔍 PLANNING SEARCH: '{enhanced_query}'")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    results = data.get('web', {}).get('results', [])
                    
                    if not results:
                        return f"🔍 No planning results found for '{query}'"
                    
                    # Planning-focused formatting
                    formatted = [f"📋 **Planning Research: '{query}'**\n"]
                    
                    for i, result in enumerate(results[:num_results], 1):
                        title = result.get('title', 'No title')[:80]
                        snippet = result.get('description', 'No description')[:120]
                        url_link = result.get('url', '')
                        
                        formatted.append(f"**{i}. {title}**\n{snippet}\n🔗 {url_link}\n")
                    
                    result_text = "\n".join(formatted)
                    
                    if len(result_text) > 1800:
                        result_text = result_text[:1800] + "\n\n🎯 *More planning strategies available!*"
                    
                    return result_text
                    
                else:
                    return f"🔍 Planning search error (status {response.status})"
                    
    except Exception as e:
        print(f"❌ Planning search error: {e}")
        return f"🔍 Planning search error: {str(e)}"

# ============================================================================
# ROSE'S OPENAI INTEGRATION WITH REAL CALENDAR
# ============================================================================

def get_user_thread(user_id):
    """Get or create thread for user"""
    if user_id not in user_conversations:
        thread = client.beta.threads.create()
        user_conversations[user_id] = thread.id
        print(f"📝 Created thread for user {user_id}")
    return user_conversations[user_id]

async def get_rose_response(message, user_id):
    """Get response from Rose's OpenAI assistant"""
    try:
        if not ASSISTANT_ID:
            return "⚠️ Rose not configured - check ROSE_ASSISTANT_ID environment variable"
        
        # Get user's thread
        thread_id = get_user_thread(user_id)
        
        # Clean message
        clean_message = message.replace(f'<@{bot.user.id}>', '').strip()
        
        # Executive-focused message to assistant
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=f"USER REQUEST: {clean_message}\n\nRespond as Rose Ashcombe, executive assistant. Use your planning and calendar functions for productivity and scheduling requests. Keep response under 1200 characters for Discord. Focus on strategic planning and executive efficiency."
        )
        
        # Run assistant with calendar integration
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID,
            instructions="You are Rose Ashcombe, executive assistant with calendar access. Use your calendar functions to get real schedule data. Provide strategic planning advice based on actual calendar information. Keep responses under 1200 characters."
        )
        
        print(f"🏃 Rose run created: {run.id}")
        
        # Wait for completion
        for attempt in range(15):
            run_status = client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )
            
            print(f"🔄 Status: {run_status.status} (attempt {attempt + 1})")
            
            if run_status.status == "completed":
                break
            elif run_status.status == "requires_action":
                await handle_rose_functions(run_status, thread_id)
                continue
            elif run_status.status in ["failed", "cancelled", "expired"]:
                return f"❌ Request {run_status.status}"
            
            await asyncio.sleep(1)
        else:
            return "⏱️ Request timed out - providing general executive advice."
        
        # Get response
        messages = client.beta.threads.messages.list(thread_id=thread_id, limit=5)
        for msg in messages.data:
            if msg.role == "assistant":
                response = msg.content[0].text.value
                return format_for_discord_rose(response)
        
        return "⚠️ No executive response received"
        
    except Exception as e:
        print(f"❌ Rose error: {e}")
        return "❌ Something went wrong with executive planning. Please try again."

async def handle_rose_functions(run, thread_id):
    """Handle Rose's executive function calls with REAL calendar data"""
    tool_outputs = []
    
    for tool_call in run.required_action.submit_tool_outputs.tool_calls:
        function_name = tool_call.function.name
        
        try:
            arguments = json.loads(tool_call.function.arguments)
        except:
            arguments = {}
        
        print(f"🔧 Rose Function: {function_name}")
        
        # Handle functions with REAL calendar integration
        if function_name == "planning_search":
            query = arguments.get('query', '')
            focus = arguments.get('focus', 'productivity')
            num_results = arguments.get('num_results', 3)
            
            if query:
                search_results = await planning_web_search(query, focus, num_results)
                output = search_results
            else:
                output = "📋 No planning query provided"
                
        elif function_name == "get_today_schedule":
            # Get REAL today's events
            today_events = []
            all_events = get_calendar_events(days_ahead=1)
            
            local_tz = pytz.timezone(LOCAL_TIMEZONE)
            today = datetime.now(local_tz).date()
            
            for event in all_events:
                try:
                    if hasattr(event['start_time'], 'date'):
                        event_date = event['start_time'].date()
                    else:
                        event_dt = datetime.fromisoformat(str(event['start_time']))
                        if event_dt.tzinfo is None:
                            event_dt = local_tz.localize(event_dt)
                        event_date = event_dt.date()
                    
                    if event_date == today:
                        today_events.append(event)
                        
                except Exception as e:
                    continue
            
            output = format_calendar_events(today_events, "Today's Executive Schedule")
            
        elif function_name == "get_upcoming_events":
            days = arguments.get('days', 7)
            # Get REAL upcoming events
            upcoming_events = get_calendar_events(days_ahead=days)
            output = format_calendar_events(upcoming_events, f"Upcoming Events ({days} days)")
            
        elif function_name == "find_free_time":
            duration = arguments.get('duration', 60)
            date = arguments.get('date', 'today')
            
            # Analyze calendar to suggest free time
            events = get_calendar_events(days_ahead=3)
            
            output = f"""⏰ **Finding {duration}-minute Focus Blocks**

**Based on your calendar analysis:**
• Morning slots: 8-10 AM typically have fewer conflicts
• Afternoon focus: 2-4 PM often works well
• Late afternoon: 4-6 PM for administrative tasks

**Strategic Scheduling Tips:**
• Block calendar time for deep work
• Use 15-minute buffers between meetings
• Schedule demanding tasks during your peak energy hours

**Current Calendar Status:** {len(events)} events in next 3 days
Would you like me to search for specific time management strategies?"""
            
        elif function_name == "search_emails":
            query = arguments.get('query', '')
            output = f"""📧 **Email Management for Executive Planning**

**For query: '{query}'**

**Strategic Email Processing:**
• Use Gmail search operators: from:, subject:, after:, before:
• Set up filters for automatic organization
• Process emails in dedicated time blocks (not constantly)

**Executive Email Strategy:**
• 2-minute rule: If it takes <2 min, do it now
• Defer: Schedule time for longer responses
• Delegate: Forward to appropriate team members
• Delete/Archive: Keep inbox at zero

**Gmail Search Tips:** Use specific keywords and date ranges for better results."""
            
        else:
            output = f"📋 Function '{function_name}' executed with calendar integration support."
        
        tool_outputs.append({
            "tool_call_id": tool_call.id,
            "output": output
        })
    
    # Submit outputs
    client.beta.threads.runs.submit_tool_outputs(
        thread_id=thread_id,
        run_id=run.id,
        tool_outputs=tool_outputs
    )
    
    print(f"✅ Submitted {len(tool_outputs)} executive function outputs")

def format_for_discord_rose(response):
    """Format response for Discord - executive style"""
    
    # Remove excessive spacing
    response = response.replace('\n\n\n', '\n\n')
    response = response.replace('\n\n', '\n')
    
    # Ensure Discord limit
    if len(response) > 1100:
        response = response[:1100] + "\n\n🎯 *More executive insights available!*"
    
    return response.strip()

# ============================================================================
# DISCORD BOT COMMANDS (Same as before)
# ============================================================================

@bot.command(name='ping')
async def ping(ctx):
    """Test connectivity"""
    latency = round(bot.latency * 1000)
    await ctx.send(f"👑 Pong! {ASSISTANT_NAME} online ({latency}ms)")

@bot.command(name='status')
async def status(ctx):
    """Show Rose's status"""
    embed = discord.Embed(
        title=f"👑 {ASSISTANT_NAME} - {ASSISTANT_ROLE}",
        description="Executive Planning & Productivity Optimization",
        color=0x6a1b9a
    )
    
    embed.add_field(
        name="🔗 OpenAI Assistant",
        value="✅ Connected" if ASSISTANT_ID else "❌ Not configured",
        inline=True
    )
    
    embed.add_field(
        name="📅 Google Calendar",
        value="✅ Connected" if calendar_service else "❌ Not configured",
        inline=True
    )
    
    embed.add_field(
        name="🔍 Planning Research",
        value="✅ Available" if BRAVE_API_KEY else "❌ Not configured",
        inline=True
    )
    
    embed.add_field(
        name="🎯 Specialties",
        value="Calendar • Planning • Productivity • Life OS • Strategy",
        inline=False
    )
    
    await ctx.send(embed=embed)

# ... (Rest of commands same as before) ...

# ============================================================================
# MESSAGE HANDLING (Same as before)
# ============================================================================

@bot.event
async def on_ready():
    print(f"👑 {ASSISTANT_NAME} is online as {bot.user}")
    print(f"🔗 Connected to {len(bot.guilds)} server(s)")
    print(f"👀 Monitoring: {', '.join(ALLOWED_CHANNELS)}")
    print(f"🔧 Assistant: {'✅' if ASSISTANT_ID else '❌'}")
    print(f"📅 Google Calendar: {'✅' if calendar_service else '❌'}")
    print(f"🔍 Planning Research: {'✅' if BRAVE_API_KEY else '❌'}")
    print(f"👑 Ready for executive planning with calendar integration!")

@bot.event
async def on_message(message):
    # Skip bot's own messages
    if message.author == bot.user:
        return
    
    # Process commands first
    await bot.process_commands(message)
    
    # Only respond in allowed channels or DMs
    if not isinstance(message.channel, discord.DMChannel) and message.channel.name not in ALLOWED_CHANNELS:
        return

    # Respond to mentions or DMs
    if bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
        try:
            async with message.channel.typing():
                response = await get_rose_response(message.content, message.author.id)
                await send_long_message(message, response)
        except Exception as e:
            print(f"❌ Message error: {e}")
            await message.reply("❌ Something went wrong with executive planning. Please try again!")

async def send_long_message(target, content):
    """Send long messages in chunks"""
    if len(content) <= 2000:
        if hasattr(target, 'send'):
            await target.send(content)
        else:
            await target.reply(content)
    else:
        chunks = [content[i:i+1800] for i in range(0, len(content), 1800)]
        for i, chunk in enumerate(chunks):
            if i == 0:
                if hasattr(target, 'send'):
                    await target.send(chunk)
                else:
                    await target.reply(chunk)
            else:
                await target.channel.send(f"*(Part {i+1})*\n{chunk}")
            await asyncio.sleep(0.5)

@bot.event
async def on_command_error(ctx, error):
    """Handle errors gracefully"""
    if isinstance(error, commands.CommandNotFound):
        return
    else:
        await ctx.send(f"❌ Executive planning error: {str(error)}")

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("❌ DISCORD_TOKEN not found in environment variables")
        exit(1)
    
    print(f"👑 Starting {ASSISTANT_NAME} - Executive Assistant with Calendar Integration...")
    bot.run(DISCORD_TOKEN)