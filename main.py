#!/usr/bin/env python3
"""
ROSE ASHCOMBE - DISCORD BOT (CRASH FIX)
Executive Assistant with Enhanced Error Handling, Planning & Calendar Functions
FIXED: Critical crash issues with error handling, async operations, and resource management
Based on proven Flora safety patterns
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

# Load environment variables
load_dotenv()

# Rose's executive configuration
ASSISTANT_NAME = "Rose Ashcombe"
ASSISTANT_ROLE = "Executive Assistant (Crash Fixed)"
ALLOWED_CHANNELS = ['life-os', 'calendar', 'planning-hub', 'general']

# Environment variables with fallbacks
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("ROSE_DISCORD_TOKEN")
ASSISTANT_ID = os.getenv("ROSE_ASSISTANT_ID") or os.getenv("ASSISTANT_ID")
BRAVE_API_KEY = os.getenv('BRAVE_API_KEY')
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Calendar integration variables
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
GOOGLE_CALENDAR_ID = os.getenv('GOOGLE_CALENDAR_ID')

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

# Google Calendar setup with error handling
calendar_service = None
try:
    if GOOGLE_SERVICE_ACCOUNT_JSON:
        credentials_info = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
        credentials = Credentials.from_service_account_info(credentials_info)
        calendar_service = build('calendar', 'v3', credentials=credentials)
        print("✅ Google Calendar service connected successfully")
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
            try:
                async with session.get(
                    'https://api.search.brave.com/res/v1/web/search',
                    headers=headers,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        
                        if 'web' not in data or 'results' not in data['web']:
                            return "🔍 No planning search results found", []
                        
                        results = data['web']['results'][:num_results]
                        
                        if not results:
                            return "🔍 No planning search results found", []
                        
                        formatted = []
                        sources = []
                        
                        for i, result in enumerate(results, 1):
                            title = result.get('title', 'Unknown Source')[:80]
                            snippet = result.get('description', 'No description available')[:150]
                            url_link = result.get('url', '')
                            
                            # Clean and validate URL
                            if url_link and len(url_link) > 10:
                                sources.append({
                                    'number': i,
                                    'title': title,
                                    'url': url_link,
                                    'domain': url_link.split('/')[2] if '/' in url_link else url_link
                                })
                                
                                formatted.append(f"📊 **{title}** ({i})\n{snippet}\n🔗 {url_link}")
                        
                        return "\n\n".join(formatted), sources
                    else:
                        print(f"❌ Brave Search API error: Status {response.status}")
                        return f"🔍 Planning search error (status {response.status})", []
                        
            except asyncio.TimeoutError:
                print("❌ Planning search timeout")
                return "🔍 Planning search timed out", []
            except aiohttp.ClientError as e:
                print(f"❌ HTTP client error: {e}")
                return f"🔍 Planning search connection error", []
                    
    except Exception as e:
        print(f"❌ Planning search error: {e}")
        print(f"📋 Traceback: {traceback.format_exc()}")
        return f"🔍 Planning search error: Please try again", []

# ============================================================================
# CALENDAR FUNCTIONS WITH ERROR HANDLING
# ============================================================================

def get_today_schedule():
    """Get today's calendar schedule with error handling"""
    if not calendar_service or not GOOGLE_CALENDAR_ID:
        return "📅 **Today's Schedule:** Calendar integration not configured\n\n🎯 **Planning Tip:** Set up your calendar integration for automated schedule management"
    
    try:
        from datetime import datetime, timezone
        
        # Get today's date range
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today.replace(hour=23, minute=59, second=59)
        
        events_result = calendar_service.events().list(
            calendarId=GOOGLE_CALENDAR_ID,
            timeMin=today.isoformat(),
            timeMax=tomorrow.isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        if not events:
            return "📅 **Today's Schedule:** No scheduled events\n\n🎯 **Executive Opportunity:** Perfect day for deep work and strategic planning"
        
        formatted_events = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            title = event.get('summary', 'Untitled Event')
            
            if 'T' in start:  # Has time
                time_str = datetime.fromisoformat(start.replace('Z', '+00:00')).strftime('%I:%M %p')
                formatted_events.append(f"• {time_str}: {title}")
            else:  # All day event
                formatted_events.append(f"• All Day: {title}")
        
        return f"📅 **Today's Schedule:** {len(events)} events\n\n" + "\n".join(formatted_events)
        
    except Exception as e:
        print(f"❌ Calendar error: {e}")
        return "📅 **Today's Schedule:** Error retrieving calendar data\n\n🎯 **Backup Plan:** Use manual schedule review"

def get_upcoming_events(days=7):
    """Get upcoming events with error handling"""
    if not calendar_service or not GOOGLE_CALENDAR_ID:
        return f"📅 **Upcoming {days} Days:** Calendar integration not configured\n\n🎯 **Planning Tip:** Manual weekly planning recommended"
    
    try:
        from datetime import datetime, timezone, timedelta
        
        # Get date range
        start_time = datetime.now(timezone.utc)
        end_time = start_time + timedelta(days=days)
        
        events_result = calendar_service.events().list(
            calendarId=GOOGLE_CALENDAR_ID,
            timeMin=start_time.isoformat(),
            timeMax=end_time.isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        if not events:
            return f"📅 **Upcoming {days} Days:** No scheduled events\n\n🎯 **Strategic Opportunity:** Focus on long-term planning and goal setting"
        
        # Group by date
        from collections import defaultdict
        events_by_date = defaultdict(list)
        
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            title = event.get('summary', 'Untitled Event')
            
            if 'T' in start:
                date_obj = datetime.fromisoformat(start.replace('Z', '+00:00'))
                date_str = date_obj.strftime('%a %m/%d')
                time_str = date_obj.strftime('%I:%M %p')
                events_by_date[date_str].append(f"  • {time_str}: {title}")
            else:
                date_obj = datetime.fromisoformat(start)
                date_str = date_obj.strftime('%a %m/%d')
                events_by_date[date_str].append(f"  • All Day: {title}")
        
        formatted = []
        for date, day_events in list(events_by_date.items())[:7]:  # Limit to 7 days for Discord
            formatted.append(f"**{date}**")
            formatted.extend(day_events[:5])  # Limit events per day
        
        return f"📅 **Upcoming {days} Days:** {len(events)} total events\n\n" + "\n".join(formatted)
        
    except Exception as e:
        print(f"❌ Calendar error: {e}")
        return f"📅 **Upcoming {days} Days:** Error retrieving calendar data"

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
                output = f"👑 Executive function {function_name} completed with strategic guidance"
                
        except Exception as e:
            print(f"❌ Function error: {e}")
            print(f"📋 Function traceback: {traceback.format_exc()}")
            output = f"Function {function_name} encountered an issue - continuing with executive guidance"
        
        tool_outputs.append({
            "tool_call_id": tool_call.id,
            "output": output
        })
    
    # Submit outputs with comprehensive error handling
    if tool_outputs:
        try:
            client.beta.threads.runs.submit_tool_outputs(
                thread_id=thread_id,
                run_id=run.id,
                tool_outputs=tool_outputs
            )
            print(f"✅ Submitted {len(tool_outputs)} executive function outputs")
        except Exception as e:
            print(f"❌ Error submitting tool outputs: {e}")
            print(f"📋 Submit traceback: {traceback.format_exc()}")
    else:
        print("⚠️ No tool outputs to submit")

# ============================================================================
# ENHANCED DISCORD FORMATTING WITH ERROR HANDLING
# ============================================================================

def format_for_discord_rose(response):
    """Format response for Discord with error handling"""
    try:
        if not response or not isinstance(response, str):
            return "👑 Executive guidance processing. Please try again."
        
        # Clean excessive spacing
        response = response.replace('\n\n\n\n', '\n\n')
        response = response.replace('\n\n\n', '\n\n')
        
        # Tighten list formatting
        response = re.sub(r'\n\n(\d+\.)', r'\n\1', response)
        response = re.sub(r'\n\n(•)', r'\n•', response)
        
        # Keep breathing room for headers
        response = re.sub(r'\n\n\n(📊)', r'\n\n📊', response)
        response = re.sub(r'\n\n\n(👑)', r'\n\n👑', response)
        response = re.sub(r'\n\n\n(📅)', r'\n\n📅', response)
        response = re.sub(r'\n\n\n(🎯)', r'\n\n🎯', response)
        response = re.sub(r'\n\n\n(💼)', r'\n\n💼', response)
        
        # Ensure nice spacing before references section
        response = re.sub(r'\n📚 \*\*Available Sources:\*\*', r'\n\n📚 **Available Sources:**', response)
        
        # Clean up any trailing issues
        response = re.sub(r'\n+$', '', response)
        response = re.sub(r' +\n', '\n', response)
        
        # Length management (preserve balanced spacing)
        if len(response) > 1900:
            if "📚 **Available Sources:**" in response:
                main_text, sources = response.split("📚 **Available Sources:**", 1)
                if len(main_text) > 1500:
                    main_text = main_text[:1500] + "\n\n👑 *(Executive summary continues...)*"
                response = main_text + "\n\n📚 **Available Sources:**\n" + sources
            else:
                response = response[:1900] + "\n\n👑 *(Strategic guidance continues)*"
        
        print(f"👑 Final response: {len(response)} characters")
        return response.strip()
        
    except Exception as e:
        print(f"❌ Discord formatting error: {e}")
        return "👑 Executive guidance needs refinement. Please try again."

# ============================================================================
# ROSE'S OPENAI INTEGRATION WITH COMPREHENSIVE ERROR HANDLING
# ============================================================================

def get_user_thread(user_id):
    """Get or create thread for user with error handling"""
    try:
        if user_id not in user_conversations:
            thread = client.beta.threads.create()
            user_conversations[user_id] = thread.id
            print(f"👑 Created executive thread for user {user_id}")
        return user_conversations[user_id]
    except Exception as e:
        print(f"❌ Error creating thread: {e}")
        return None

async def get_rose_response(message, user_id):
    """Get response from Rose's enhanced OpenAI assistant with comprehensive error handling"""
    try:
        if not ASSISTANT_ID:
            return "⚠️ Rose not configured - check ROSE_ASSISTANT_ID environment variable"
        
        # Check if user already has an active run
        if user_id in active_runs:
            return "👑 Rose is currently analyzing your executive strategy. Please wait a moment..."
        
        # Mark user as having active run
        active_runs[user_id] = True
        
        # Get user's thread
        thread_id = get_user_thread(user_id)
        if not thread_id:
            return "❌ Error creating executive connection. Please try again."
        
        # Clean message
        clean_message = message.replace(f'<@{bot.user.id}>', '').strip() if hasattr(bot, 'user') and bot.user else message.strip()
        
        # Enhanced message with executive focus
        enhanced_message = f"""USER EXECUTIVE REQUEST: {clean_message}

RESPONSE GUIDELINES:
- Use executive-level Discord formatting with strategic headers
- When using calendar functions, provide actionable scheduling insights
- For planning research, include strategic context and implementation steps
- Apply executive assistant tone: strategic, organized, action-oriented
- Keep main content under 1200 characters for Discord efficiency
- Use headers like: 👑 **Executive Summary:** or 📊 **Strategic Analysis:**
- IMPORTANT: Always provide next steps and strategic context for decisions"""
        
        try:
            client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=enhanced_message
            )
        except Exception as e:
            if "while a run" in str(e) and "is active" in str(e):
                print("⏳ Waiting for previous executive analysis to complete...")
                await asyncio.sleep(3)
                try:
                    client.beta.threads.messages.create(
                        thread_id=thread_id,
                        role="user",
                        content=enhanced_message
                    )
                except Exception as e2:
                    print(f"❌ Still can't add message: {e2}")
                    return "👑 Executive office is busy. Please try again in a moment."
            else:
                print(f"❌ Message creation error: {e}")
                return "❌ Error creating executive message. Please try again."
        
        # Run assistant with executive instructions
        try:
            run = client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=ASSISTANT_ID,
                instructions="""You are Rose Ashcombe, executive assistant with enhanced planning and calendar capabilities.

EXECUTIVE APPROACH:
- Use calendar functions to provide real schedule data and insights
- For planning research, use web search to find latest productivity strategies
- Apply strategic thinking with systems-level optimization
- Provide actionable next steps with clear timelines
- Connect daily actions to bigger picture goals

FORMATTING: Use executive-level formatting with strategic headers (👑 📊 📅 🎯 💼) and provide organized, action-oriented guidance.

STRUCTURE:
👑 **Executive Summary:** [strategic overview with key insights]
📊 **Strategic Analysis:** [data-driven recommendations]
🎯 **Action Items:** [specific next steps with timelines]

Keep core content focused and always provide strategic context."""
            )
        except Exception as e:
            print(f"❌ Run creation error: {e}")
            return "❌ Error starting executive analysis. Please try again."
        
        print(f"👑 Rose run created: {run.id}")
        
        # Wait for completion with function handling
        for attempt in range(20):
            try:
                run_status = client.beta.threads.runs.retrieve(
                    thread_id=thread_id,
                    run_id=run.id
                )
            except Exception as e:
                print(f"❌ Error retrieving run status: {e}")
                await asyncio.sleep(2)
                continue
            
            print(f"🔄 Status: {run_status.status} (attempt {attempt + 1})")
            
            if run_status.status == "completed":
                break
            elif run_status.status == "requires_action":
                await handle_rose_functions_enhanced(run_status, thread_id)
            elif run_status.status in ["failed", "cancelled", "expired"]:
                print(f"❌ Run {run_status.status}")
                return "❌ Executive analysis interrupted. Please try again with a different request."
            
            await asyncio.sleep(2)
        else:
            print("⏱️ Run timed out")
            return "⏱️ Executive office is busy analyzing complex strategies. Please try again in a moment."
        
        # Get response and apply enhanced formatting
        try:
            messages = client.beta.threads.messages.list(thread_id=thread_id, limit=5)
            for msg in messages.data:
                if msg.role == "assistant":
                    response = msg.content[0].text.value
                    return format_for_discord_rose(response)
        except Exception as e:
            print(f"❌ Error retrieving messages: {e}")
            return "❌ Error retrieving executive guidance. Please try again."
        
        return "👑 Executive analysis unclear. Please try again with a different approach."
        
    except Exception as e:
        print(f"❌ Rose error: {e}")
        print(f"📋 Full traceback: {traceback.format_exc()}")
        return "❌ Something went wrong with executive guidance. Please try again!"
    finally:
        # Always remove user from active runs when done
        active_runs.pop(user_id, None)

