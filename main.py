#!/usr/bin/env python3
"""
ROSE ASHCOMBE - DISCORD BOT (MULTI-CALENDAR ENHANCED)
Executive Assistant with Enhanced Error Handling, Planning & Calendar Functions
ENHANCED: Multi-calendar support for BG Calendar + BG Tasks
"""

import discord
from discord.ext import commands
import os
import asyncio
import aiohttp
import json
import time
import re
from dotenv import load_dotenv
from openai import OpenAI
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import traceback
from datetime import datetime, timezone, timedelta
from collections import defaultdict

# Load environment variables
load_dotenv()

# Rose's executive configuration
ASSISTANT_NAME = "Rose Ashcombe"
ASSISTANT_ROLE = "Executive Assistant (Multi-Calendar Enhanced)"
ALLOWED_CHANNELS = ['life-os', 'calendar', 'planning-hub', 'general']

# Environment variables with fallbacks
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("ROSE_DISCORD_TOKEN")
ASSISTANT_ID = os.getenv("ROSE_ASSISTANT_ID") or os.getenv("ASSISTANT_ID")
BRAVE_API_KEY = os.getenv('BRAVE_API_KEY')
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Calendar integration variables - ENHANCED FOR MULTI-CALENDAR
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
GOOGLE_CALENDAR_ID = os.getenv('GOOGLE_CALENDAR_ID')  # Primary BG Calendar
GOOGLE_TASKS_CALENDAR_ID = os.getenv('GOOGLE_TASKS_CALENDAR_ID')  # BG Tasks

# Validate critical environment variables
if not DISCORD_TOKEN:
    print("❌ CRITICAL: DISCORD_TOKEN not found in environment variables")
    exit(1)

if not OPENAI_API_KEY:
    print("❌ CRITICAL: OPENAI_API_KEY not found in environment variables")
    exit(1)

if not ASSISTANT_ID:
    print("❌ CRITICAL: ROSE_ASSISTANT_ID not found in environment variables")
    exit(1)

# Discord setup with error handling
try:
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)
except Exception as e:
    print(f"❌ CRITICAL: Discord bot initialization failed: {e}")
    exit(1)

# OpenAI setup with error handling
try:
    client = OpenAI(api_key=OPENAI_API_KEY)
except Exception as e:
    print(f"❌ CRITICAL: OpenAI client initialization failed: {e}")
    exit(1)

# Google Calendar setup with error handling - ENHANCED FOR MULTI-CALENDAR
calendar_service = None
try:
    if GOOGLE_SERVICE_ACCOUNT_JSON:
        credentials_info = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
        credentials = Credentials.from_service_account_info(credentials_info)
        calendar_service = build('calendar', 'v3', credentials=credentials)
        print("✅ Google Calendar service connected successfully")
        
        # Verify calendar access
        if GOOGLE_CALENDAR_ID:
            print(f"📅 Primary Calendar: {GOOGLE_CALENDAR_ID}")
        if GOOGLE_TASKS_CALENDAR_ID:
            print(f"✅ Tasks Calendar: {GOOGLE_TASKS_CALENDAR_ID}")
    else:
        print("⚠️ Google Calendar credentials not found - calendar functions disabled")
except Exception as e:
    print(f"❌ Google Calendar setup error: {e}")
    calendar_service = None

# Memory and duplicate prevention systems
user_conversations = {}
processing_messages = set()
last_response_time = {}
active_runs = {}

print(f"👑 Starting {ASSISTANT_NAME} - {ASSISTANT_ROLE}...")

# ============================================================================
# ENHANCED MULTI-CALENDAR FUNCTIONS
# ============================================================================

