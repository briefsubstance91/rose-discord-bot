import discord
from discord.ext import commands
import os
import asyncio
from datetime import datetime
import aiohttp
from dotenv import load_dotenv
from utils.openai_handler import get_openai_response

# Load environment variables
load_dotenv()

# TEMPORARY: Run assistant fix on startup
async def run_assistant_fix():
    """Run the assistant fix script on startup"""
    print("🔧 Running Rose assistant fix...")
    try:
        import subprocess
        result = subprocess.run(['python3', 'fix_rose_assistant.py'], 
                              capture_output=True, text=True, timeout=30)
        
        print("📋 Fix script output:")
        print(result.stdout)
        
        if result.stderr:
            print("⚠️ Fix script warnings/errors:")
            print(result.stderr)
            
        if result.returncode == 0:
            print("✅ Assistant fix completed successfully!")
        else:
            print(f"❌ Assistant fix failed with return code: {result.returncode}")
            
    except subprocess.TimeoutExpired:
        print("⏱️ Assistant fix timed out after 30 seconds")
    except Exception as e:
        print(f"❌ Error running assistant fix: {e}")
    
    print("🚀 Continuing with bot startup...")

DISCORD_TOKEN = os.getenv("ROSE_DISCORD_TOKEN")
BRAVE_API_KEY = os.getenv('BRAVE_API_KEY')

# Configure Discord intents
intents = discord.Intents.default()
intents.message_content = True

# Bot setup with commands - disable default help to avoid conflicts
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# Allowed channels for Vivian
ALLOWED_CHANNELS = ['life-os', 'calendar', 'planning-hub', 'general']

print("🚀 Starting Rose Ashcombe - Executive Planning Assistant...")

# ============================================================================
# WEB SEARCH FUNCTIONS (from Celeste)
# ============================================================================

async def search_web(query, search_type="general", num_results=5):
    """Web search using Brave Search API"""
    try:
        if not BRAVE_API_KEY:
            return "Web search not available - BRAVE_API_KEY not configured."
        
        headers = {
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip',
            'X-Subscription-Token': BRAVE_API_KEY
        }
        
        params = {
            'q': query,
            'count': num_results,
            'offset': 0,
            'mkt': 'en-US',
            'safesearch': 'moderate',
            'textDecorations': False,
            'textFormat': 'Raw'
        }
        
        if search_type == "reddit":
            params['q'] += " site:reddit.com"
        elif search_type == "news":
            params['freshness'] = 'Day'
            params['q'] += " latest news"
        elif search_type == "productivity":
            params['q'] += " productivity tools tips best practices"
        
        url = "https://api.search.brave.com/res/v1/web/search"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    results = data.get('web', {}).get('results', [])
                    
                    if not results:
                        return f"No results found for '{query}'"
                    
                    formatted_results = []
                    for i, result in enumerate(results[:3], 1):
                        title = result.get('title', 'No title')
                        snippet = result.get('description', 'No description')
                        url_link = result.get('url', '')
                        
                        if len(snippet) > 150:
                            snippet = snippet[:150] + '...'
                        
                        # Add source indicators
                        source_indicator = ""
                        if "reddit.com" in url_link.lower():
                            source_indicator = "🔴 "
                        elif any(domain in url_link.lower() for domain in ['edu', 'gov']):
                            source_indicator = "🎓 "
                        elif any(domain in url_link.lower() for domain in ['news', 'cnn', 'bbc']):
                            source_indicator = "📰 "
                        
                        formatted_results.append(f"**{i}. {source_indicator}{title}**\n{snippet}\n{url_link}\n")
                    
                    return f"**🔍 Search Results for '{query}':**\n\n" + "\n".join(formatted_results)
                else:
                    return f"Search failed with status {response.status}"
                    
    except Exception as e:
        print(f"Search error: {e}")
        return f"Search error: {str(e)}"

# ============================================================================
# BOT COMMANDS
# ============================================================================

@bot.command(name='ping')
async def ping(ctx):
    """Test bot connectivity"""
    latency = round(bot.latency * 1000)
    embed = discord.Embed(
        title="🏓 Pong!",
        description="Rose Ashcombe is online and ready to help with productivity!",
        color=0x51cf66
    )
    embed.add_field(name="Latency", value=f"{latency}ms", inline=True)
    embed.add_field(name="Status", value="✅ Operational", inline=True)
    await ctx.send(embed=embed)