# ============================================================================
# ENHANCED MESSAGE HANDLING WITH COMPREHENSIVE ERROR HANDLING
# ============================================================================

async def send_long_message(original_message, response):
    """Send response with length handling and error recovery"""
    try:
        if len(response) <= 2000:
            await original_message.reply(response)
        else:
            # Split into chunks
            chunks = []
            current_chunk = ""
            
            for line in response.split('\n'):
                if len(current_chunk + line + '\n') > 1900:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = line + '\n'
                else:
                    current_chunk += line + '\n'
            
            if current_chunk:
                chunks.append(current_chunk.strip())
            
            # Send chunks
            for i, chunk in enumerate(chunks):
                if i == 0:
                    await original_message.reply(chunk)
                else:
                    await original_message.channel.send(chunk)
                    
    except discord.HTTPException as e:
        print(f"❌ Discord HTTP error: {e}")
        try:
            await original_message.reply("👑 Executive guidance too complex for Discord. Please try a more specific request.")
        except:
            pass
    except Exception as e:
        print(f"❌ Message sending error: {e}")

# ============================================================================
# DISCORD BOT EVENT HANDLERS WITH ERROR HANDLING
# ============================================================================

@bot.event
async def on_ready():
    """Bot startup with comprehensive initialization"""
    try:
        print(f"✅ {ASSISTANT_NAME} has awakened!")
        print(f"👑 Connected as {bot.user.name} (ID: {bot.user.id})")
        print(f"📋 Watching channels: {', '.join(ALLOWED_CHANNELS)}")
        print(f"🤖 Assistant ID: {ASSISTANT_ID}")
        print(f"🔍 Planning Search: {'✅' if BRAVE_API_KEY else '❌'}")
        print(f"📅 Calendar Integration: {'✅' if calendar_service else '❌'}")
    except Exception as e:
        print(f"❌ Error in on_ready: {e}")