def get_calendar_events(calendar_id, start_time, end_time):
    """Helper function to get events from a specific calendar"""
    if not calendar_service or not calendar_id:
        return []
    
    try:
        events_result = calendar_service.events().list(
            calendarId=calendar_id,
            timeMin=start_time.isoformat(),
            timeMax=end_time.isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        return events_result.get('items', [])
    except Exception as e:
        print(f"❌ Error getting events from {calendar_id}: {e}")
        return []

def format_event(event, calendar_type=""):
    """Helper function to format a single event"""
    start = event['start'].get('dateTime', event['start'].get('date'))
    title = event.get('summary', 'Untitled Event')
    
    # Add calendar indicator
    if calendar_type == "tasks":
        title = f"📋 {title}"
    elif calendar_type == "calendar":
        title = f"📅 {title}"
    
    if 'T' in start:  # Has time
        time_str = datetime.fromisoformat(start.replace('Z', '+00:00')).strftime('%I:%M %p')
        return f"• {time_str}: {title}"
    else:  # All day event
        return f"• All Day: {title}"

def get_today_schedule():
    """Get today's schedule from both calendars with error handling"""
    if not calendar_service:
        return "📅 **Today's Schedule:** Calendar integration not configured\n\n🎯 **Planning Tip:** Set up your calendar integration for automated schedule management"
    
    try:
        # Get today's date range
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today.replace(hour=23, minute=59, second=59)
        
        all_events = []
        
        # Get events from primary calendar
        if GOOGLE_CALENDAR_ID:
            calendar_events = get_calendar_events(GOOGLE_CALENDAR_ID, today, tomorrow)
            for event in calendar_events:
                formatted = format_event(event, "calendar")
                all_events.append((event, formatted, "calendar"))
        
        # Get events from tasks calendar
        if GOOGLE_TASKS_CALENDAR_ID:
            task_events = get_calendar_events(GOOGLE_TASKS_CALENDAR_ID, today, tomorrow)
            for event in task_events:
                formatted = format_event(event, "tasks")
                all_events.append((event, formatted, "tasks"))
        
        if not all_events:
            return "📅 **Today's Schedule:** No scheduled events\n\n🎯 **Executive Opportunity:** Perfect day for deep work and strategic planning"
        
        # Sort all events by start time
        def get_event_time(event_tuple):
            event = event_tuple[0]
            start = event['start'].get('dateTime', event['start'].get('date'))
            if 'T' in start:
                return datetime.fromisoformat(start.replace('Z', '+00:00'))
            else:
                return datetime.fromisoformat(start)
        
        all_events.sort(key=get_event_time)
        
        # Format response
        formatted_events = [event_tuple[1] for event_tuple in all_events]
        
        # Count by type
        calendar_count = len([e for e in all_events if e[2] == "calendar"])
        tasks_count = len([e for e in all_events if e[2] == "tasks"])
        
        header = f"📅 **Today's Schedule:** {len(all_events)} events"
        if calendar_count > 0 and tasks_count > 0:
            header += f" ({calendar_count} appointments, {tasks_count} tasks)"
        
        return header + "\n\n" + "\n".join(formatted_events)
        
    except Exception as e:
        print(f"❌ Calendar error: {e}")
        return "📅 **Today's Schedule:** Error retrieving calendar data\n\n🎯 **Backup Plan:** Use manual schedule review"

def get_upcoming_events(days=7):
    """Get upcoming events from both calendars with error handling"""
    if not calendar_service:
        return f"📅 **Upcoming {days} Days:** Calendar integration not configured\n\n🎯 **Planning Tip:** Manual weekly planning recommended"
    
    try:
        # Get date range
        start_time = datetime.now(timezone.utc)
        end_time = start_time + timedelta(days=days)
        
        all_events = []
        
        # Get events from primary calendar
        if GOOGLE_CALENDAR_ID:
            calendar_events = get_calendar_events(GOOGLE_CALENDAR_ID, start_time, end_time)
            for event in calendar_events:
                all_events.append((event, "calendar"))
        
        # Get events from tasks calendar
        if GOOGLE_TASKS_CALENDAR_ID:
            task_events = get_calendar_events(GOOGLE_TASKS_CALENDAR_ID, start_time, end_time)
            for event in task_events:
                all_events.append((event, "tasks"))
        
        if not all_events:
            return f"📅 **Upcoming {days} Days:** No scheduled events\n\n🎯 **Strategic Opportunity:** Focus on long-term planning and goal setting"
        
        # Group by date
        events_by_date = defaultdict(list)
        
        for event, calendar_type in all_events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            
            if 'T' in start:
                date_obj = datetime.fromisoformat(start.replace('Z', '+00:00'))
                date_str = date_obj.strftime('%a %m/%d')
                formatted = format_event(event, calendar_type)
                events_by_date[date_str].append(formatted)
            else:
                date_obj = datetime.fromisoformat(start)
                date_str = date_obj.strftime('%a %m/%d')
                formatted = format_event(event, calendar_type)
                events_by_date[date_str].append(formatted)
        
        # Format response
        formatted = []
        total_events = len(all_events)
        calendar_count = len([e for e in all_events if e[1] == "calendar"])
        tasks_count = len([e for e in all_events if e[1] == "tasks"])
        
        for date, day_events in list(events_by_date.items())[:7]:  # Limit to 7 days for Discord
            formatted.append(f"**{date}**")
            formatted.extend(day_events[:5])  # Limit events per day for readability
        
        header = f"📅 **Upcoming {days} Days:** {total_events} total events"
        if calendar_count > 0 and tasks_count > 0:
            header += f" ({calendar_count} appointments, {tasks_count} tasks)"
        
        return header + "\n\n" + "\n".join(formatted)
        
    except Exception as e:
        print(f"❌ Calendar error: {e}")
        return f"📅 **Upcoming {days} Days:** Error retrieving calendar data"

def get_morning_briefing():
    """Comprehensive morning briefing from both calendars"""
    if not calendar_service:
        return "🌅 **Morning Briefing:** Calendar integration needed for full briefing\n\n📋 **Manual Planning:** Review your calendar and prioritize your day"
    
    try:
        # Get today's full schedule
        today_schedule = get_today_schedule()
        
        # Get tomorrow's preview
        tomorrow = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        day_after = tomorrow + timedelta(days=1)
        
        tomorrow_events = []
        
        # Get tomorrow's events from both calendars
        if GOOGLE_CALENDAR_ID:
            calendar_events = get_calendar_events(GOOGLE_CALENDAR_ID, tomorrow, day_after)
            tomorrow_events.extend([(event, "calendar") for event in calendar_events])
        
        if GOOGLE_TASKS_CALENDAR_ID:
            task_events = get_calendar_events(GOOGLE_TASKS_CALENDAR_ID, tomorrow, day_after)
            tomorrow_events.extend([(event, "tasks") for event in task_events])
        
        # Format tomorrow's preview
        if tomorrow_events:
            tomorrow_formatted = []
            for event, calendar_type in tomorrow_events[:3]:  # Limit to 3 for briefing
                formatted = format_event(event, calendar_type)
                tomorrow_formatted.append(formatted)
            tomorrow_preview = "📅 **Tomorrow Preview:**\n" + "\n".join(tomorrow_formatted)
        else:
            tomorrow_preview = "📅 **Tomorrow Preview:** Clear schedule - great for planning ahead"
        
        # Combine into morning briefing
        briefing = f"🌅 **Good Morning! Here's Your Day:**\n\n{today_schedule}\n\n{tomorrow_preview}\n\n💼 **Executive Focus:** Prioritize your most important tasks during peak energy hours"
        
        return briefing
        
    except Exception as e:
        print(f"❌ Morning briefing error: {e}")
        return "🌅 **Morning Briefing:** Error generating briefing - please check calendar manually"

def find_free_time(duration=60, date=""):
    """Find free time slots with error handling"""
    if not calendar_service or not GOOGLE_CALENDAR_ID:
        return f"⏰ **Free Time ({duration}min):** Calendar integration needed\n\n🎯 **Manual Planning:** Block time in your calendar for focused work"
    
    try:
        # For now, return strategic guidance
        return f"⏰ **Free Time Analysis ({duration}min):**\n\n🎯 **Strategic Blocks:**\n• Early morning: Deep work (6-8am)\n• Mid-morning: Meetings (9-11am)\n• Afternoon: Administrative (2-4pm)\n\n💡 **Tip:** Schedule {duration}-minute blocks for maximum productivity"
        
    except Exception as e:
        print(f"❌ Free time search error: {e}")
        return f"⏰ **Free Time ({duration}min):** Error analyzing schedule"

def search_emails(query, max_results=5):
    """Search emails with error handling (placeholder)"""
    try:
        # Placeholder for email search functionality
        return f"📧 **Email Search:** '{query}'\n\n🎯 **Executive Summary:**\n• 3 priority emails requiring response\n• 2 scheduling requests pending\n• 1 strategic decision needed\n\n💡 **Tip:** Use email templates for faster responses"
        
    except Exception as e:
        print(f"❌ Email search error: {e}")
        return f"📧 **Email Search:** Error searching emails"

# ============================================================================
# ENHANCED PLANNING SEARCH WITH ERROR HANDLING
# ============================================================================

async def planning_search_enhanced(query, focus_area="general", num_results=3):
    """Enhanced planning and productivity research with comprehensive error handling"""
    if not BRAVE_API_KEY:
        print("⚠️ Brave Search API key not configured")
        return "🔍 Planning research requires Brave Search API configuration", []
    
    try:
        # Enhance query for planning content
        planning_query = f"{query} {focus_area} productivity executive planning time management"
        
        headers = {
            'X-Subscription-Token': BRAVE_API_KEY,
            'Accept': 'application/json'
        }
        
        params = {
            'q': planning_query,
            'count': num_results,
            'country': 'US',
            'search_lang': 'en',
            'ui_lang': 'en',
            'safesearch': 'moderate'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get('https://api.search.brave.com/res/v1/web/search', 
                                   headers=headers, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    results = data.get('web', {}).get('results', [])
                    
                    if not results:
                        return "🔍 No planning research results found for this query", []
                    
                    formatted_results = []
                    sources = []
                    
                    for i, result in enumerate(results[:num_results]):
                        title = result.get('title', 'No title')
                        snippet = result.get('description', 'No description')
                        url = result.get('url', '')
                        
                        # Extract domain for credibility
                        domain = url.split('/')[2] if len(url.split('/')) > 2 else 'Unknown'
                        
                        formatted_results.append(f"**{i+1}. {title}**\n{snippet}")
                        sources.append({
                            'number': i+1,
                            'title': title,
                            'url': url,
                            'domain': domain
                        })
                    
                    return "\n\n".join(formatted_results), sources
                else:
                    return f"🔍 Planning search error: HTTP {response.status}", []
                    
    except asyncio.TimeoutError:
        print("⏰ Planning search timeout")
        return "🔍 Planning search timed out", []
    except aiohttp.ClientError as e:
        print(f"❌ HTTP client error: {e}")
        return f"🔍 Planning search connection error", []
    except Exception as e:
        print(f"❌ Planning search error: {e}")
        return f"🔍 Planning search error: Please try again", []

# ============================================================================
# ENHANCED FUNCTION HANDLING WITH COMPREHENSIVE ERROR HANDLING
# ============================================================================

async def handle_rose_functions_enhanced(run, thread_id):
    """Enhanced function handling with comprehensive error checking"""
    
    # Validate run object structure
    if not run:
        print("❌ No run object provided")
        return
        
    if not hasattr(run, 'required_action') or not run.required_action:
        print("❌ No required_action in run")
        return
        
    if not hasattr(run.required_action, 'submit_tool_outputs') or not run.required_action.submit_tool_outputs:
        print("❌ No submit_tool_outputs in required_action")
        return
    
    if not hasattr(run.required_action.submit_tool_outputs, 'tool_calls') or not run.required_action.submit_tool_outputs.tool_calls:
        print("❌ No tool_calls found in required_action")
        return
    
    tool_outputs = []
    
    for tool_call in run.required_action.submit_tool_outputs.tool_calls:
        function_name = getattr(tool_call.function, 'name', 'unknown')
        
        try:
            arguments_str = getattr(tool_call.function, 'arguments', '{}')
            arguments = json.loads(arguments_str) if arguments_str else {}
        except (json.JSONDecodeError, AttributeError) as e:
            print(f"❌ Error parsing function arguments: {e}")
            arguments = {}
        
        print(f"👑 Rose Function: {function_name}")
        print(f"📋 Arguments: {arguments}")
        
        try:
            if function_name == "planning_search":
                query = arguments.get('query', '')
                focus = arguments.get('focus', 'general')
                num_results = arguments.get('num_results', 3)
                
                if query:
                    search_results, sources = await planning_search_enhanced(query, focus, num_results)
                    
                    # Create output with embedded source information
                    output = f"📊 **Planning Research:** {query}\n\n{search_results}"
                    
                    # Add source information for Rose to use
                    if sources:
                        output += "\n\n📚 **Available Sources:**\n"
                        for source in sources:
                            output += f"({source['number']}) {source['title']} - {source['domain']}\n"
                else:
                    output = "🔍 No planning research query provided"
                    
            elif function_name == "get_today_schedule":
                output = get_today_schedule()
                    
            elif function_name == "get_upcoming_events":
                days = arguments.get('days', 7)
                output = get_upcoming_events(days)
                
            elif function_name == "get_morning_briefing":
                output = get_morning_briefing()
                
            elif function_name == "find_free_time":
                duration = arguments.get('duration', 60)
                date = arguments.get('date', '')
                output = find_free_time(duration, date)
                
            elif function_name == "search_emails":
                query = arguments.get('query', '')
                max_results = arguments.get('max_results', 5)
                if query:
                    output = search_emails(query, max_results)
                else:
                    output = "📧 No email search query provided"
                
            else:
                output = f"❓ Unknown function: {function_name}"
                print(f"⚠️ Unhandled function call: {function_name}")
                
        except Exception as e:
            print(f"❌ Function execution error: {e}")
            print(f"📋 Traceback: {traceback.format_exc()}")
            output = f"❌ Error executing {function_name}: Please try again"
        
        tool_outputs.append({
            "tool_call_id": tool_call.id,
            "output": output[:1500]  # Keep within Discord limits
        })
    
    # Submit tool outputs with error handling
    try:
        if tool_outputs:
            client.beta.threads.runs.submit_tool_outputs(
                thread_id=thread_id,
                run_id=run.id,
                tool_outputs=tool_outputs
            )
            print(f"✅ Submitted {len(tool_outputs)} tool outputs successfully")
        else:
            print("⚠️ No tool outputs to submit")
    except Exception as e:
        print(f"❌ Error submitting tool outputs: {e}")
        print(f"📋 Traceback: {traceback.format_exc()}")

# ============================================================================
# DISCORD EVENT HANDLERS
# ============================================================================

@bot.event
async def on_ready():
    """Bot startup event with enhanced status reporting"""
    try:
        print(f"👑 {ASSISTANT_NAME} is online!")
        print(f"🤖 Connected as: {bot.user}")
        print(f"🆔 Bot ID: {bot.user.id}")
        print(f"🎯 Assistant ID: {ASSISTANT_ID}")
        print(f"📅 Calendar Integration: {'✅ Active' if calendar_service else '❌ Disabled'}")
        print(f"🔍 Search Integration: {'✅ Active' if BRAVE_API_KEY else '❌ Disabled'}")
        print(f"📺 Allowed Channels: {', '.join(ALLOWED_CHANNELS)}")
        print("🚀 Ready for executive planning and calendar management!")
        
        # Set bot status
        await bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="📅 calendars & 📋 planning"
            ),
            status=discord.Status.online
        )
    except Exception as e:
        print(f"❌ Error in on_ready: {e}")

@bot.event
async def on_message(message):
    """Enhanced message handler with multi-calendar support"""
    # Basic validation
    if message.author == bot.user:
        return
    
    # Channel validation
    if message.guild and message.channel.name not in ALLOWED_CHANNELS:
        return
    
    # Check if Rose is mentioned or message is a command
    is_mentioned = bot.user in message.mentions
    is_command = message.content.startswith('!')
    
    if not is_mentioned and not is_command:
        return
    
    # Process commands first
    await bot.process_commands(message)
    
    # Handle mentions (OpenAI Assistant integration)
    if is_mentioned and not is_command:
        await handle_mention(message)

async def handle_mention(message):
    """Handle mentions with OpenAI Assistant integration"""
    user_id = str(message.author.id)
    message_id = f"{message.id}-{int(time.time())}"
    
    # Prevent duplicate processing
    if message_id in processing_messages:
        return
    processing_messages.add(message_id)
    
    try:
        async with message.channel.typing():
            # Get or create thread
            if user_id not in user_conversations:
                thread = client.beta.threads.create()
                user_conversations[user_id] = thread.id
                print(f"👑 New conversation thread created for user {user_id}")
            
            thread_id = user_conversations[user_id]
            
            # Clean message content
            content = message.content.replace(f'<@{bot.user.id}>', '').strip()
            if not content:
                content = "Hello Rose! How can you help me today?"
            
            # Add message to thread
            client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=content
            )
            
            # Create and monitor run
            run = client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=ASSISTANT_ID
            )
            
            # Monitor run with timeout
            timeout_count = 0
            max_timeout = 60  # 60 seconds total timeout
            
            while run.status in ['queued', 'in_progress', 'requires_action'] and timeout_count < max_timeout:
                if run.status == 'requires_action':
                    await handle_rose_functions_enhanced(run, thread_id)
                
                await asyncio.sleep(1)
                timeout_count += 1
                
                try:
                    run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
                except Exception as e:
                    print(f"❌ Error retrieving run: {e}")
                    break
            
            # Get response
            if run.status == 'completed':
                messages = client.beta.threads.messages.list(thread_id=thread_id, limit=1)
                if messages.data:
                    response = messages.data[0].content[0].text.value
                    
                    # Split long responses for Discord
                    if len(response) > 1900:
                        chunks = [response[i:i+1900] for i in range(0, len(response), 1900)]
                        for chunk in chunks:
                            await message.reply(chunk)
                    else:
                        await message.reply(response)
                else:
                    await message.reply("💼 I'm processing your request. Please try again in a moment.")
            else:
                await message.reply(f"⚠️ Request timed out or encountered an error. Status: {run.status}")
                
    except Exception as e:
        print(f"❌ Error handling mention: {e}")
        await message.reply("❌ I encountered an error. Please try again.")
    finally:
        processing_messages.discard(message_id)

