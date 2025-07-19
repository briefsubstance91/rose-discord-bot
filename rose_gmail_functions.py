# ============================================================================
# GMAIL INTEGRATION FUNCTIONS (ADD TO ROSE'S MAIN.PY)
# Add these after your calendar functions and before the function handling
# ============================================================================

import base64
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Gmail service (add this near your calendar_service initialization)
gmail_service = None

# Initialize Gmail service (add this in your Google setup section)
try:
    if GOOGLE_SERVICE_ACCOUNT_JSON:
        credentials_info = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
        credentials = Credentials.from_service_account_info(
            credentials_info,
            scopes=[
                'https://www.googleapis.com/auth/calendar.readonly',
                'https://www.googleapis.com/auth/calendar.events',
                'https://www.googleapis.com/auth/calendar',
                'https://www.googleapis.com/auth/gmail.readonly',
                'https://www.googleapis.com/auth/gmail.send',
                'https://www.googleapis.com/auth/gmail.modify'
            ]
        )
        gmail_service = build('gmail', 'v1', credentials=credentials)
        print("✅ Gmail service initialized")
        
except Exception as e:
    print(f"❌ Gmail setup error: {e}")
    gmail_service = None

# ============================================================================
# CORE GMAIL FUNCTIONS
# ============================================================================

def get_recent_emails(count=10, query="in:inbox"):
    """Get recent emails with Gmail query support"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        # Search for messages
        results = gmail_service.users().messages().list(
            userId='me',
            q=query,
            maxResults=count
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            return f"📧 **Recent Emails:** No emails found for query: {query}"
        
        formatted_emails = []
        
        for message in messages[:count]:
            msg = gmail_service.users().messages().get(
                userId='me',
                id=message['id'],
                format='metadata',
                metadataHeaders=['From', 'Subject', 'Date']
            ).execute()
            
            headers = {h['name']: h['value'] for h in msg['payload'].get('headers', [])}
            
            from_email = headers.get('From', 'Unknown')
            subject = headers.get('Subject', 'No Subject')
            date_str = headers.get('Date', '')
            
            # Parse date for better formatting
            try:
                if date_str:
                    from email.utils import parsedate_to_datetime
                    date_obj = parsedate_to_datetime(date_str)
                    toronto_tz = pytz.timezone('America/Toronto')
                    local_date = date_obj.astimezone(toronto_tz)
                    formatted_date = local_date.strftime('%m/%d %H:%M')
                else:
                    formatted_date = 'Unknown'
            except:
                formatted_date = 'Unknown'
            
            # Check if unread
            labels = msg.get('labelIds', [])
            unread_indicator = "🔴 " if 'UNREAD' in labels else ""
            
            formatted_emails.append(f"{unread_indicator}**{formatted_date}** | {from_email}\n📝 {subject}")
        
        return f"📧 **Recent Emails ({len(formatted_emails)}):**\n\n" + "\n\n".join(formatted_emails)
        
    except Exception as e:
        print(f"❌ Gmail error: {e}")
        return f"❌ Error retrieving emails: {str(e)}"

def get_unread_emails(count=10):
    """Get unread emails only"""
    return get_recent_emails(count, "is:unread")

def search_emails(query, count=10):
    """Search emails using Gmail search syntax"""
    return get_recent_emails(count, query)

def send_email(to_email, subject, body):
    """Send email through Gmail"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        # Create message
        message = MIMEText(body)
        message['to'] = to_email
        message['subject'] = subject
        
        # Encode message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        # Send message
        sent_message = gmail_service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()
        
        return f"✅ **Email Sent Successfully**\n📧 To: {to_email}\n📝 Subject: {subject}\n🆔 Message ID: {sent_message['id']}"
        
    except Exception as e:
        print(f"❌ Send email error: {e}")
        return f"❌ Failed to send email: {str(e)}"

def get_email_stats():
    """Get email dashboard statistics"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        # Get unread count
        unread_results = gmail_service.users().messages().list(
            userId='me',
            q='is:unread',
            maxResults=1
        ).execute()
        unread_count = unread_results.get('resultSizeEstimate', 0)
        
        # Get today's emails
        toronto_tz = pytz.timezone('America/Toronto')
        today = datetime.now(toronto_tz).strftime('%Y/%m/%d')
        today_results = gmail_service.users().messages().list(
            userId='me',
            q=f'newer_than:1d',
            maxResults=1
        ).execute()
        today_count = today_results.get('resultSizeEstimate', 0)
        
        # Get important emails
        important_results = gmail_service.users().messages().list(
            userId='me',
            q='is:important is:unread',
            maxResults=1
        ).execute()
        important_count = important_results.get('resultSizeEstimate', 0)
        
        return f"""📧 **Executive Email Dashboard**

