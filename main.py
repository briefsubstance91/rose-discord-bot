    async def send_email(self, to_email, subject, body, from_name="Rose Ashcombe"):
        """Send email through Gmail API"""
        if not self.service:
            return {
                'success': False,
                'error': 'Gmail service not available'
            }
        
        try:
            # Create message
            message = MIMEText(body)
            message['to'] = to_email
            message['subject'] = subject
            message['from'] = from_name
            
            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            # Send email
            sent_message = self.service.users().messages().send(
                userId=self.user_id,
                body={'raw': raw_message}
            ).execute()
            
            return {
                'success': True,
                'message_id': sent_message['id'],
                'to': to_email,
                'subject': subject,
                'summary': f"✅ **Email Sent Successfully**\n📧 To: {to_email}\n📝 Subject: {subject}\n🆔 ID: {sent_message['id'][:8]}..."
            }
            
        except Exception as e:
            error_msg = RoseErrorHandler.handle_api_error(e, "Gmail Send")
            return {
                'success': False,
                'error': error_msg,
                'summary': f"❌ Failed to send email: {error_msg}"
            }
    
    async def delete_email(self, email_id):
        """Delete email (move to trash)"""
        if not self.service:
            return {
                'success': False,
                'error': 'Gmail service not available'
            }
        
        try:
            # Move to trash
            self.service.users().messages().trash(
                userId=self.user_id,
                id=email_id
            ).execute()
            
            return {
                'success': True,
                'summary': f"🗑️ Email {email_id[:8]}... moved to trash"
            }
            
        except Exception as e:
            error_msg = RoseErrorHandler.handle_api_error(e, "Gmail Delete")
            return {
                'success': False,
                'error': error_msg,
                'summary': f"❌ Failed to delete email: {error_msg}"
            }
    
    async def archive_email(self, email_id):
        """Archive email (remove from inbox)"""
        if not self.service:
            return {
                'success': False,
                'error': 'Gmail service not available'
            }
        
        try:
            # Remove inbox label
            self.service.users().messages().modify(
                userId=self.user_id,
                id=email_id,
                body={'removeLabelIds': ['INBOX']}
            ).execute()
            
            return {
                'success': True,
                'summary': f"📁 Email {email_id[:8]}... archived"
            }
            
        except Exception as e:
            error_msg = RoseErrorHandler.handle_api_error(e, "Gmail Archive")
            return {
                'success': False,
                'error': error_msg,
                'summary': f"❌ Failed to archive email: {error_msg}"
            }
    
    async def mark_as_read(self, email_id):
        """Mark email as read"""
        if not self.service:
            return {
                'success': False,
                'error': 'Gmail service not available'
            }
        
        try:
            # Remove unread label
            self.service.users().messages().modify(
                userId=self.user_id,
                id=email_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            
            return {
                'success': True,
                'summary': f"✅ Email {email_id[:8]}... marked as read"
            }
            
        except Exception as e:
            error_msg = RoseErrorHandler.handle_api_error(e, "Gmail Mark Read")
            return {
                'success': False,
                'error': error_msg,
                'summary': f"❌ Failed to mark email as read: {error_msg}"
            }
    
    async def get_email_stats(self):
        """Get email statistics for executive dashboard"""
        if not self.service:
            return "📧 Gmail integration not available"
        
        try:
            # Get various counts
            unread = self.service.users().messages().list(
                userId=self.user_id,
                q='is:unread in:inbox',
                maxResults=1
            ).execute()
            
            today_emails = self.service.users().messages().list(
                userId=self.user_id,
                q='in:inbox newer_than:1d',
                maxResults=1
            ).execute()
            
            important = self.service.users().messages().list(
                userId=self.user_id,
                q='is:important is:unread',
                maxResults=1
            ).execute()
            
            unread_count = unread.get('resultSizeEstimate', 0)
            today_count = today_emails.get('resultSizeEstimate', 0)
            important_count = important.get('resultSizeEstimate', 0)
            
            stats = f"📊 **Email Dashboard**\n"
            stats += f"📥 Unread: {unread_count}\n"
            stats += f"📅 Today: {today_count}\n"
            stats += f"⭐ Important: {important_count}"
            
            return stats
            
        except Exception as e:
            error_msg = RoseErrorHandler.handle_api_error(e, "Gmail Stats")
            return f"📧 Email statistics error: {error_msg}"

# ============================================================================
# INITIALIZE SERVICES WITH ENHANCED ERROR HANDLING
# ============================================================================

# Discord setup
try:
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)
except Exception as e:
    print(f"❌ CRITICAL: Discord bot initialization failed: {e}")
    exit(1)

# OpenAI setup
try:
    client = OpenAI(api_key=OPENAI_API_KEY)
except Exception as e:
    print(f"❌ CRITICAL: OpenAI client initialization failed: {e}")
    exit(1)

# Google Services setup (Calendar + Gmail)
calendar_service = None
gmail_service = None
accessible_calendars = []
calendar_manager = None
gmail_manager = None

# Updated scopes for both Calendar and Gmail
GOOGLE_SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify'
]

try:
    if GOOGLE_SERVICE_ACCOUNT_JSON:
        credentials_info = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
        credentials = Credentials.from_service_account_info(
            credentials_info,
            scopes=GOOGLE_SCOPES
        )
        
        # Initialize Calendar service
        calendar_service = build('calendar', 'v3', credentials=credentials)
        calendar_list = calendar_service.calendarList().list().execute()
        for calendar in calendar_list.get('items', []):
            accessible_calendars.append((calendar['id'], calendar.get('summary', 'Unnamed')))
        
        calendar_manager = CalendarManager(calendar_service, accessible_calendars)
        print(f"✅ Google Calendar initialized with {len(accessible_calendars)} calendars")
        
        # Initialize Gmail service
        gmail_service = build('gmail', 'v1', credentials=credentials)
        gmail_manager = GmailManager(gmail_service)
        print("✅ Gmail service initialized")
        
except Exception as e:
    print(f"⚠️ Google services initialization failed: {e}")
    calendar_manager = CalendarManager(None, [])
    gmail_manager = GmailManager(None)

# Global state management
user_conversations = {}
active_runs = {}
last_response_time = {}
processing_messages = set()

# ============================================================================
# CONSOLIDATED CALENDAR FUNCTIONS
# ============================================================================

async def get_calendar_events_unified(timeframe="today", max_results=10, calendar_filter=None):
    """Unified calendar function replacing get_today_schedule, get_upcoming_events, etc."""
    if not calendar_manager:
        return "📅 Calendar integration not available"
    
    try:
        result = await calendar_manager.get_events(
            timeframe=timeframe,
            max_results=max_results,
            calendar_filter=calendar_filter
        )
        
        if result['success']:
            return result['summary']
        else:
            return result.get('error', 'Calendar error occurred')
            
    except Exception as e:
        return RoseErrorHandler.handle_calendar_error(e, "Calendar events retrieval")

async def create_calendar_event_unified(event_data):
    """Unified event creation function"""
    if not calendar_manager:
        return "📅 Calendar integration not available"
    
    try:
        result = await calendar_manager.create_event(event_data)
        
        if result['success']:
            return result['summary']
        else:
            return result.get('error', 'Event creation failed')
            
    except Exception as e:
        return RoseErrorHandler.handle_calendar_error(e, "Event creation")

