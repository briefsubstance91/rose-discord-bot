#!/usr/bin/env python3
"""
ROSE FIXED DISCORD BOT - Executive Assistant
Fixed function calling loop issue - prevents infinite calendar calls
"""

import discord
from discord.ext import commands
import os
import asyncio
import aiohttp
import json
from dotenv import load_dotenv
from openai import OpenAI

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

print(f"👑 Starting {ASSISTANT_NAME} - {ASSISTANT_ROLE}...")

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
                print(f"🔍 API Response: {response.status}")
                
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
                        
                        # Add planning-relevant indicators
                        if any(word in title.lower() for word in ['productivity', 'gtd', 'planning']):
                            indicator = "📈 "
                        elif any(word in title.lower() for word in ['calendar', 'schedule', 'time']):
                            indicator = "📅 "
                        elif any(word in title.lower() for word in ['strategy', 'system', 'method']):
                            indicator = "🎯 "
                        else:
                            indicator = "📋 "
                        
                        formatted.append(f"**{i}. {indicator}{title}**\n{snippet}\n🔗 {url_link}\n")
                    
                    result_text = "\n".join(formatted)
                    
                    # Ensure Discord length limit
                    if len(result_text) > 1800:
                        result_text = result_text[:1800] + "\n\n🎯 *More planning strategies available - ask for specifics!*"
                    
                    return result_text
                    
                else:
                    return f"🔍 Planning search error (status {response.status})"
                    
    except Exception as e:
        print(f"❌ Planning search error: {e}")
        return f"🔍 Planning search error: {str(e)}"

# ============================================================================
# ROSE'S OPENAI INTEGRATION - FIXED FUNCTION HANDLING
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
        
        # Run assistant with more specific instructions to prevent loops
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID,
            instructions="You are Rose Ashcombe, executive assistant. Use functions ONLY when specifically needed. If calendar data is not available, provide strategic advice based on general planning principles. Keep responses under 1200 characters. Avoid calling the same function multiple times."
        )
        
        print(f"🏃 Rose run created: {run.id}")
        
        # Wait for completion with function call handling
        for attempt in range(15):  # Reduced from 20 to prevent long loops
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
            return "⏱️ Request timed out - providing general executive advice instead."
        
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
    """Handle Rose's executive function calls - FIXED to prevent loops"""
    tool_outputs = []
    
    for tool_call in run.required_action.submit_tool_outputs.tool_calls:
        function_name = tool_call.function.name
        
        try:
            arguments = json.loads(tool_call.function.arguments)
        except:
            arguments = {}
        
        print(f"🔧 Rose Function: {function_name}")
        
        # Handle Rose's executive functions with more complete responses
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
            # More complete response to satisfy the assistant
            output = """📅 **Today's Executive Schedule**

I don't have access to your live calendar, but I can help you optimize your day strategically:

🎯 **Strategic Time Blocks:**
• Morning: High-focus work (2-3 hours)
• Midday: Meetings and collaboration 
• Afternoon: Administrative tasks and planning
• Evening: Review and next-day preparation

📋 **Executive Planning Tip:** Use time blocking to protect your most important work. Would you like me to search for time management strategies?"""
            
        elif function_name == "get_upcoming_events":
            days = arguments.get('days', 7)
            # More complete response to prevent re-calling
            output = f"""📅 **Upcoming Events Planning ({days} days)**

I don't have live calendar access, but here's strategic planning guidance:

🎯 **Weekly Planning Framework:**
• **Monday:** Week planning and priority setting
• **Wednesday:** Mid-week review and adjustments  
• **Friday:** Week completion and next week prep

📋 **Executive Recommendations:**
• Block 2-hour focus sessions for deep work
• Schedule buffer time between meetings
• Plan strategic thinking time daily

Would you like me to research specific productivity systems or scheduling strategies?"""
            
        elif function_name == "find_free_time":
            duration = arguments.get('duration', 60)
            date = arguments.get('date', 'today')
            output = f"""⏰ **Finding {duration}-minute Focus Blocks**

**Strategic Scheduling Advice:**
• Best focus times: 9-11 AM or 2-4 PM
• Avoid: Right after lunch (1-2 PM)
• Protect: Early morning for deep work

**Executive Time Management:**
• Batch similar tasks together
• Use calendar blocking to protect focus time
• Build in 15-minute buffers between meetings

Would you like me to research time blocking strategies?"""
            
        elif function_name == "search_emails":
            query = arguments.get('query', '')
            max_results = arguments.get('max_results', 5)
            output = f"""📧 **Email Management Strategy**

I don't have direct email access, but here's executive email guidance:

🎯 **Email Processing System:**
• Check email at set times (not constantly)
• Use 2-minute rule: If it takes <2 min, do it now
• Archive, delegate, or schedule longer items

📋 **Search Strategy for '{query}':**
• Use specific keywords and date ranges
• Set up filters for priority senders
• Create folders for project organization

Want me to research email management systems?"""
            
        else:
            output = f"📋 Function '{function_name}' executed for executive planning. I've provided strategic guidance based on executive planning principles."
        
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
    
    # Remove excessive spacing - keep content intact
    response = response.replace('\n\n\n', '\n\n')  # Triple to double
    response = response.replace('\n\n', '\n')       # Double to single
    
    # Ensure Discord limit
    if len(response) > 1100:
        response = response[:1100] + "\n\n🎯 *More executive insights available!*"
    
    return response.strip()