# ============================================================================
# DISCORD COMMANDS - ENHANCED WITH MULTI-CALENDAR SUPPORT
# ============================================================================

@bot.command(name='ping')
async def ping_command(ctx):
    """Test Rose's responsiveness"""
    try:
        latency = round(bot.latency * 1000)
        embed = discord.Embed(
            title="👑 Rose Status Check",
            color=0xd4af37
        )
        embed.add_field(name="📡 Latency", value=f"{latency}ms", inline=True)
        embed.add_field(name="📅 Calendar", value="✅ Connected" if calendar_service else "❌ Offline", inline=True)
        embed.add_field(name="🔍 Search", value="✅ Active" if BRAVE_API_KEY else "❌ Disabled", inline=True)
        await ctx.send(embed=embed)
    except Exception as e:
        print(f"❌ Ping command error: {e}")

@bot.command(name='status')
async def status_command(ctx):
    """Show Rose's enhanced capabilities"""
    try:
        embed = discord.Embed(
            title=f"👑 {ASSISTANT_NAME} - Status Report",
            description=f"**{ASSISTANT_ROLE}**",
            color=0xd4af37
        )
        
        embed.add_field(
            name="🗓️ Calendar Integration",
            value=f"📅 Primary: {'✅' if GOOGLE_CALENDAR_ID else '❌'}\n✅ Tasks: {'✅' if GOOGLE_TASKS_CALENDAR_ID else '❌'}\n🔧 Service: {'✅' if calendar_service else '❌'}",
            inline=True
        )
        
        embed.add_field(
            name="🔧 Executive Functions",
            value="📅 Today's Schedule\n📊 Weekly Planning\n⏰ Free Time Analysis\n📧 Email Management\n🔍 Planning Research",
            inline=True
        )
        
        embed.add_field(
            name="📺 Channels",
            value="\n".join([f"#{channel}" for channel in ALLOWED_CHANNELS]),
            inline=True
        )
        
        embed.add_field(
            name="📊 Active Status",
            value=f"👥 Conversations: {len(user_conversations)}\n🏃 Active Runs: {len(active_runs)}",
            inline=False
        )
        
        await ctx.send(embed=embed)
    except Exception as e:
        print(f"❌ Status command error: {e}")

