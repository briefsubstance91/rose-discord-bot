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

# Run coordination enhancement on startup
async def run_coordination_enhancement():
    """Run the coordination enhancement script on startup"""
    print("🔧 Running Rose coordination enhancement...")
    try:
        import subprocess
        result = subprocess.run(['python3', 'fix_rose_assistant.py'], 
                              capture_output=True, text=True, timeout=30)
        
        print("📋 Coordination enhancement output:")
        print(result.stdout)
        
        if result.stderr:
            print("⚠️ Enhancement warnings/errors:")
            print(result.stderr)
            
        if result.returncode == 0:
            print("✅ Coordination enhancement completed successfully!")
        else:
            print(f"❌ Enhancement failed with return code: {result.returncode}")
            
    except subprocess.TimeoutExpired:
        print("⏱️ Enhancement timed out after 30 seconds")
    except Exception as e:
        print(f"❌ Error running enhancement: {e}")
    
    print("🚀 Continuing with Rose startup...")

DISCORD_TOKEN = os.getenv("ROSE_DISCORD_TOKEN")
BRAVE_API_KEY = os.getenv('BRAVE_API_KEY')

# Configure Discord intents
intents = discord.Intents.default()
intents.message_content = True

# Bot setup
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# Rose's coordinated channels
ALLOWED_CHANNELS = ['life-os', 'calendar', 'planning-hub', 'general']

# Assistant team information for coordination
ASSISTANT_TEAM = {
    'vivian': {
        'name': 'Vivian Spencer',
        'focus': 'PR, Social Media, External Communications',
        'channels': ['social-overview', 'news-feed', 'external-communications'],
        'status': 'operational'
    },
    'celeste': {
        'name': 'Celeste Marchmont', 
        'focus': 'Content Creation, Copywriting, Research',
        'channels': ['writing-queue', 'summary-drafts', 'knowledge-pool'],
        'status': 'operational'
    },
    'maeve': {
        'name': 'Maeve Windham',
        'focus': 'Style, Travel, Lifestyle Management',
        'channels': ['packing-style-travel', 'shopping-tracker', 'meals-beauty-style'],
        'status': 'planned'
    },
    'flora': {
        'name': 'Flora Penrose',
        'focus': 'Spiritual Guidance, Tarot, Esoteric',
        'channels': ['spiritual-journal', 'energy-reading', 'seasonal-symbols'],
        'status': 'planned'
    }
}

print("🚀 Starting Rose Ashcombe - Executive Assistant & AI Team Coordinator...")

# ============================================================================
# COORDINATION HELPERS
# ============================================================================

async def post_coordination_message(channel_name, message, user_id, task_id=None):
    """Post coordination message to specific assistant channel"""
    try:
        target_channel = None
        for channel in bot.get_all_channels():
            if channel.name == channel_name and isinstance(channel, discord.TextChannel):
                target_channel = channel
                break
        
        if target_channel:
            embed = discord.Embed(
                title="🎯 Task Coordination from Rose",
                description=message,
                color=0x9b59b6,
                timestamp=datetime.now()
            )
            embed.add_field(name="Coordinator", value="Rose Ashcombe", inline=True)
            embed.add_field(name="Requesting User", value=f"<@{user_id}>", inline=True)
            if task_id:
                embed.add_field(name="Task ID", value=task_id, inline=True)
            embed.set_footer(text="AI Team Coordination System")
            
            await target_channel.send(embed=embed)
            return f"✅ Coordination message posted to #{channel_name}"
        else:
            return f"⚠️ Channel #{channel_name} not found - message logged for manual routing"
    except Exception as e:
        return f"❌ Error posting to #{channel_name}: {str(e)}"

async def gather_team_status():
    """Gather status from operational assistants"""
    team_status = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'assistants': {}
    }
    
    for assistant_key, assistant_info in ASSISTANT_TEAM.items():
        if assistant_info['status'] == 'operational':
            # For now, return status based on channel activity
            # In full implementation, this would ping the actual assistants
            team_status['assistants'][assistant_key] = {
                'name': assistant_info['name'],
                'status': '✅ Online',
                'focus': assistant_info['focus'],
                'channels': assistant_info['channels']
            }
        else:
            team_status['assistants'][assistant_key] = {
                'name': assistant_info['name'],
                'status': '⏳ Planned',
                'focus': assistant_info['focus']
            }
    
    return team_status

# ============================================================================
# WEB SEARCH FUNCTIONS
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
                        
                        formatted_results.append(f"**{i}. {title}**\n{snippet}\n{url_link}\n")
                    
                    return f"**🔍 Search Results for '{query}':**\n\n" + "\n".join(formatted_results)
                else:
                    return f"Search failed with status {response.status}"
                    
    except Exception as e:
        print(f"Search error: {e}")
        return f"Search error: {str(e)}"