🔴 **Unread:** {unread_count} emails
📅 **Today:** {today_count} emails received
⭐ **Important & Unread:** {important_count} emails

💡 **Quick Actions:**
• Use `!unread` for unread emails
• Use `!emails` for recent inbox
• Mention @Rose to process specific emails"""
        
    except Exception as e:
        print(f"❌ Email stats error: {e}")
        return f"❌ Error retrieving email statistics: {str(e)}"

def delete_email(email_id):
    """Move email to trash"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        gmail_service.users().messages().trash(
            userId='me',
            id=email_id
        ).execute()
        
        return f"✅ Email moved to trash (ID: {email_id})"
        
    except Exception as e:
        print(f"❌ Delete email error: {e}")
        return f"❌ Failed to delete email: {str(e)}"

def archive_email(email_id):
    """Archive email (remove from inbox)"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        gmail_service.users().messages().modify(
            userId='me',
            id=email_id,
            body={'removeLabelIds': ['INBOX']}
        ).execute()
        
        return f"✅ Email archived (ID: {email_id})"
        
    except Exception as e:
        print(f"❌ Archive email error: {e}")
        return f"❌ Failed to archive email: {str(e)}"

# ============================================================================
# ADD THESE TO YOUR handle_rose_functions_enhanced FUNCTION
# ============================================================================

# Add these elif blocks to your existing function handling:

elif function_name == "get_recent_emails":
    count = arguments.get('count', 10)
    query = arguments.get('query', 'in:inbox')
    output = get_recent_emails(count, query)

elif function_name == "get_unread_emails":
    count = arguments.get('count', 10)
    output = get_unread_emails(count)

elif function_name == "search_emails":
    query = arguments.get('query', '')
    count = arguments.get('count', 10)
    if query:
        output = search_emails(query, count)
    else:
        output = "❌ Missing required parameter: query"

elif function_name == "send_email":
    to_email = arguments.get('to_email', '')
    subject = arguments.get('subject', '')
    body = arguments.get('body', '')
    
    if to_email and subject and body:
        output = send_email(to_email, subject, body)
    else:
        output = "❌ Missing required parameters: to_email, subject, body"

elif function_name == "get_email_stats":
    output = get_email_stats()

elif function_name == "delete_email":
    email_id = arguments.get('email_id', '')
    if email_id:
        output = delete_email(email_id)
    else:
        output = "❌ Missing required parameter: email_id"

elif function_name == "archive_email":
    email_id = arguments.get('email_id', '')
    if email_id:
        output = archive_email(email_id)
    else:
        output = "❌ Missing required parameter: email_id"

# ============================================================================
# ADD THESE DISCORD COMMANDS
# ============================================================================

@bot.command(name='emails')
async def emails_command(ctx, count: int = 10):
    """Recent emails command"""
    try:
        async with ctx.typing():
            count = max(1, min(count, 20))
            emails = get_recent_emails(count)
            await send_long_message(ctx.message, emails)
    except Exception as e:
        print(f"❌ Emails command error: {e}")
        await ctx.send("📧 Recent emails unavailable. Please try again.")

@bot.command(name='unread')
async def unread_command(ctx, count: int = 10):
    """Unread emails command"""
    try:
        async with ctx.typing():
            count = max(1, min(count, 20))
            emails = get_unread_emails(count)
            await send_long_message(ctx.message, emails)
    except Exception as e:
        print(f"❌ Unread command error: {e}")
        await ctx.send("📧 Unread emails unavailable. Please try again.")

@bot.command(name='emailstats')
async def emailstats_command(ctx):
    """Email statistics command"""
    try:
        async with ctx.typing():
            stats = get_email_stats()
            await ctx.send(stats)
    except Exception as e:
        print(f"❌ Email stats command error: {e}")
        await ctx.send("📧 Email statistics unavailable. Please try again.")

# ============================================================================
# UPDATE YOUR HELP COMMAND TO INCLUDE EMAIL COMMANDS
# ============================================================================

# In your existing help_command function, add this section:
"""
**📧 Email Management:**
• `!emails [count]` - Recent emails (default 10)
• `!unread [count]` - Unread emails only
• `!emailstats` - Email dashboard overview

**💬 Natural Email Commands:**
• "@Rose check my unread emails"
• "@Rose send email to [person] about [topic]"
• "@Rose what emails came in today?"
"""