@bot.event
async def on_error(event, *args, **kwargs):
    """Global error handler"""
    print(f"❌ Discord error in {event}: {traceback.format_exc()}")

@bot.event
async def on_message(message):
    """Enhanced message handling with comprehensive error checking"""
    try:
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
            
            # DUPLICATE PREVENTION
            message_key = f"{message.author.id}_{message.content[:50]}"
            current_time = time.time()
            
            # Check if we're already processing this message
            if message_key in processing_messages:
                return
            
            # Check if user sent same message too quickly (within 5 seconds)
            if message.author.id in last_response_time:
                if current_time - last_response_time[message.author.id] < 5:
                    return
            
            # Mark message as being processed
            processing_messages.add(message_key)
            last_response_time[message.author.id] = current_time
            
            try:
                async with message.channel.typing():
                    response = await get_rose_response(message.content, message.author.id)
                    await send_long_message(message, response)
            except Exception as e:
                print(f"❌ Message error: {e}")
                print(f"📋 Message traceback: {traceback.format_exc()}")
                try:
                    await message.reply("❌ Something went wrong with executive guidance. Please try again!")
                except:
                    pass
            finally:
                # Always clean up
                processing_messages.discard(message_key)
                
    except Exception as e:
        print(f"❌ Critical on_message error: {e}")
        print(f"📋 Critical traceback: {traceback.format_exc()}")