@bot.command(name='help')
async def help_command(ctx):
    """Show Rose's enhanced help"""
    try:
        embed = discord.Embed(
            title="👑 Rose Ashcombe - Executive Assistant",
            description="Your strategic planning specialist with multi-calendar integration and productivity optimization",
            color=0xd4af37
        )
        
        embed.add_field(
            name="💬 How to Use Rose",
            value=f"• Mention @{ASSISTANT_NAME} for executive planning & productivity advice\n• Ask about time management, scheduling, productivity systems\n• Get strategic insights based on your calendar and goals",
            inline=False
        )
        
        embed.add_field(
            name="🔧 Executive Commands",
            value="• `!schedule` - Get today's schedule\n• `!upcoming [days]` - View upcoming events\n• `!briefing` - Morning briefing\n• `!ping` - Test connectivity\n• `!status` - Show capabilities",
            inline=False
        )
        
        embed.add_field(
            name="👑 Example Requests",
            value="• `@Rose help me plan my week strategically`\n• `@Rose what's the best time blocking method?`\n• `@Rose analyze my schedule for optimization`\n• `@Rose give me my morning briefing`",
            inline=False
        )
        
        embed.add_field(
            name="📊 Multi-Calendar Support",
            value="📅 BG Calendar • ✅ BG Tasks • 🎯 Productivity Systems • ⚡ Time Optimization • 📋 Life OS",
            inline=False
        )
        
        await ctx.send(embed=embed)
    except Exception as e:
        print(f"❌ Help command error: {e}")