# ============================================================================
# EMAIL FUNCTIONS FOR OPENAI ASSISTANT
# ============================================================================

async def get_recent_emails(count=10, query="in:inbox"):
    """Get recent emails for Rose's executive briefings"""
    if not gmail_manager:
        return "📧 Gmail integration not available"
    
    try:
        result = await gmail_manager.get_emails(query=query, max_results=count)
        return result['summary'] if result['success'] else result['error']
    except Exception as e:
        return RoseErrorHandler.handle_api_error(e, "Gmail")

async def get_unread_emails(count=10):
    """Get unread emails"""
    return await get_recent_emails(count, "is:unread in:inbox")

async def search_emails(search_query, count=10):
    """Search emails with Gmail search syntax"""
    if not gmail_manager:
        return "📧 Gmail search not available"
    
    try:
        # Prepend in:inbox if not specified
        if not any(prefix in search_query.lower() for prefix in ['in:', 'from:', 'to:', 'subject:']):
            search_query = f"in:inbox {search_query}"
        
        result = await gmail_manager.get_emails(query=search_query, max_results=count)
        return result['summary'] if result['success'] else result['error']
    except Exception as e:
        return RoseErrorHandler.handle_api_error(e, "Gmail Search")

async def send_email_function(to_email, subject, body):
    """Send email through Gmail"""
    if not gmail_manager:
        return "📧 Gmail sending not available"
    
    try:
        result = await gmail_manager.send_email(to_email, subject, body)
        return result['summary']
    except Exception as e:
        return RoseErrorHandler.handle_api_error(e, "Gmail Send")

async def get_email_stats_function():
    """Get email statistics"""
    if not gmail_manager:
        return "📧 Gmail integration not available"
    
    try:
        return await gmail_manager.get_email_stats()
    except Exception as e:
        return RoseErrorHandler.handle_api_error(e, "Gmail Stats")

async def delete_email_function(email_id):
    """Delete/trash email"""
    if not gmail_manager:
        return "📧 Gmail integration not available"
    
    try:
        result = await gmail_manager.delete_email(email_id)
        return result['summary']
    except Exception as e:
        return RoseErrorHandler.handle_api_error(e, "Gmail Delete")

async def archive_email_function(email_id):
    """Archive email"""
    if not gmail_manager:
        return "📧 Gmail integration not available"
    
    try:
        result = await gmail_manager.archive_email(email_id)
        return result['summary']
    except Exception as e:
        return RoseErrorHandler.handle_api_error(e, "Gmail Archive")

# ============================================================================
# IMPROVED SEARCH FUNCTION WITH ERROR HANDLING
# ============================================================================

async def planning_search_enhanced(query, max_results=5):
    """Enhanced search with better error handling"""
    if not BRAVE_API_KEY:
        return "🔍 Search not available - API key not configured", []
    
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            params = {
                'q': query,
                'count': max_results,
                'mkt': 'en-CA',
                'safesearch': 'moderate'
            }
            
            headers = {
                'X-Subscription-Token': BRAVE_API_KEY,
                'Accept': 'application/json'
            }
            
            async with session.get('https://api.search.brave.com/res/v1/web/search', 
                                 params=params, headers=headers) as response:
                
                if response.status == 200:
                    data = await response.json()
                    results = data.get('web', {}).get('results', [])
                    
                    if not results:
                        return "🔍 No search results found for your query", []
                    
                    formatted_results = []
                    sources = []
                    
                    for i, result in enumerate(results[:max_results]):
                        title = result.get('title', 'No title')[:80]
                        snippet = result.get('description', 'No description')[:150]
                        url = result.get('url', '')
                        
                        formatted_results.append(f"**{i+1}. {title}**\n{snippet}")
                        sources.append({
                            'number': i+1,
                            'title': title,
                            'url': url
                        })
                    
                    return "\n\n".join(formatted_results), sources
                    
                elif response.status == 429:
                    return "⏳ Search rate limit reached. Please try again later.", []
                elif response.status == 401:
                    return "🔐 Search authentication error. Contact administrator.", []
                else:
                    return f"🔍 Search service error (HTTP {response.status})", []
                    
    except asyncio.TimeoutError:
        return "⏱️ Search request timed out. Please try again.", []
    except Exception as e:
        error_msg = RoseErrorHandler.handle_api_error(e, "Search")
        RoseErrorHandler.log_error(e, "Planning search", {'query': query})
        return error_msg, []

# ============================================================================
# ENHANCED FUNCTION HANDLING WITH EMAIL FUNCTIONS
# ============================================================================