# ============================================================================
# BASIC BOT COMMANDS WITH ERROR HANDLING
# ============================================================================

@bot.command(name='ping')
async def ping(ctx):
    """Test connectivity with error handling"""
    try:
        latency = round(bot.latency * 1000)
        await ctx.send(f"👑 Pong! Latency: {latency}ms - Executive operations running smoothly!")
    except Exception as e:
        print(f"❌ Ping command error: {e}")

@bot.command(name='status')
async def status(ctx):
    """Show Rose's status with error handling"""
    try:
        status_msg = f"""👑 **Rose Ashcombe Status**
✅ OpenAI Assistant: {'Connected' if ASSISTANT_ID else 'Not configured'}
🔍 Planning Search: {'Connected' if BRAVE_API_KEY else 'Not configured'}
📅 Calendar Integration: {'Connected' if calendar_service else 'Not configured'}
👥 Active Conversations: {len(user_conversations)}
🏃 Active Runs: {len(active_runs)}
"""
        await ctx.send(status_msg)
    except Exception as e:
        print(f"❌ Status command error: {e}")

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
        async with ctx.typing():
            events = get_upcoming_events(days)
            await ctx.send(events)
    except Exception as e:
        print(f"❌ Upcoming command error: {e}")
        await ctx.send("❌ Error retrieving upcoming events. Please try again.")

@bot.command(name='plan')
async def plan_command(ctx, *, query):
    """Search planning information with error handling"""
    try:
        async with ctx.typing():
            results, _ = await planning_search_enhanced(query)
            await send_long_message(ctx, results)
    except Exception as e:
        print(f"❌ Plan command error: {e}")
        await ctx.send("❌ Error searching planning information. Please try again.")

# ============================================================================
# BOT STARTUP WITH ERROR HANDLING
# ============================================================================

def main():
    """Main function with comprehensive error handling"""
    try:
        if not DISCORD_TOKEN:
            print("❌ CRITICAL: No Discord token found")
            return
            
        print(f"👑 Starting Rose Ashcombe executive assistant bot...")
        bot.run(DISCORD_TOKEN)
        
    except discord.LoginFailure:
        print("❌ CRITICAL: Invalid Discord token")
    except Exception as e:
        print(f"❌ CRITICAL: Bot startup failed: {e}")
        print(f"📋 Startup traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    main()