@bot.command(name='status')
async def status(ctx):
    """Show comprehensive bot status"""
    latency = round(bot.latency * 1000)
    embed = discord.Embed(
        title="🤖 Rose Status - Productivity Assistant",
        description="Calendar + Email + Research + Memory",
        color=0x4dabf7
    )
    
    embed.add_field(
        name="🔗 OpenAI Assistant",
        value="✅ Connected" if os.getenv("ASSISTANT_ID") else "❌ Not configured",
        inline=True
    )
    
    embed.add_field(
        name="🔍 Web Search",
        value="✅ Enabled" if BRAVE_API_KEY else "⚠️ Disabled",
        inline=True
    )
    
    embed.add_field(
        name="📅 Google Calendar",
        value="✅ Connected" if os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON') else "⚠️ Not configured",
        inline=True
    )
    
    embed.add_field(
        name="📧 Gmail Integration",
        value="✅ Ready" if os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON') else "⚠️ Not configured",
        inline=True
    )
    
    capabilities = [
        "📅 Calendar Management",
        "📧 Email Search & Composition", 
        "🔍 Web Research",
        "🧠 Conversation Memory",
        "⏰ Schedule Analysis",
        "📝 Meeting Notes & Follow-ups"
    ]
    
    embed.add_field(
        name="⚡ Capabilities",
        value="\n".join(capabilities),
        inline=False
    )
    
    embed.add_field(
        name="👀 Monitored Channels",
        value=", ".join([f"#{channel}" for channel in ALLOWED_CHANNELS]),
        inline=False
    )
    
    embed.set_footer(text=f"Latency: {latency}ms | Your Productivity Assistant")
    
    await ctx.send(embed=embed)

@bot.command(name='schedule')
async def schedule_command(ctx, timeframe="today"):
    """Show calendar schedule"""
    async with ctx.typing():
        if timeframe.lower() == "today":
            prompt = "Show me my schedule for today with any strategic insights about my time allocation."
        elif timeframe.lower() == "tomorrow":
            prompt = "Show me tomorrow's schedule and help me prepare for it."
        elif timeframe.lower() == "week":
            prompt = "Give me an overview of my week ahead with time management insights."
        else:
            try:
                days = int(timeframe)
                prompt = f"Show me my schedule for the next {days} days with productivity insights."
            except:
                prompt = "Show me my upcoming schedule for the next few days."
        
        response = await get_openai_response(prompt, user_id=ctx.author.id)
        await send_long_message_ctx(ctx, response)

@bot.command(name='research')
async def research_command(ctx, *, query):
    """Perform web research with productivity focus"""
    if not BRAVE_API_KEY:
        await ctx.send("❌ **Web research disabled** - BRAVE_API_KEY not configured.")
        return
    
    async with ctx.typing():
        # Determine search type based on query
        search_type = "general"
        if any(word in query.lower() for word in ['productivity', 'workflow', 'efficiency', 'tools']):
            search_type = "productivity"
        elif "reddit" in query.lower():
            search_type = "reddit"
        elif any(word in query.lower() for word in ['news', 'latest', 'recent']):
            search_type = "news"
        
        search_results = await search_web(query, search_type)
        
        # Send to OpenAI with research context
        research_prompt = f"Based on this web research, provide strategic insights and actionable recommendations:\n\n{search_results}\n\nUser's research query: {query}\n\nFocus on productivity, efficiency, and practical application."
        
        analysis = await get_openai_response(research_prompt, user_id=ctx.author.id)
        
        response = f"**🔍 RESEARCH ANALYSIS: {query}**\n\n{analysis}"
        await send_long_message_ctx(ctx, response)

@bot.command(name='email')
async def email_command(ctx, action="check", *, details=""):
    """Email management commands"""
    async with ctx.typing():
        if action.lower() == "check":
            prompt = "Check my recent emails and highlight anything that needs my attention. Provide a strategic overview of what's important."
        elif action.lower() == "search" and details:
            prompt = f"Search my emails for: {details}. Show me the most relevant results and summarize what's important."
        elif action.lower() == "draft" and details:
            prompt = f"Help me draft an email: {details}. Make it professional and strategic."
        elif action.lower() == "compose" and details:
            prompt = f"Compose an email for me: {details}. Use a professional but approachable tone."
        else:
            await ctx.send("**📧 Email Commands:**\n• `!email check` - Check recent emails\n• `!email search [query]` - Search emails\n• `!email draft [description]` - Draft an email\n• `!email compose [description]` - Compose an email")
            return
        
        response = await get_openai_response(prompt, user_id=ctx.author.id)
        await send_long_message_ctx(ctx, response)