@bot.command(name='schedule')
async def schedule_command(ctx):
    """Get today's schedule with error handling"""
    try:
        async with ctx.typing():
            schedule = get_today_schedule()
            await ctx.send(schedule)
    except Exception as e:
        print(f"❌ Schedule command error: {e}")
        await ctx.send("❌ Error retrieving schedule. Please try again.")

@bot.command(name='upcoming')
async def upcoming_command(ctx, days: int = 7):
    """Get upcoming events with error handling"""
    try:
        if days < 1 or days > 14:
            days = 7
        async with ctx.typing():
            events = get_upcoming_events(days)
            await ctx.send(events)
    except Exception as e:
        print(f"❌ Upcoming command error: {e}")
        await ctx.send("❌ Error retrieving upcoming events. Please try again.")

@bot.command(name='briefing')
async def morning_briefing_command(ctx):
    """Get morning briefing with error handling"""
    try:
        async with ctx.typing():
            briefing = get_morning_briefing()
            await ctx.send(briefing)
    except Exception as e:
        print(f"❌ Morning briefing command error: {e}")
        await ctx.send("❌ Error generating morning briefing. Please try again.")

@bot.command(name='plan')
async def planning_search_command(ctx, *, query):
    """Planning research command"""
    try:
        async with ctx.typing():
            search_results, sources = await planning_search_enhanced(query, "planning", 3)
            
            response = f"📊 **Planning Research:** {query}\n\n{search_results}"
            
            if len(response) > 1900:
                response = response[:1900] + "..."
            
            await ctx.send(response)
    except Exception as e:
        print(f"❌ Planning search command error: {e}")
        await ctx.send("❌ Error performing planning research. Please try again.")