# ============================================================================
# BOT COMMANDS - ENHANCED WITH COORDINATION
# ============================================================================

@bot.command(name='ping')
async def ping(ctx):
    """Test bot connectivity"""
    latency = round(bot.latency * 1000)
    embed = discord.Embed(
        title="🏓 Pong!",
        description="Rose Ashcombe is online and coordinating your AI team!",
        color=0x51cf66
    )
    embed.add_field(name="Latency", value=f"{latency}ms", inline=True)
    embed.add_field(name="Status", value="✅ Operational", inline=True)
    embed.add_field(name="Team Coordination", value="✅ Active", inline=True)
    await ctx.send(embed=embed)

@bot.command(name='status')
async def status(ctx):
    """Show comprehensive system status"""
    latency = round(bot.latency * 1000)
    embed = discord.Embed(
        title="🤖 Rose Status - Executive Assistant & AI Team Coordinator",
        description="Personal Productivity + AI Team Management",
        color=0x9b59b6
    )
    
    # Personal capabilities
    embed.add_field(
        name="🔗 Personal Assistant Functions",
        value="✅ Connected" if os.getenv("ROSE_ASSISTANT_ID") else "❌ Not configured",
        inline=True
    )
    
    embed.add_field(
        name="📅 Calendar Integration",
        value="✅ Connected" if os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON') else "⚠️ Not configured",
        inline=True
    )
    
    embed.add_field(
        name="🔍 Research Capabilities",
        value="✅ Enabled" if BRAVE_API_KEY else "⚠️ Disabled",
        inline=True
    )
    
    # Team coordination status
    operational_count = len([a for a in ASSISTANT_TEAM.values() if a['status'] == 'operational'])
    planned_count = len([a for a in ASSISTANT_TEAM.values() if a['status'] == 'planned'])
    
    embed.add_field(
        name="🎯 AI Team Coordination",
        value=f"✅ {operational_count} Operational, ⏳ {planned_count} Planned",
        inline=False
    )
    
    # Team members
    team_status = []
    for assistant_info in ASSISTANT_TEAM.values():
        status_icon = "✅" if assistant_info['status'] == 'operational' else "⏳"
        team_status.append(f"{status_icon} {assistant_info['name']} - {assistant_info['focus']}")
    
    embed.add_field(
        name="👥 Assistant Team",
        value="\n".join(team_status),
        inline=False
    )
    
    embed.add_field(
        name="📡 Coordination Channels",
        value=", ".join([f"#{channel}" for channel in ALLOWED_CHANNELS]),
        inline=False
    )
    
    embed.set_footer(text=f"Latency: {latency}ms | Your Executive Coordinator")
    
    await ctx.send(embed=embed)

@bot.command(name='coordinate')
async def coordinate_command(ctx, *, task_description):
    """Coordinate a task across the AI team"""
    async with ctx.typing():
        # Enhanced prompt for coordination
        coordination_prompt = f"""COORDINATION REQUEST: {task_description}

Instructions for Rose:
1. Analyze this task using your analyze_task_requirements function
2. Determine the best coordination strategy (single assistant vs multi-assistant)
3. Route appropriately using your coordination functions
4. Provide a clear coordination plan with next steps

Task: {task_description}
User: {ctx.author.display_name}
Channel: #{ctx.channel.name}"""
        
        response = await get_openai_response(coordination_prompt, user_id=ctx.author.id)
        await send_long_message_ctx(ctx, response)

@bot.command(name='route')
async def route_command(ctx, assistant_name, *, task):
    """Manually route a task to a specific assistant"""
    async with ctx.typing():
        # Validate assistant name
        valid_assistants = list(ASSISTANT_TEAM.keys()) + [info['name'].lower().replace(' ', '') for info in ASSISTANT_TEAM.values()]
        
        if assistant_name.lower() not in valid_assistants:
            await ctx.send(f"❌ Unknown assistant: {assistant_name}\nAvailable: {', '.join(ASSISTANT_TEAM.keys())}")
            return
        
        routing_prompt = f"""MANUAL ROUTING REQUEST:
Assistant: {assistant_name}
Task: {task}
User: {ctx.author.display_name}

Use your route_to_assistant function to handle this manual routing with appropriate coordination."""
        
        response = await get_openai_response(routing_prompt, user_id=ctx.author.id)
        await send_long_message_ctx(ctx, response)