async def handle_rose_functions_enhanced(run, thread_id):
    """Enhanced function handling with calendar and email functions"""
    
    if not run or not hasattr(run, 'required_action') or not run.required_action:
        return
        
    if not hasattr(run.required_action, 'submit_tool_outputs') or not run.required_action.submit_tool_outputs:
        return
    
    if not hasattr(run.required_action.submit_tool_outputs, 'tool_calls') or not run.required_action.submit_tool_outputs.tool_calls:
        return
    
    tool_outputs = []
    
    for tool_call in run.required_action.submit_tool_outputs.tool_calls:
        function_name = getattr(tool_call.function, 'name', 'unknown')
        
        try:
            # Calendar functions (unified)
            if function_name in ["get_today_schedule", "get_upcoming_events", "get_calendar_events_detailed"]:
                args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
                
                # Map old function names to new unified approach
                if function_name == "get_today_schedule":
                    timeframe = "today"
                elif function_name == "get_upcoming_events":
                    timeframe = args.get('days', 'week')
                    if timeframe == 7:
                        timeframe = "week"
                    elif timeframe == 30:
                        timeframe = "month"
                else:
                    timeframe = args.get('timeframe', 'today')
                
                max_results = args.get('max_results', 10)
                result = await get_calendar_events_unified(timeframe, max_results)
                
                tool_outputs.append({
                    "tool_call_id": tool_call.id,
                    "output": result
                })
            
            elif function_name == "create_calendar_event":
                args = json.loads(tool_call.function.arguments)
                result = await create_calendar_event_unified(args)
                
                tool_outputs.append({
                    "tool_call_id": tool_call.id,
                    "output": result
                })
            
            # Email functions
            elif function_name == "get_recent_emails":
                args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
                count = args.get('count', 10)
                query = args.get('query', 'in:inbox')
                
                result = await get_recent_emails(count, query)
                tool_outputs.append({
                    "tool_call_id": tool_call.id,
                    "output": result
                })

            elif function_name == "get_unread_emails":
                args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
                count = args.get('count', 10)
                
                result = await get_unread_emails(count)
                tool_outputs.append({
                    "tool_call_id": tool_call.id,
                    "output": result
                })

            elif function_name == "search_emails":
                args = json.loads(tool_call.function.arguments)
                search_query = args.get('query', '')
                count = args.get('count', 10)
                
                if not search_query:
                    result = "🔍 Email search query required"
                else:
                    result = await search_emails(search_query, count)
                
                tool_outputs.append({
                    "tool_call_id": tool_call.id,
                    "output": result
                })

            elif function_name == "send_email":
                args = json.loads(tool_call.function.arguments)
                to_email = args.get('to_email', '')
                subject = args.get('subject', '')
                body = args.get('body', '')
                
                if not all([to_email, subject, body]):
                    result = "📧 Missing required email parameters (to_email, subject, body)"
                else:
                    result = await send_email_function(to_email, subject, body)
                
                tool_outputs.append({
                    "tool_call_id": tool_call.id,
                    "output": result
                })

            elif function_name == "get_email_stats":
                result = await get_email_stats_function()
                tool_outputs.append({
                    "tool_call_id": tool_call.id,
                    "output": result
                })

            elif function_name == "delete_email":
                args = json.loads(tool_call.function.arguments)
                email_id = args.get('email_id', '')
                
                if not email_id:
                    result = "🗑️ Email ID required for deletion"
                else:
                    result = await delete_email_function(email_id)
                
                tool_outputs.append({
                    "tool_call_id": tool_call.id,
                    "output": result
                })

            elif function_name == "archive_email":
                args = json.loads(tool_call.function.arguments)
                email_id = args.get('email_id', '')
                
                if not email_id:
                    result = "📁 Email ID required for archiving"
                else:
                    result = await archive_email_function(email_id)
                
                tool_outputs.append({
                    "tool_call_id": tool_call.id,
                    "output": result
                })
            
            elif function_name == "planning_search":
                args = json.loads(tool_call.function.arguments)
                query = args.get('query', '')
                max_results = args.get('max_results', 5)
                
                if not query:
                    result = "🔍 Search query required"
                else:
                    result, sources = await planning_search_enhanced(query, max_results)
                
                tool_outputs.append({
                    "tool_call_id": tool_call.id,
                    "output": result
                })
            
            else:
                # Handle unknown functions gracefully
                tool_outputs.append({
                    "tool_call_id": tool_call.id,
                    "output": f"⚠️ Function '{function_name}' not recognized"
                })
        
        except json.JSONDecodeError as e:
            error_msg = "⚠️ Invalid function arguments format"
            RoseErrorHandler.log_error(e, f"Function {function_name} JSON decode", 
                                     {'arguments': tool_call.function.arguments})
            tool_outputs.append({
                "tool_call_id": tool_call.id,
                "output": error_msg
            })
        
        except Exception as e:
            error_msg = RoseErrorHandler.handle_api_error(e, f"Function {function_name}")
            RoseErrorHandler.log_error(e, f"Function {function_name} execution")
            tool_outputs.append({
                "tool_call_id": tool_call.id,
                "output": error_msg
            })
    
    # Submit tool outputs
    if tool_outputs:
        try:
            client.beta.threads.runs.submit_tool_outputs(
                thread_id=thread_id,
                run_id=run.id,
                tool_outputs=tool_outputs
            )
        except Exception as e:
            error_msg = RoseErrorHandler.handle_api_error(e, "OpenAI tool outputs")
            RoseErrorHandler.log_error(e, "Tool outputs submission")
            print(f"❌ Failed to submit tool outputs: {error_msg}")

# ============================================================================
# MAIN RESPONSE FUNCTION WITH IMPROVED FORMATTING
# ============================================================================

async def get_rose_response(message, user_id):
    """Main response function with enhanced formatting and error handling"""
    try:
        if not ASSISTANT_ID:
            return "⚠️ Rose not configured - check ROSE_ASSISTANT_ID environment variable"
        
        # Rate limiting check
        current_time = time.time()
        if user_id in last_response_time:
            if current_time - last_response_time[user_id] < 3:
                return "⏳ Please wait a moment between requests."
        
        # Check for active runs
        if user_id in active_runs and active_runs[user_id]:
            return "⏳ Executive analysis in progress. Please wait..."
        
        # Mark user as having active run
        active_runs[user_id] = True
        
        try:
            # Get user's thread
            if user_id not in user_conversations:
                thread = client.beta.threads.create()
                user_conversations[user_id] = thread.id
                print(f"👑 Created executive thread for user {user_id}")
            
            thread_id = user_conversations[user_id]
            
            # Clean message
            clean_message = message.replace(f'<@{bot.user.id}>', '').strip() if hasattr(bot, 'user') and bot.user else message.strip()
            
            # Enhanced message with executive planning and email focus
            enhanced_message = f"""USER EXECUTIVE REQUEST: {clean_message}

RESPONSE GUIDELINES:
- Use professional executive formatting with strategic headers
- SMART DETECTION: Automatically detect calendar, email, or planning queries
- EMAIL QUERIES: Use email functions for inbox management, sending, searching
- CALENDAR QUERIES: Use calendar functions for scheduling and coordination
- PLANNING QUERIES: Use research functions for strategic insights
- Apply executive assistant tone: strategic, organized, action-oriented
- Keep main content under 1200 characters for Discord efficiency
- Use headers like: 👑 **Executive Summary:** or 📧 **Email Management:** or 📅 **Calendar Coordination:**
- IMPORTANT: Always provide strategic context and actionable next steps
- All times are in Toronto timezone (America/Toronto)
- For executive briefings, include both calendar and email statistics"""
            
            # Create message
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
                    raise e
            
            # Create and run assistant
            run = client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=ASSISTANT_ID
            )
            
            # Wait for completion with timeout
            start_time = time.time()
            timeout = 45
            
            while run.status in ['queued', 'in_progress', 'requires_action']:
                if time.time() - start_time > timeout:
                    return "⏱️ Executive analysis taking longer than expected. Please try again."
                
                if run.status == 'requires_action':
                    await handle_rose_functions_enhanced(run, thread_id)
                
                await asyncio.sleep(1)
                try:
                    run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
                except Exception as e:
                    print(f"❌ Error retrieving run status: {e}")
                    break
            
            # Handle run completion
            if run.status == 'completed':
                # Get messages
                messages = client.beta.threads.messages.list(thread_id=thread_id, limit=1)
                
                if messages.data:
                    assistant_message = messages.data[0]
                    if hasattr(assistant_message, 'content') and assistant_message.content:
                        response_text = assistant_message.content[0].text.value
                        
                        # Apply improved formatting
                        formatted_response = ResponseFormatter.format_response(response_text)
                        return formatted_response
                    else:
                        return "👑 Executive response processing... Please try again."
                else:
                    return "👑 Executive analysis complete. Please try again for results."
            
            elif run.status == 'failed':
                error_info = getattr(run, 'last_error', None)
                if error_info:
                    return RoseErrorHandler.handle_api_error(Exception(str(error_info)), "OpenAI Assistant")
                else:
                    return "❌ Executive analysis failed. Please try again."
            
            else:
                return f"⚠️ Executive analysis status: {run.status}. Please try again."
                
        finally:
            # Always clear active run status
            active_runs[user_id] = False
            last_response_time[user_id] = current_time
            
    except Exception as e:
        # Clear active run status on error
        active_runs[user_id] = False
        error_msg = RoseErrorHandler.handle_api_error(e, "Rose Assistant")
        RoseErrorHandler.log_error(e, "get_rose_response", {'user_id': user_id, 'message': message[:100]})
        return error_msg

# ============================================================================
# IMPROVED MESSAGE HANDLING
# ============================================================================