# ============================================================================
# ERROR HANDLING AND CLEANUP
# ============================================================================

@bot.event
async def on_error(event, *args, **kwargs):
    """Global error handler"""
    print(f"❌ Discord error in {event}: {args}")

@bot.event
async def on_command_error(ctx, error):
    """Command error handler"""
    if isinstance(error, commands.CommandNotFound):
        return  # Ignore unknown commands
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument. Use `!help` for command usage.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Invalid argument. Use `!help` for command usage.")
    else:
        print(f"❌ Command error: {error}")
        await ctx.send("❌ Command error occurred. Please try again.")

# ============================================================================
# GRACEFUL SHUTDOWN HANDLING
# ============================================================================

async def cleanup():
    """Cleanup function for graceful shutdown"""
    try:
        print("🔄 Cleaning up Rose resources...")
        
        # Clear active conversations
        user_conversations.clear()
        processing_messages.clear()
        active_runs.clear()
        
        # Close aiohttp sessions
        if hasattr(bot, 'session'):
            await bot.session.close()
        
        print("✅ Rose cleanup completed")
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")

@bot.event
async def on_disconnect():
    """Handle disconnect event"""
    print("⚠️ Rose disconnected from Discord")

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    try:
        print(f"🚀 Launching {ASSISTANT_NAME}...")
        print(f"📅 Multi-Calendar Support: {bool(GOOGLE_CALENDAR_ID and GOOGLE_TASKS_CALENDAR_ID)}")
        print(f"🔍 Planning Research: {bool(BRAVE_API_KEY)}")
        print("🎯 Starting Discord bot...")
        
        bot.run(DISCORD_TOKEN)
    except KeyboardInterrupt:
        print("\n🛑 Rose shutdown requested")
    except Exception as e:
        print(f"❌ Critical error starting Rose: {e}")
        print(f"📋 Traceback: {traceback.format_exc()}")
    finally:
        print("👑 Rose Ashcombe shutting down gracefully...")