@bot.command(name='dashboard')
async def dashboard_command(ctx, timeframe="daily"):
    """Create a comprehensive dashboard across all assistants"""
    async with ctx.typing():
        if timeframe not in ["daily", "weekly", "monthly", "quarterly"]:
            timeframe = "daily"
        
        dashboard_prompt = f"""DASHBOARD REQUEST:
Timeframe: {timeframe}
User: {ctx.author.display_name}

Use your create_dashboard_summary function to generate a comprehensive {timeframe} dashboard that includes:
1. Calendar analysis and strategic insights
2. Communication patterns and priorities  
3. AI team coordination status
4. Life OS integration and goal progress
5. Strategic recommendations for optimization

Focus on actionable insights and strategic coordination across all life areas."""
        
        response = await get_openai_response(dashboard_prompt, user_id=ctx.author.id)
        await send_long_message_ctx(ctx, response)

@bot.command(name='team_status')
async def team_status_command(ctx):
    """Show AI assistant team status"""
    team_status = await gather_team_status()
    
    embed = discord.Embed(
        title="👥 AI Assistant Team Status",
        description="Current status of all team members",
        color=0x9b59b6,
        timestamp=datetime.now()
    )
    
    for assistant_key, assistant_data in team_status['assistants'].items():
        status_text = f"**Status:** {assistant_data['status']}\n**Focus:** {assistant_data['focus']}"
        if 'channels' in assistant_data:
            channels = ", ".join([f"#{ch}" for ch in assistant_data['channels']])
            status_text += f"\n**Channels:** {channels}"
        
        embed.add_field(
            name=assistant_data['name'],
            value=status_text,
            inline=True
        )
    
    embed.set_footer(text="AI Team Coordination System")
    await ctx.send(embed=embed)

# Continue with existing commands (schedule, research, email, etc.)
@bot.command(name='schedule')
async def schedule_command(ctx, timeframe="today"):
    """Show calendar schedule with strategic insights"""
    async with ctx.typing():
        if timeframe.lower() == "today":
            prompt = "Show me today's schedule with strategic coordination insights and optimization recommendations."
        elif timeframe.lower() == "tomorrow":
            prompt = "Show me tomorrow's schedule and help me prepare strategically."
        elif timeframe.lower() == "week":
            prompt = "Give me a strategic overview of my week ahead with time management insights."
        else:
            try:
                days = int(timeframe)
                prompt = f"Show me my schedule for the next {days} days with strategic insights."
            except:
                prompt = "Show me my upcoming schedule with coordination insights."
        
        response = await get_openai_response(prompt, user_id=ctx.author.id)
        await send_long_message_ctx(ctx, response)

@bot.command(name='help')
async def help_command(ctx):
    """Show comprehensive help for Rose's coordination capabilities"""
    embed = discord.Embed(
        title="🤖 Rose Ashcombe - Executive Assistant & AI Team Coordinator",
        description="Personal Productivity + AI Team Management",
        color=0x9b59b6
    )
    
    embed.add_field(
        name="🎯 Coordination Commands",
        value="• `!coordinate [task]` - Intelligent task coordination\n• `!route [assistant] [task]` - Manual task routing\n• `!dashboard [daily/weekly/monthly]` - Life OS dashboard\n• `!team_status` - AI team status overview",
        inline=True
    )
    
    embed.add_field(
        name="📅 Personal Assistant",
        value="• `!schedule [today/week/7]` - Calendar analysis\n• `!email check` - Email coordination\n• `@Rose what's my schedule?` - Natural language\n• `@Rose find time for [task]` - Strategic scheduling",
        inline=True
    )
    
    embed.add_field(
        name="🔍 Research & Analysis",
        value="• `!research [topic]` - Strategic research\n• `@Rose analyze [topic]` - Deep analysis\n• Focus on productivity optimization\n• Life OS integration",
        inline=True
    )
    
    embed.add_field(
        name="👥 AI Team Members",
        value="• **Vivian Spencer** - PR, Social, Work Communications\n• **Celeste Marchmont** - Content, Copywriting, Research\n• **Maeve Windham** - Style, Travel, Lifestyle [Planned]\n• **Flora Penrose** - Spiritual, Tarot, Esoteric [Planned]",
        inline=False
    )
    
    embed.add_field(
        name="💡 Coordination Examples",
        value="• `@Rose draft a LinkedIn post about AI productivity`\n• `@Rose plan my conference presentation strategy`\n• `@Rose coordinate content for product launch`\n• `@Rose create my weekly dashboard`\n• `!coordinate research and write about productivity trends`",
        inline=False
    )
    
    embed.add_field(
        name="🎯 Strategic Focus",
        value="• **Intelligent Routing** - Right task to right assistant\n• **Multi-Assistant Projects** - Coordinated team workflows\n• **Life OS Integration** - Connect daily actions to quarterly goals\n• **Executive Oversight** - Strategic synthesis and optimization",
        inline=False
    )
    
    embed.add_field(
        name="🛠️ System Commands",
        value="• `!ping` - Test coordination system\n• `!status` - Full system status\n• `!help` - This help message\n• `!clear_memory` - Reset conversation",
        inline=True
    )
    
    embed.set_footer(text="🎯 Your Executive Coordinator - Streamlining your entire productivity ecosystem!")
    
    await ctx.send(embed=embed)