@bot.command(name='clear_memory')
async def clear_memory_command(ctx):
    """Clear conversation memory for the user"""
    # This will be handled by the updated openai_handler
    response = await get_openai_response("Clear my conversation memory and start fresh.", user_id=ctx.author.id, clear_memory=True)
    await ctx.send("🧹 **Memory cleared!** Starting fresh conversation.")

@bot.command(name='my_context')
async def show_context_command(ctx):
    """Show current conversation context"""
    async with ctx.typing():
        prompt = "Show me a summary of our recent conversation context and what we've been working on together."
        response = await get_openai_response(prompt, user_id=ctx.author.id)
        
        embed = discord.Embed(
            title="💭 Your Conversation Context",
            description=response,
            color=0x4dabf7
        )
        await ctx.send(embed=embed)

@bot.command(name='help')
async def help_command(ctx):
    """Show comprehensive help"""
    embed = discord.Embed(
        title="🤖 Rose Ashcombe - Your Executive Assistant",
        description="Calendar + Email + Research + Memory",
        color=0x4dabf7
    )
    
    embed.add_field(
        name="📅 Calendar Commands",
        value="• `!schedule today` - Today's schedule\n• `!schedule week` - This week\n• `!schedule 7` - Next 7 days\n• `@Vivian what's on my calendar?`",
        inline=True
    )
    
    embed.add_field(
        name="📧 Email Commands",
        value="• `!email check` - Check recent emails\n• `!email search [query]` - Search emails\n• `!email draft [topic]` - Draft email\n• `@Vivian find emails about [topic]`",
        inline=True
    )
    
    embed.add_field(
        name="🔍 Research Commands",
        value="• `!research [topic]` - Web research\n• `@Vivian research [topic]`\n• Focus on productivity insights",
        inline=True
    )
    
    embed.add_field(
        name="🧠 Memory Commands",
        value="• `!clear_memory` - Clear conversation\n• `!my_context` - Show history\n• Memory works automatically!",
        inline=True
    )
    
    embed.add_field(
        name="🛠️ System Commands",
        value="• `!ping` - Test connectivity\n• `!status` - Show capabilities\n• `!help` - This help message",
        inline=True
    )
    
    embed.add_field(
        name="💡 Natural Language",
        value="• `@Vivian when is my next meeting?`\n• `@Vivian draft follow-up for today's call`\n• `@Vivian find time for project review`\n• `@Vivian research productivity tools`",
        inline=False
    )
    
    embed.add_field(
        name="🎯 Productivity Focus",
        value="• **Schedule Analysis** - Strategic insights about your time\n• **Email Efficiency** - Prioritize what matters\n• **Research** - Productivity and workflow optimization\n• **Memory** - Remember your preferences and patterns",
        inline=False
    )
    
    embed.set_footer(text="💼 Your AI productivity partner - streamlining your workflow!")
    
    await ctx.send(embed=embed)

# ============================================================================
# MESSAGE HANDLING (Enhanced)
# ============================================================================

@bot.event
async def on_ready():
    print(f"🤖 Rose Ashcombe is online as {bot.user}")
    print(f"🔗 Connected to {len(bot.guilds)} guild(s)")
    print(f"👀 Monitoring channels: {', '.join(ALLOWED_CHANNELS)}")
    print(f"📅 Calendar: {'✅' if os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON') else '❌'}")
    print(f"📧 Gmail: {'✅' if os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON') else '❌'}")
    print(f"🔍 Research: {'✅' if BRAVE_API_KEY else '❌'}")
    print(f"🧠 Memory: ✅ Enhanced with context tracking")
    print(f"🚀 Rose Ashcombe: Your complete productivity assistant!")

