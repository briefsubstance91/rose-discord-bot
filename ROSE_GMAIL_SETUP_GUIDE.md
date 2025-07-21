# 🚀 Rose Gmail Calendar Integration Setup Guide

## 📦 Files Created:
1. `rose_direct_work_calendar_integration.py` - Updates Rose's OpenAI assistant
2. `rose_calendar_functions.py` - Gmail calendar functions for main.py
3. `requirements_additions.txt` - Dependencies to add
4. `deploy_rose_gmail_calendar.py` - This deployment script

## 🔧 Step 1: Update Rose's Assistant
```bash
python3 rose_direct_work_calendar_integration.py
```

## 🔧 Step 2: Google Cloud Setup
1. Go to Google Cloud Console (console.cloud.google.com)
2. Enable Gmail Calendar API
3. Create Service Account:
   - Name: "rose-gmail-calendar"
   - Role: "Project > Viewer"
   - Download JSON key file
4. Share Gmail Calendar:
   - Open calendar.google.com
   - Settings > Share with specific people
   - Add service account email with "See all event details"

## 🔧 Step 3: Environment Variables (Railway)
```bash
DISCORD_TOKEN=your_discord_bot_token
OPENAI_API_KEY=sk-proj-your_openai_key
ROSE_ASSISTANT_ID=asst_your_rose_assistant_id
GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account",...}
GMAIL_WORK_CALENDAR_ID=primary
```

## 🔧 Step 4: Update main.py
Add to the top of your main.py:
```python
from rose_calendar_functions import handle_rose_calendar_commands, ROSE_CALENDAR_FUNCTION_HANDLERS

# Update your function_handlers dictionary:
function_handlers.update(ROSE_CALENDAR_FUNCTION_HANDLERS)
```

Add to your on_message function:
```python
@bot.event
async def on_message(message):
    # Your existing code...
    
    # Add this line for Rose's calendar commands:
    if await handle_rose_calendar_commands(message):
        return  # Command was handled
    
    # Rest of your existing code...
```

## 🔧 Step 5: Update Requirements
Add to requirements.txt:
```
google-auth==2.23.4
google-auth-oauthlib==1.1.0
google-auth-httplib2==0.1.1
google-api-python-client==2.108.0
```

## 🧪 Step 6: Test Commands
```
!calendar-status      # Check all integrations
!briefing            # Enhanced briefing with work calendar
!work-calendar today  # Direct Gmail calendar access
!work-analysis       # Work schedule analysis
!meeting-prep        # Meeting preparation summary
```

## 🚀 Step 7: Deploy
1. Commit changes to GitHub
2. Railway auto-deploys
3. Test with !calendar-status

## ✅ Success Indicators:
- Assistant update completes without errors
- !calendar-status shows Gmail service connected
- !briefing includes work calendar events
- Rose can analyze your work schedule

## 🔧 Troubleshooting:
- Gmail Service Disconnected: Check GOOGLE_SERVICE_ACCOUNT_JSON
- No work events: Verify calendar sharing and GMAIL_WORK_CALENDAR_ID
- Permission errors: Ensure service account has calendar access

Rose will now have complete work calendar autonomy! 👑