async def send_long_message(original_message, response):
    """Send response with improved length handling and error recovery"""
    try:
        if len(response) <= 2000:
            await original_message.reply(response)
        else:
            # Smart chunking that preserves formatting
            chunks = []
            current_chunk = ""
            
            # Split on double newlines first to preserve sections
            sections = response.split('\n\n')
            
            for section in sections:
                if len(current_chunk + section + '\n\n') > 1900:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = section + '\n\n'
                else:
                    current_chunk += section + '\n\n'
            
            if current_chunk:
                chunks.append(current_chunk.strip())
            
            # Send chunks
            for i, chunk in enumerate(chunks):
                if i == 0:
                    await original_message.reply(chunk)
                else:
                    await original_message.channel.send(chunk)
                    
    except discord.HTTPException as e:
        error_msg = RoseErrorHandler.handle_discord_error(e, "Message sending")
        try:
            await original_message.reply(error_msg)
        except:
            pass
    except Exception as e:
        RoseErrorHandler.log_error(e, "send_long_message")

# ============================================================================
# DISCORD BOT EVENT HANDLERS
# ============================================================================

@bot.event
async def on_ready():
    """Bot startup with comprehensive initialization"""
    try:
        print(f"✅ {ASSISTANT_NAME} has awakened!")
        print(f"🤖 Connected as: {bot.user.name} (ID: {bot.user.id})")
        print(f"🎯 Role: {ASSISTANT_ROLE}")
        print(f"📅 Calendar Status: {len(accessible_calendars)} accessible calendars")
        print(f"📧 Gmail Status: {'Enabled' if gmail_service else 'Disabled'}")
        print(f"🔍 Research: {'Enabled' if BRAVE_API_KEY else 'Disabled'}")
        print(f"🏢 Allowed channels: {', '.join(ALLOWED_CHANNELS)}")
        
        await bot.change_presence(
            status=discord.Status.online,
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="📅📧 Executive Calendar & Email Management"
            )
        )
        print("👑 Rose is ready for complete executive assistance!")
        
    except Exception as e:
        RoseErrorHandler.log_error(e, "Bot startup")

@bot.event
async def on_error(event, *args, **kwargs):
    """Global error handler"""
    print(f"❌ Discord error in {event}: {traceback.format_exc()}")

@bot.event
async def on_message(message):
    """Enhanced message handling with improved error handling"""
    try:
        if message.author == bot.user:
            return
        
        await bot.process_commands(message)
        
        channel_name = message.channel.name.lower() if hasattr(message.channel, 'name') else 'dm'
        is_dm = isinstance(message.channel, discord.DMChannel)
        is_allowed_channel = any(allowed in channel_name for allowed in ALLOWED_CHANNELS)
        
        if not (is_dm or is_allowed_channel):
            return

        if bot.user.mentioned_in(message) or is_dm:
            
            message_key = f"{message.author.id}_{message.content[:50]}"
            current_time = time.time()
            
            if message_key in processing_messages:
                return
            
            if message.author.id in last_response_time:
                if current_time - last_response_time[message.author.id] < 5:
                    return
            
            processing_messages.add(message_key)
            last_response_time[message.author.id] = current_time
            
            try:
                async with message.channel.typing():
                    response = await get_rose_response(message.content, message.author.id)
                    await send_long_message(message, response)
            except Exception as e:
                error_msg = RoseErrorHandler.handle_discord_error(e, "Message processing")
                try:
                    await message.reply(error_msg)
                except:
                    pass
            finally:
                processing_messages.discard(message_key)
                    
    except Exception as e:
        RoseErrorHandler.log_error(e, "on_message event")

# ============================================================================
# ROSE'S EXECUTIVE COMMANDS (WITH EMAIL COMMANDS ADDED)
# ============================================================================

@bot.command(name='ping')
async def ping_command(ctx):
    """Test Rose's connectivity with executive flair"""
    try:
        latency = round(bot.latency * 1000)
        await ctx.send(f"👑 Pong! Executive response time: {latency}ms")
    except Exception as e:
        error_msg = RoseErrorHandler.handle_discord_error(e, "Ping command")
        await ctx.send(error_msg)

@bot.command(name='schedule')
async def schedule_command(ctx):
    """Get today's calendar schedule"""
    try:
        async with ctx.typing():
            schedule = await get_calendar_events_unified("today", 10)
            
        embed = discord.Embed(
            title="📅 Today's Executive Schedule",
            description=schedule,
            color=0x9932CC
        )
        await ctx.send(embed=embed)
        
    except Exception as e:
        error_msg = RoseErrorHandler.handle_discord_error(e, "Schedule command")
        await ctx.send(error_msg)

@bot.command(name='upcoming')
async def upcoming_command(ctx, days: int = 7):
    """View upcoming events (default: 7 days)"""
    try:
        async with ctx.typing():
            if days <= 7:
                timeframe = "week"
            elif days <= 30:
                timeframe = "month"
            else:
                timeframe = "month"
                days = 30
            
            events = await get_calendar_events_unified(timeframe, 15)
            
        embed = discord.Embed(
            title=f"📋 Upcoming Events ({days} days)",
            description=events,
            color=0x9932CC
        )
        await ctx.send(embed=embed)
        
    except Exception as e:
        error_msg = RoseErrorHandler.handle_discord_error(e, "Upcoming command")
        await ctx.send(error_msg)

@bot.command(name='plan')
async def plan_command(ctx, *, query):
    """Planning research for strategic insights"""
    try:
        async with ctx.typing():
            if not query:
                await ctx.send("👑 Please provide a planning topic to research.")
                return
            
            search_results, sources = await planning_search_enhanced(query, 5)
            
        embed = discord.Embed(
            title="📊 Strategic Planning Research",
            description=f"**Query:** {query}\n\n{search_results}",
            color=0x9932CC
        )
        
        if sources:
            source_list = "\n".join([f"{s['number']}. {s['title'][:50]}..." for s in sources[:3]])
            embed.add_field(name="🔗 Sources", value=source_list, inline=False)
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        error_msg = RoseErrorHandler.handle_discord_error(e, "Plan command")
        await ctx.send(error_msg)