@bot.event
async def on_message(message):
    """Enhanced message handler with research integration"""
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return
    
    # Process commands first
    await bot.process_commands(message)
    
    # Only respond in allowed channels or DMs
    if not isinstance(message.channel, discord.DMChannel) and message.channel.name not in ALLOWED_CHANNELS:
        return

    # Handle mentions and DMs
    if bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
        try:
            content = message.content
            
            # Clean mentions
            if bot.user.mentioned_in(message):
                for mention in message.mentions:
                    if mention == bot.user:
                        content = content.replace(f'<@{mention.id}>', '').strip()
                        content = content.replace(f'<@!{mention.id}>', '').strip()
            
            if not content:
                await message.reply(
                    "Hi! I'm Vivian, your enhanced productivity assistant! 💼\n\n"
                    "**🧠 I remember our conversations**\n"
                    "**📅 I manage your calendar**\n"
                    "**📧 I handle your emails**\n"
                    "**🔍 I research productivity topics**\n\n"
                    "Try: `@Vivian what's on my schedule?` or `!help` for all commands!"
                )
                return

            print(f"📨 Enhanced message from {message.author}: {content}")
            
            # Show typing indicator
            async with message.channel.typing():
                # Check if this is a research request and we have web search capabilities
                research_keywords = ['research', 'find information', 'look up', 'search for', 'what are people saying', 'latest trends', 'best practices', 'productivity tools']
                
                if any(keyword in content.lower() for keyword in research_keywords) and BRAVE_API_KEY:
                    print(f"🔍 Detected research request, performing web search...")
                    
                    # Determine search type
                    search_type = "general"
                    if any(word in content.lower() for word in ['productivity', 'workflow', 'efficiency']):
                        search_type = "productivity"
                    elif "reddit" in content.lower():
                        search_type = "reddit"
                    elif any(word in content.lower() for word in ['news', 'latest', 'recent']):
                        search_type = "news"
                    
                    # Perform web search
                    search_results = await search_web(content, search_type)
                    
                    # Enhanced prompt with research data
                    enhanced_content = f"RESEARCH DATA:\n{search_results}\n\nUSER REQUEST: {content}\n\nPlease analyze this research data and provide strategic insights focused on productivity and practical application. Be concise but actionable."
                    
                    reply = await get_openai_response(enhanced_content, user_id=message.author.id)
                else:
                    # Regular request without research
                    reply = await get_openai_response(content, user_id=message.author.id)
                
                # Send response with Discord message limit handling
                await send_long_message(message, reply)
                
        except Exception as e:
            print(f"❌ Error processing message: {e}")
            await message.reply("Sorry, I encountered an error while processing your message. Please try again.")

async def send_long_message(message, content):
    """Send long messages in chunks"""
    if len(content) <= 2000:
        await message.reply(content)
    else:
        chunks = [content[i:i+1900] for i in range(0, len(content), 1900)]
        for i, chunk in enumerate(chunks):
            if i == 0:
                await message.reply(chunk)
            else:
                await message.channel.send(f"*(continued {i+1}/{len(chunks)})*\n{chunk}")
            await asyncio.sleep(0.5)

async def send_long_message_ctx(ctx, content):
    """Send long messages in chunks for commands"""
    if len(content) <= 2000:
        await ctx.send(content)
    else:
        chunks = [content[i:i+1900] for i in range(0, len(content), 1900)]
        for i, chunk in enumerate(chunks):
            await ctx.send(f"*(Part {i+1}/{len(chunks)})*\n{chunk}")
            await asyncio.sleep(0.5)

@bot.event
async def on_command_error(ctx, error):
    """Enhanced error handling"""
    if isinstance(error, commands.CommandNotFound):
        return  # Ignore unknown commands
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ **Missing argument:** `{error.param.name}`\n\nUse `!help` to see correct usage.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ **Invalid argument:** {str(error)}\n\nUse `!help` to see correct usage.")
    else:
        print(f"❌ Command error: {error}")
        await ctx.send("❌ **Command Error**\n\nSomething went wrong. Please try again or use `!help` for guidance.")

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("❌ DISCORD_TOKEN not found in environment variables")
        exit(1)
    
    print("🚀 Starting Rose Ashcombe with unified capabilities...")
    
    # Run the assistant fix before starting the bot
    async def startup():
        await run_assistant_fix()
        try:
            await bot.start(DISCORD_TOKEN)
        except Exception as e:
            print(f"❌ Failed to start bot: {e}")
    
    # Run the startup sequence
    asyncio.run(startup())