# ============================================================================
# MESSAGE HANDLING - ENHANCED WITH COORDINATION
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
    print(f"🎯 AI Team Coordination: ✅ ACTIVE")
    
    # Show team status
    operational = [name for name, info in ASSISTANT_TEAM.items() if info['status'] == 'operational']
    planned = [name for name, info in ASSISTANT_TEAM.items() if info['status'] == 'planned']
    print(f"👥 Team Status: {len(operational)} operational ({', '.join(operational)}), {len(planned)} planned")
    print(f"🚀 Rose Ashcombe: Your Executive Coordinator is ready!")

@bot.event
async def on_message(message):
    """Enhanced message handler with coordination intelligence"""
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return
    
    # Process commands first
    await bot.process_commands(message)
    
    # Only respond in allowed channels or DMs
    if not isinstance(message.channel, discord.DMChannel) and message.channel.name not in ALLOWED_CHANNELS:
        return

    # Handle mentions and DMs with coordination intelligence
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
                    "Hi! I'm Rose Ashcombe, your Executive Assistant & AI Team Coordinator! 🎯\n\n"
                    "**🧠 I manage your personal productivity**\n"
                    "**📅 I coordinate your calendar & emails**\n"
                    "**👥 I manage your AI assistant team**\n"
                    "**🎯 I route tasks to specialized assistants**\n\n"
                    "Try: `@Rose coordinate [task]` or `!help` for all commands!"
                )
                return

            print(f"📨 Coordination request from {message.author}: {content}")
            
            # Show typing indicator
            async with message.channel.typing():
                # Enhanced prompt with coordination context
                coordination_context = f"""COORDINATION CONTEXT:
User: {message.author.display_name}
Channel: #{message.channel.name}
Request: {content}

AVAILABLE AI TEAM:
• Vivian Spencer (PR/Social/Work) - ✅ Operational
• Celeste Marchmont (Content/Copywriting) - ✅ Operational  
• Maeve Windham (Style/Travel/Lifestyle) - ⏳ Planned
• Flora Penrose (Spiritual/Esoteric) - ⏳ Planned

COORDINATION INSTRUCTIONS:
1. First analyze if this requires task coordination using analyze_task_requirements
2. If it's a simple personal request (calendar/email), handle directly
3. If it requires specialized skills, route to appropriate assistant
4. If it's complex, coordinate multi-assistant workflow
5. Always provide strategic oversight and Life OS integration
6. Make coordination process transparent to user

Request: {content}"""

                # Check if it's a research request that needs web search
                research_keywords = ['research', 'find information', 'look up', 'search for', 'trends', 'latest', 'what are people saying']
                
                if any(keyword in content.lower() for keyword in research_keywords) and BRAVE_API_KEY:
                    print(f"🔍 Detected research component, performing web search...")
                    
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
                    
                    # Enhanced prompt with research data and coordination
                    enhanced_content = f"{coordination_context}\n\nRESEARCH DATA:\n{search_results}\n\nPlease coordinate this research request appropriately, potentially routing to Celeste for content synthesis or Vivian for PR strategy analysis."
                    
                    reply = await get_openai_response(enhanced_content, user_id=message.author.id)
                else:
                    # Regular coordination request
                    reply = await get_openai_response(coordination_context, user_id=message.author.id)
                
                # Send response with Discord message limit handling
                await send_long_message(message, reply)
                
        except Exception as e:
            print(f"❌ Error processing coordination request: {e}")
            await message.reply("Sorry, I encountered an error while processing your coordination request. Please try again.")

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
        await ctx.send("❌ **Coordination Error**\n\nSomething went wrong. Please try again or use `!help` for guidance.")

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("❌ ROSE_DISCORD_TOKEN not found in environment variables")
        exit(1)
    
    print("🚀 Starting Rose Ashcombe with AI Team Coordination...")
    
    # Run the coordination enhancement before starting the bot
    async def startup():
        await run_coordination_enhancement()
        try:
            await bot.start(DISCORD_TOKEN)
        except Exception as e:
            print(f"❌ Failed to start Rose coordination bot: {e}")
    
    # Run the startup sequence
    asyncio.run(startup())