@bot.command(name='briefing')
async def briefing_command(ctx):
    """Executive briefing with calendar, email, and insights"""
    try:
        async with ctx.typing():
            # Get today's schedule
            today_schedule = await get_calendar_events_unified("today", 8)
            
            # Get upcoming events
            upcoming_events = await get_calendar_events_unified("week", 5)
            
            # Get email statistics
            email_stats = await get_email_stats_function()
            
            # Build executive briefing
            briefing_parts = [
                "👑 **Executive Briefing**",
                f"📅 **Today's Priority Schedule:**\n{today_schedule}",
                f"📧 **Email Status:**\n{email_stats}",
                f"📋 **Week Ahead Preview:**\n{upcoming_events}",
                "🎯 **Strategic Focus:** Optimize time blocks, manage inbox, and maintain executive productivity"
            ]
            
            briefing = "\n\n".join(briefing_parts)
        
        # Send as embed or long message depending on length
        if len(briefing) <= 4000:
            embed = discord.Embed(
                title="📊 Executive Briefing",
                description=briefing,
                color=0x9932CC
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send(briefing)
        
    except Exception as e:
        error_msg = RoseErrorHandler.handle_discord_error(e, "Briefing command")
        await ctx.send(error_msg)

@bot.command(name='emails')
async def emails_command(ctx, count: int = 10):
    """Get recent emails"""
    try:
        async with ctx.typing():
            emails = await get_recent_emails(count)
            
        embed = discord.Embed(
            title="📧 Recent Emails",
            description=emails,
            color=0x9932CC
        )
        await ctx.send(embed=embed)
        
    except Exception as e:
        error_msg = RoseErrorHandler.handle_discord_error(e, "Emails command")
        await ctx.send(error_msg)

@bot.command(name='unread')
async def unread_command(ctx, count: int = 10):
    """Get unread emails"""
    try:
        async with ctx.typing():
            emails = await get_unread_emails(count)
            
        embed = discord.Embed(
            title="🔵 Unread Emails",
            description=emails,
            color=0x9932CC
        )
        await ctx.send(embed=embed)
        
    except Exception as e:
        error_msg = RoseErrorHandler.handle_discord_error(e, "Unread command")
        await ctx.send(error_msg)

@bot.command(name='emailstats')
async def emailstats_command(ctx):
    """Get email statistics"""
    try:
        async with ctx.typing():
            stats = await get_email_stats_function()
            
        embed = discord.Embed(
            title="📊 Email Statistics",
            description=stats,
            color=0x9932CC
        )
        await ctx.send(embed=embed)
        
    except Exception as e:
        error_msg = RoseErrorHandler.handle_discord_error(e, "Email stats command")
        await ctx.send(error_msg)

@bot.command(name='status')
async def status_command(ctx):
    """Show Rose's comprehensive status"""
    try:
        embed = discord.Embed(
            title="👑 Rose Ashcombe - Executive Status",
            description="Complete executive assistance system status",
            color=0x9932CC
        )
        
        # System status
        embed.add_field(
            name="🤖 System Status",
            value=f"✅ Online\n📡 Latency: {round(bot.latency * 1000)}ms",
            inline=True
        )
        
        # Calendar status
        calendar_status = "✅ Active" if calendar_manager and calendar_manager.service else "❌ Unavailable"
        embed.add_field(
            name="📅 Calendar Integration",
            value=f"{calendar_status}\n📋 Calendars: {len(accessible_calendars)}",
            inline=True
        )
        
        # Gmail status
        gmail_status = "✅ Active" if gmail_manager and gmail_manager.service else "❌ Unavailable"
        embed.add_field(
            name="📧 Gmail Integration",
            value=gmail_status,
            inline=True
        )
        
        # Search capability
        search_status = "✅ Available" if BRAVE_API_KEY else "❌ Not configured"
        embed.add_field(
            name="🔍 Research Capability",
            value=search_status,
            inline=True
        )
        
        # Active conversations
        embed.add_field(
            name="📊 Executive Metrics",
            value=f"👥 Active Threads: {len(user_conversations)}\n🏃 Processing: {len(processing_messages)}",
            inline=False
        )
        
        # Channels
        embed.add_field(
            name="🏢 Monitored Channels",
            value=f"• {', '.join([f'#{ch}' for ch in ALLOWED_CHANNELS])}",
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        error_msg = RoseErrorHandler.handle_discord_error(e, "Status command")
        await ctx.send(error_msg)

@bot.command(name='help')
async def help_command(ctx):
    """Show Rose's executive capabilities and usage"""
    try:
        embed = discord.Embed(
            title="👑 Rose Ashcombe - Executive Assistant",
            description="Your strategic planning specialist with calendar integration, email management, and productivity optimization",
            color=0x9932CC
        )
        
        # How to Use Rose
        embed.add_field(
            name="💬 How to Use Rose",
            value="• Mention @Rose Ashcombe for executive planning & productivity advice\n• Ask about time management, scheduling, productivity systems\n• Get strategic insights based on your calendar and goals\n• Manage emails and coordinate communications",
            inline=False
        )
        
        # Executive Commands
        embed.add_field(
            name="🔧 Executive Commands",
            value="• `!schedule` - Get today's calendar\n• `!upcoming [days]` - View upcoming events\n• `!emails [count]` - Recent emails\n• `!unread [count]` - Unread emails\n• `!emailstats` - Email dashboard\n• `!briefing` - Executive briefing\n• `!plan [query]` - Planning research\n• `!ping` - Test connectivity\n• `!status` - Show capabilities",
            inline=False
        )
        
        # Example Requests
        embed.add_field(
            name="👑 Example Requests",
            value="• @Rose help me plan my week strategically\n• @Rose check my unread emails\n• @Rose send an email to the team about tomorrow's meeting\n• @Rose what's the best time blocking method?\n• @Rose give me my executive briefing\n• @Rose research productivity systems for executives",
            inline=False
        )
        
        # Specialties
        embed.add_field(
            name="📊 Specialties",
            value="👑 Executive Planning • 📅 Calendar Management • 📧 Email Management • 🎯 Productivity Systems • ⚡ Time Optimization • 🏢 Life OS",
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        error_msg = RoseErrorHandler.handle_discord_error(e, "Help command")
        await ctx.send(error_msg)

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    try:
        print("🚀 Starting Rose Ashcombe - Executive Assistant Bot (Complete with Email)")
        bot.run(DISCORD_TOKEN)
    except Exception as e:
        print(f"❌ CRITICAL: Bot startup failed: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        exit(1)#!/usr/bin/env python3
"""
ROSE ASHCOMBE - COMPLETE VERSION WITH EMAIL INTEGRATION
Executive Assistant with Full Google Calendar + Gmail Integration
"""
import pytz
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
from googleapiclient.errors import HttpError
import traceback
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from typing import Dict, List, Optional, Tuple, Union

# Email-specific imports
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import mimetypes

# Load environment variables
load_dotenv()

# Rose's executive configuration
ASSISTANT_NAME = "Rose Ashcombe"
ASSISTANT_ROLE = "Executive Assistant with Email & Calendar"
ALLOWED_CHANNELS = ['life-os', 'calendar', 'planning-hub', 'general']

# Environment variables with fallbacks
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("ROSE_DISCORD_TOKEN")
ASSISTANT_ID = os.getenv("ROSE_ASSISTANT_ID") or os.getenv("ASSISTANT_ID")
BRAVE_API_KEY = os.getenv('BRAVE_API_KEY')
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Enhanced integration
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
GOOGLE_CALENDAR_ID = os.getenv('GOOGLE_CALENDAR_ID')
GOOGLE_TASKS_CALENDAR_ID = os.getenv('GOOGLE_TASKS_CALENDAR_ID')
BRITT_ICLOUD_CALENDAR_ID = os.getenv('BRITT_ICLOUD_CALENDAR_ID')

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

# ============================================================================
# STANDARDIZED ERROR HANDLING CLASS
# ============================================================================

class RoseErrorHandler:
    """Centralized error handling for consistent user experience"""
    
    @staticmethod
    def handle_discord_error(error: Exception, context: str = "Discord operation") -> str:
        """Handle Discord-related errors with user-friendly messages"""
        error_str = str(error).lower()
        error_msg = f"❌ {context}: {str(error)[:100]}"
        print(f"{error_msg}\nFull traceback: {traceback.format_exc()}")
        
        if "rate limit" in error_str or "429" in error_str:
            return "⏳ Rose is handling multiple requests. Please try again in a moment."
        elif "timeout" in error_str:
            return "⏱️ Request timed out. Please try a more specific query."
        elif "permission" in error_str or "403" in error_str:
            return "🔐 Permission issue detected. Contact administrator if this persists."
        elif "not found" in error_str or "404" in error_str:
            return "🔍 Requested resource not found. Please check your request."
        else:
            return "👑 Executive assistance temporarily unavailable. Please try again."
    
    @staticmethod
    def handle_api_error(error: Exception, service: str = "API") -> str:
        """Handle API-related errors"""
        error_str = str(error).lower()
        
        if "quota" in error_str or "limit" in error_str:
            return f"📊 {service} quota reached. Executive capabilities temporarily reduced."
        elif "unauthorized" in error_str or "authentication" in error_str:
            return f"🔐 {service} authentication issue. Contact administrator."
        elif "timeout" in error_str:
            return f"⏱️ {service} timeout. Please try again."
        else:
            return f"🔧 {service} temporarily unavailable. ({str(error)[:50]})"
    
    @staticmethod
    def handle_calendar_error(error: Exception, operation: str = "Calendar operation") -> str:
        """Handle calendar-specific errors"""
        if isinstance(error, HttpError):
            status_code = error.resp.status
            if status_code == 404:
                return "📅 Calendar not found. Please check calendar permissions."
            elif status_code == 403:
                return "🔐 Calendar access denied. Share calendar with service account."
            elif status_code == 400:
                return "⚠️ Invalid calendar request. Please check your query."
            else:
                return f"📅 Calendar error ({status_code}). Please try again."
        else:
            return RoseErrorHandler.handle_api_error(error, "Calendar")
    
    @staticmethod
    def log_error(error: Exception, context: str, details: Dict = None):
        """Log detailed error information for debugging"""
        print(f"❌ ERROR in {context}:")
        print(f"   Type: {type(error).__name__}")
        print(f"   Message: {str(error)}")
        if details:
            print(f"   Details: {details}")
        print(f"   Traceback: {traceback.format_exc()}")

# ============================================================================
# IMPROVED RESPONSE FORMATTING CLASS
# ============================================================================

class ResponseFormatter:
    """Clean, structured response formatting without complex regex"""
    
    SECTION_PATTERNS = {
        'executive_summary': [
            r'👑\s*\*\*Executive Summary:?\*\*\s*(.*?)(?=\n\*\*|\n👑|\n📊|\n🎯|\n📅|\n💼|$)',
            r'Executive Summary:?\s*(.*?)(?=\n\*\*|\n👑|\n📊|\n🎯|\n📅|\n💼|$)',
            r'Summary:?\s*(.*?)(?=\n\*\*|\n👑|\n📊|\n🎯|\n📅|\n💼|$)'
        ],
        'calendar_details': [
            r'📅\s*\*\*(?:Calendar Coordination|Meeting Details):?\*\*\s*(.*?)(?=\n\*\*|\n👑|\n📊|\n🎯|\n🔗|$)',
            r'📅\s*\*\*Calendar:?\*\*\s*(.*?)(?=\n\*\*|\n👑|\n📊|\n🎯|\n🔗|$)',
            r'💼\s*\*\*Meeting Details:?\*\*\s*(.*?)(?=\n\*\*|\n👑|\n📊|\n🎯|\n🔗|$)'
        ],
        'email_details': [
            r'📧\s*\*\*(?:Email|Email Summary|Email Management):?\*\*\s*(.*?)(?=\n\*\*|\n👑|\n📊|\n🎯|\n📅|$)',
            r'📧\s*\*\*(?:Email Coordination|Email Response):?\*\*\s*(.*?)(?=\n\*\*|\n👑|\n📊|\n🎯|\n📅|$)'
        ],
        'strategic_analysis': [
            r'📊\s*\*\*Strategic Analysis:?\*\*\s*(.*?)(?=\n\*\*|\n👑|\n🎯|\n📅|\n💼|$)',
            r'📊\s*\*\*Analysis:?\*\*\s*(.*?)(?=\n\*\*|\n👑|\n🎯|\n📅|\n💼|$)'
        ],
        'action_items': [
            r'🎯\s*\*\*Action Items:?\*\*\s*(.*?)(?=\n\*\*|\n👑|\n📊|\n📅|\n💼|$)',
            r'🎯\s*\*\*Actions:?\*\*\s*(.*?)(?=\n\*\*|\n👑|\n📊|\n📅|\n💼|$)'
        ]
    }
    
    @classmethod
    def format_response(cls, response_text: str, response_type: str = "general") -> str:
        """Main formatting method that routes to specific formatters"""
        try:
            if not response_text or not response_text.strip():
                return "👑 Executive response processing... Please try again."
            
            # Determine response type if not specified
            if response_type == "general":
                response_type = cls._detect_response_type(response_text)
            
            # Route to appropriate formatter
            if response_type == "calendar":
                return cls._format_calendar_response(response_text)
            elif response_type == "email":
                return cls._format_email_response(response_text)
            elif response_type == "planning":
                return cls._format_planning_response(response_text)
            else:
                return cls._format_general_response(response_text)
                
        except Exception as e:
            RoseErrorHandler.log_error(e, "Response formatting")
            return "👑 Executive message formatting... Please try again."
    
    @classmethod
    def _detect_response_type(cls, text: str) -> str:
        """Detect response type based on content"""
        text_lower = text.lower()
        
        # Email indicators
        email_indicators = ['email', 'send', 'inbox', 'unread', 'message', 'reply']
        if any(indicator in text_lower for indicator in email_indicators):
            return "email"
        
        # Calendar indicators
        calendar_indicators = ['meeting', 'event', 'calendar', 'schedule', 'appointment', 'time:', 'date:']
        if any(indicator in text_lower for indicator in calendar_indicators):
            return "calendar"
        
        # Planning indicators  
        planning_indicators = ['strategy', 'plan', 'analysis', 'research', 'action item']
        if any(indicator in text_lower for indicator in planning_indicators):
            return "planning"
        
        return "general"
    
    @classmethod
    def _extract_section(cls, text: str, section_key: str) -> str:
        """Extract specific section using multiple pattern attempts"""
        patterns = cls.SECTION_PATTERNS.get(section_key, [])
        
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                content = match.group(1).strip()
                # Clean up the content
                content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)  # Remove excessive newlines
                content = re.sub(r'^\*\*|\*\*$', '', content)  # Remove leading/trailing **
                return content.strip()
        
        return ""
    
    @classmethod
    def _extract_links(cls, text: str) -> str:
        """Extract calendar or other links"""
        link_patterns = [
            r'🔗\s*\[View Event\][^)]*\)',
            r'🔗[^)]*View Event[^)]*\)',
            r'🔗[^)]*Google Calendar[^)]*\)',
            r'🔗.*?https://calendar\.google\.com[^\s)]*'
        ]
        
        for pattern in link_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0).strip()
        
        return ""
    
    @classmethod
    def _format_email_response(cls, text: str) -> str:
        """Format email-specific responses"""
        summary = cls._extract_section(text, 'executive_summary')
        email_details = cls._extract_section(text, 'email_details')
        actions = cls._extract_section(text, 'action_items')
        
        response_parts = []
        
        if summary:
            response_parts.append(f"👑 **Executive Summary:**\n{summary}")
        
        if email_details:
            response_parts.append(f"📧 **Email Management:**\n{email_details}")
        
        if actions:
            response_parts.append(f"🎯 **Next Steps:**\n{actions}")
        
        if not response_parts:
            return cls._clean_response_text(text)
        
        return "\n\n".join(response_parts)
    
    @classmethod
    def _format_calendar_response(cls, text: str) -> str:
        """Format calendar-specific responses (simplified)"""
        summary = cls._extract_section(text, 'executive_summary')
        details = cls._extract_section(text, 'calendar_details')
        links = cls._extract_links(text)
        
        # Build response with only essential sections
        response_parts = []
        
        if summary:
            response_parts.append(f"👑 **Executive Summary:**\n{summary}")
        
        if details:
            response_parts.append(f"📅 **Calendar Coordination:**\n{details}")
        elif not summary:  # Fallback if no clear sections
            # Try to extract key calendar info from the full text
            calendar_info = cls._extract_calendar_fallback(text)
            if calendar_info:
                response_parts.append(f"📅 **Calendar Coordination:**\n{calendar_info}")
        
        if links:
            response_parts.append(links)
        
        if not response_parts:
            # Final fallback - clean up the original text
            return cls._clean_response_text(text)
        
        return "\n\n".join(response_parts)
    
    @classmethod
    def _format_planning_response(cls, text: str) -> str:
        """Format planning/strategic responses (full format)"""
        summary = cls._extract_section(text, 'executive_summary')
        analysis = cls._extract_section(text, 'strategic_analysis')
        actions = cls._extract_section(text, 'action_items')
        calendar = cls._extract_section(text, 'calendar_details')
        
        response_parts = []
        
        if summary:
            response_parts.append(f"👑 **Executive Summary:**\n{summary}")
        
        if analysis:
            response_parts.append(f"📊 **Strategic Analysis:**\n{analysis}")
        
        if actions:
            response_parts.append(f"🎯 **Action Items:**\n{actions}")
        
        if calendar:
            response_parts.append(f"📅 **Calendar Coordination:**\n{calendar}")
        
        if not response_parts:
            return cls._clean_response_text(text)
        
        return "\n\n".join(response_parts)
    
    @classmethod
    def _format_general_response(cls, text: str) -> str:
        """Format general responses"""
        # For general responses, try to preserve structure but clean up
        return cls._clean_response_text(text)
    
    @classmethod
    def _extract_calendar_fallback(cls, text: str) -> str:
        """Fallback method to extract calendar info when sections aren't clear"""
        # Look for common calendar patterns
        calendar_lines = []
        
        for line in text.split('\n'):
            line = line.strip()
            if any(keyword in line.lower() for keyword in ['title:', 'date:', 'time:', 'location:', 'calendar:', 'created']):
                if not line.startswith('**') or not line.endswith('**'):
                    calendar_lines.append(f"• {line}")
                else:
                    calendar_lines.append(line)
        
        return "\n".join(calendar_lines) if calendar_lines else ""
    
    @classmethod
    def _clean_response_text(cls, text: str) -> str:
        """Clean up response text while preserving structure"""
        # Remove excessive newlines
        cleaned = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        # Ensure proper Discord character limits
        if len(cleaned) > 1900:
            cleaned = cleaned[:1900] + "\n\n👑 *(Executive insights continue)*"
        
        return cleaned.strip()

# ============================================================================
# CONSOLIDATED CALENDAR MANAGEMENT CLASS
# ============================================================================

class CalendarManager:
    """Unified calendar operations with consistent error handling"""
    
    def __init__(self, calendar_service, accessible_calendars):
        self.service = calendar_service
        self.calendars = accessible_calendars or []
        self.toronto_tz = pytz.timezone('America/Toronto')
    
    def _get_time_range(self, timeframe: str) -> Tuple[str, str]:
        """Get ISO time range for different timeframes"""
        now = datetime.now(self.toronto_tz)
        
        if timeframe == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        elif timeframe == "tomorrow":
            tomorrow = now + timedelta(days=1)
            start = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
            end = tomorrow.replace(hour=23, minute=59, second=59, microsecond=999999)
        elif timeframe == "week":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=7)
        elif timeframe == "month":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=30)
        else:  # Default to today
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        return start.isoformat(), end.isoformat()
    
    async def get_events(self, 
                        timeframe: str = "today",
                        max_results: int = 10,
                        calendar_filter: List[str] = None) -> Dict:
        """Unified method to get events from all or filtered calendars"""
        if not self.service:
            return {
                'success': False,
                'error': 'Calendar service not available',
                'events': [],
                'summary': 'Calendar integration not configured'
            }
        
        try:
            time_min, time_max = self._get_time_range(timeframe)
            all_events = []
            calendars_searched = []
            errors = []
            
            for calendar_id, calendar_name in self.calendars:
                # Apply calendar filter if specified
                if calendar_filter and calendar_name not in calendar_filter:
                    continue
                
                try:
                    events_result = self.service.events().list(
                        calendarId=calendar_id,
                        timeMin=time_min,
                        timeMax=time_max,
                        maxResults=max_results,
                        singleEvents=True,
                        orderBy='startTime'
                    ).execute()
                    
                    events = events_result.get('items', [])
                    
                    # Add calendar source to each event
                    for event in events:
                        event['calendar_source'] = calendar_name
                        event['calendar_id'] = calendar_id
                    
                    all_events.extend(events)
                    calendars_searched.append(calendar_name)
                    
                except HttpError as e:
                    error_msg = RoseErrorHandler.handle_calendar_error(e, f"Fetching {calendar_name}")
                    errors.append(f"{calendar_name}: {error_msg}")
                    RoseErrorHandler.log_error(e, f"Calendar fetch for {calendar_name}")
                
                except Exception as e:
                    error_msg = RoseErrorHandler.handle_api_error(e, f"{calendar_name} Calendar")
                    errors.append(f"{calendar_name}: {error_msg}")
                    RoseErrorHandler.log_error(e, f"Calendar fetch for {calendar_name}")
            
            # Sort all events by start time
            all_events.sort(key=lambda x: x.get('start', {}).get('dateTime', x.get('start', {}).get('date', '')))
            
            return {
                'success': True,
                'events': all_events[:max_results],
                'total_found': len(all_events),
                'timeframe': timeframe,
                'calendars_searched': calendars_searched,
                'errors': errors,
                'summary': self._create_events_summary(all_events[:max_results], timeframe, calendars_searched, errors)
            }
            
        except Exception as e:
            error_msg = RoseErrorHandler.handle_api_error(e, "Calendar Manager")
            RoseErrorHandler.log_error(e, "Calendar Manager get_events")
            return {
                'success': False,
                'error': error_msg,
                'events': [],
                'summary': error_msg
            }
    
    def _create_events_summary(self, events: List, timeframe: str, calendars: List[str], errors: List[str]) -> str:
        """Create a formatted summary of calendar events"""
        if not events and not errors:
            return f"📅 No events found for {timeframe}"
        
        if not events and errors:
            return f"📅 Calendar access issues:\n" + "\n".join(f"• {error}" for error in errors)
        
        # Format events
        event_lines = []
        for event in events:
            try:
                summary = event.get('summary', 'Untitled Event')
                start = event.get('start', {})
                calendar_source = event.get('calendar_source', 'Unknown')
                
                # Format time
                if start.get('dateTime'):
                    # Parse datetime
                    start_dt = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
                    if start_dt.tzinfo:
                        start_dt = start_dt.astimezone(self.toronto_tz)
                    time_str = start_dt.strftime('%I:%M %p').lower().lstrip('0')
                elif start.get('date'):
                    time_str = "All day"
                else:
                    time_str = "Unknown time"
                
                event_lines.append(f"• **{time_str}** - {summary} *({calendar_source})*")
                
            except Exception as e:
                RoseErrorHandler.log_error(e, "Event formatting", {'event': event})
                event_lines.append(f"• Event formatting error")
        
        # Build summary
        header = f"📅 **{timeframe.title()} Schedule** ({len(events)} event{'s' if len(events) != 1 else ''})"
        
        summary_parts = [header]
        if calendars:
            summary_parts.append(f"📋 *Searched: {', '.join(calendars)}*")
        
        summary_parts.extend(event_lines)
        
        if errors:
            summary_parts.append(f"\n⚠️ **Calendar Issues:**")
            summary_parts.extend(f"• {error}" for error in errors)
        
        return "\n".join(summary_parts)
    
    async def create_event(self, event_data: Dict) -> Dict:
        """Create a new calendar event"""
        if not self.service:
            return {
                'success': False,
                'error': 'Calendar service not available'
            }
        
        try:
            # Use primary calendar or first available
            calendar_id = self.calendars[0][0] if self.calendars else 'primary'
            
            # Create event
            created_event = self.service.events().insert(
                calendarId=calendar_id,
                body=event_data
            ).execute()
            
            return {
                'success': True,
                'event_id': created_event.get('id'),
                'event_link': created_event.get('htmlLink'),
                'summary': f"✅ Event created: {event_data.get('summary', 'New Event')}"
            }
            
        except HttpError as e:
            error_msg = RoseErrorHandler.handle_calendar_error(e, "Event creation")
            return {
                'success': False,
                'error': error_msg
            }
        except Exception as e:
            error_msg = RoseErrorHandler.handle_api_error(e, "Calendar")
            RoseErrorHandler.log_error(e, "Calendar event creation", {'event_data': event_data})
            return {
                'success': False,
                'error': error_msg
            }