# ============================================================================
# DISCORD BOT COMMANDS - Executive Focus
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
        name="🔍 Planning Research",
        value="✅ Available" if BRAVE_API_KEY else "❌ Not configured",
        inline=True
    )
    
    embed.add_field(
        name="🎯 Specialties",
        value="Calendar • Planning • Productivity • Life OS • Strategy",
        inline=False
    )
    
    embed.add_field(
        name="📋 Channels",
        value=", ".join([f"#{ch}" for ch in ALLOWED_CHANNELS]),
        inline=False
    )
    
    await ctx.send(embed=embed)

@bot.command(name='plan')
async def plan_command(ctx, *, query):
    """Get planning and productivity advice"""
    async with ctx.typing():
        results = await planning_web_search(query, "productivity")
        await send_long_message(ctx, results)

@bot.command(name='schedule')
async def schedule_command(ctx, timeframe="today"):
    """Check calendar schedule"""
    async with ctx.typing():
        if timeframe.lower() == "week":
            prompt = f"@Rose show me my week ahead with strategic planning insights"
        else:
            prompt = f"@Rose show me my {timeframe} schedule"
        
        response = await get_rose_response(prompt, ctx.author.id)
        await send_long_message(ctx, response)

@bot.command(name='productivity')
async def productivity_command(ctx, *, topic):
    """Get productivity and time management advice"""
    async with ctx.typing():
        results = await planning_web_search(f"{topic} productivity tips", "productivity")
        await send_long_message(ctx, results)

@bot.command(name='help')
async def help_command(ctx):
    """Show Rose's help"""
    embed = discord.Embed(
        title=f"👑 {ASSISTANT_NAME} - {ASSISTANT_ROLE}",
        description="Your strategic executive assistant and productivity optimizer",
        color=0x6a1b9a
    )
    
    embed.add_field(
        name="💬 How to Use Rose",
        value=f"• Mention @{ASSISTANT_NAME} for executive planning\n• Ask about productivity, scheduling, life OS\n• DM me directly for strategic consultation",
        inline=False
    )
    
    embed.add_field(
        name="🔧 Commands",
        value="• `!plan [topic]` - Planning and productivity advice\n• `!schedule [timeframe]` - Calendar and scheduling\n• `!productivity [topic]` - Time management tips\n• `!ping` - Test connectivity\n• `!status` - Show capabilities",
        inline=False
    )
    
    embed.add_field(
        name="🎯 Specialties",
        value="• **Strategic Planning** - Life OS, quarterly reviews, goal setting\n• **Calendar Management** - Scheduling optimization, time blocking\n• **Productivity Systems** - GTD, time management, workflow optimization\n• **Executive Support** - High-level planning and coordination",
        inline=False
    )
    
    embed.add_field(
        name="📋 Example Requests",
        value="• `@Rose help me optimize my weekly planning`\n• `@Rose find time for a 2-hour deep work session`\n• `@Rose what's the best productivity system for executives?`\n• `@Rose show me my schedule with strategic insights`",
        inline=False
    )
    
    await ctx.send(embed=embed)

# ============================================================================
# MESSAGE HANDLING - Executive Focus
# ============================================================================

@bot.event
async def on_ready():
    print(f"👑 {ASSISTANT_NAME} is online as {bot.user}")
    print(f"🔗 Connected to {len(bot.guilds)} server(s)")
    print(f"👀 Monitoring: {', '.join(ALLOWED_CHANNELS)}")
    print(f"🔧 Assistant: {'✅' if ASSISTANT_ID else '❌'}")
    print(f"🔍 Planning Research: {'✅' if BRAVE_API_KEY else '❌'}")
    print(f"👑 Ready for executive planning and productivity optimization!")

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

# ============================================================================
# START ROSE
# ============================================================================

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("❌ DISCORD_TOKEN not found in environment variables")
        exit(1)
    
    print(f"👑 Starting {ASSISTANT_NAME} - Executive Assistant & Strategic Planner...")
    bot.run(DISCORD_TOKEN)