# ============================================================================
# GMAIL MANAGER CLASS
# ============================================================================

class GmailManager:
    """Comprehensive Gmail management for Rose"""
    
    def __init__(self, gmail_service):
        self.service = gmail_service
        self.user_id = 'me'
    
    async def get_emails(self, query="in:inbox", max_results=10, include_body=False):
        """Get emails with flexible filtering"""
        if not self.service:
            return {
                'success': False,
                'error': 'Gmail service not available',
                'emails': [],
                'summary': 'Gmail integration not configured'
            }
        
        try:
            # Search for messages
            messages_result = self.service.users().messages().list(
                userId=self.user_id,
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = messages_result.get('messages', [])
            if not messages:
                return {
                    'success': True,
                    'emails': [],
                    'total_count': 0,
                    'summary': f'📭 No emails found for query: "{query}"'
                }
            
            # Get detailed email info
            email_details = []
            for message in messages:
                try:
                    email_detail = self.service.users().messages().get(
                        userId=self.user_id,
                        id=message['id'],
                        format='full' if include_body else 'metadata'
                    ).execute()
                    
                    email_info = self._parse_email(email_detail, include_body)
                    email_details.append(email_info)
                    
                except Exception as e:
                    RoseErrorHandler.log_error(e, f"Getting email {message['id']}")
                    continue
            
            return {
                'success': True,
                'emails': email_details,
                'total_count': len(email_details),
                'query': query,
                'summary': self._create_email_summary(email_details, query)
            }
            
        except Exception as e:
            error_msg = RoseErrorHandler.handle_api_error(e, "Gmail")
            return {
                'success': False,
                'error': error_msg,
                'emails': [],
                'summary': error_msg
            }
    
    def _parse_email(self, email_data, include_body=False):
        """Parse email data into structured format"""
        headers = {}
        payload = email_data.get('payload', {})
        
        # Extract headers
        for header in payload.get('headers', []):
            headers[header['name'].lower()] = header['value']
        
        email_info = {
            'id': email_data['id'],
            'thread_id': email_data['threadId'],
            'from': headers.get('from', 'Unknown sender'),
            'to': headers.get('to', 'Unknown recipient'),
            'subject': headers.get('subject', 'No subject'),
            'date': headers.get('date', 'Unknown date'),
            'labels': email_data.get('labelIds', []),
            'snippet': email_data.get('snippet', ''),
            'is_unread': 'UNREAD' in email_data.get('labelIds', [])
        }
        
        # Extract sender name
        from_email = email_info['from']
        if '<' in from_email:
            email_info['sender_name'] = from_email.split('<')[0].strip(' "')
            email_info['sender_email'] = from_email.split('<')[1].strip('>')
        else:
            email_info['sender_name'] = from_email
            email_info['sender_email'] = from_email
        
        # Extract body if requested
        if include_body:
            email_info['body'] = self._extract_body(payload)
        
        return email_info
    
    def _extract_body(self, payload):
        """Extract email body from payload"""
        body = ""
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data')
                    if data:
                        body = base64.urlsafe_b64decode(data).decode('utf-8')
                        break
        else:
            if payload['mimeType'] == 'text/plain':
                data = payload['body'].get('data')
                if data:
                    body = base64.urlsafe_b64decode(data).decode('utf-8')
        
        return body[:500] + "..." if len(body) > 500 else body
    
    def _create_email_summary(self, emails, query):
        """Create formatted summary of emails"""
        if not emails:
            return f"📭 No emails found for: '{query}'"
        
        email_lines = []
        unread_count = 0
        
        for email in emails[:10]:  # Limit display
            try:
                sender = email['sender_name'][:30]
                subject = email['subject'][:50]
                date_str = email['date'][:16] if email['date'] else 'Unknown'
                
                status = "🔵" if email['is_unread'] else "⚪"
                if email['is_unread']:
                    unread_count += 1
                
                email_lines.append(f"{status} **{sender}**\n   *{subject}*\n   📅 {date_str}")
                
            except Exception as e:
                RoseErrorHandler.log_error(e, "Email summary formatting")
                continue
        
        # Build summary
        header = f"📧 **Email Summary** ({len(emails)} total"
        if unread_count > 0:
            header += f", {unread_count} unread"
        header += ")"
        
        summary_parts = [header]
        if query != "in:inbox":
            summary_parts.append(f"🔍 *Query: {query}*")
        
        summary_parts.extend(email_lines)
        
        if len(emails) > 10:
            summary_parts.append(f"\n... and {len(emails) - 10} more emails")
        
        return "\n\n".join(summary_parts)
    
    async def send_email(self, to_email, subject, body, from_name="Rose Ashcombe"):
        """Send email through Gmail API"""
        if not