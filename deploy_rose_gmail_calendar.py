#!/usr/bin/env python3
"""
DEPLOY ROSE GMAIL CALENDAR INTEGRATION
Complete deployment script for Rose's direct Gmail work calendar access
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def validate_environment():
    """Validate required environment variables"""
    print("🔍 VALIDATING ENVIRONMENT...")
    
    required_vars = ['OPENAI_API_KEY']
    optional_vars = ['ROSE_ASSISTANT_ID', 'ASSISTANT_ID', 'GOOGLE_SERVICE_ACCOUNT_JSON']
    
    missing_required = []
    missing_optional = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_required.append(var)
    
    for var in optional_vars:
        if not os.getenv(var):
            missing_optional.append(var)
    
    if missing_required:
        print(f"❌ Missing required environment variables: {', '.join(missing_required)}")
        return False
    
    if missing_optional:
        print(f"⚠️ Missing optional environment variables: {', '.join(missing_optional)}")
        print("   These can be configured in Railway environment")
    
    print("✅ Environment validation complete")
    return True

def run_assistant_update():
    """Run the assistant update script"""
    print("🤖 RUNNING ROSE ASSISTANT UPDATE...")
    
    try:
        import subprocess
        result = subprocess.run(['python3', 'rose_direct_work_calendar_integration.py'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Rose assistant update completed successfully")
            print(result.stdout)
            return True
        else:
            print(f"❌ Rose assistant update failed:")
            print(result.stderr)
            return False
    except FileNotFoundError:
        print("❌ rose_direct_work_calendar_integration.py not found")
        print("   Make sure all files are in the same directory")
        return False
    except Exception as e:
        print(f"❌ Error running assistant update: {e}")
        return False

def create_setup_guide():
    """Create setup guide file"""
    print("📋 CREATING SETUP GUIDE...")
    
    guide_content = '''# 🚀 Rose Gmail Calendar Integration Setup Guide

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
'''
    
    with open("ROSE_GMAIL_SETUP_GUIDE.md", "w") as f:
        f.write(guide_content)
    
    print("✅ Setup guide created: ROSE_GMAIL_SETUP_GUIDE.md")

def main():
    """Main deployment function"""
    print("🚀 ROSE GMAIL CALENDAR INTEGRATION DEPLOYMENT")
    print("=" * 60)
    
    # Check if required files exist
    required_files = [
        "rose_direct_work_calendar_integration.py",
        "rose_calendar_functions.py",
        "requirements_additions.txt"
    ]
    
    missing_files = [f for f in required_files if not Path(f).exists()]
    
    if missing_files:
        print(f"❌ Missing required files: {', '.join(missing_files)}")
        print("   Please ensure all integration files are downloaded")
        return
    
    print(f"✅ All required files found: {', '.join(required_files)}")
    
    # Validate environment
    env_valid = validate_environment()
    
    # Create setup guide
    create_setup_guide()
    
    # Update assistant if environment is ready
    assistant_updated = False
    if env_valid and os.getenv('OPENAI_API_KEY'):
        if os.getenv('ROSE_ASSISTANT_ID') or os.getenv('ASSISTANT_ID'):
            assistant_updated = run_assistant_update()
        else:
            print("⚠️ ROSE_ASSISTANT_ID not found - skipping assistant update")
            print("   You can run rose_direct_work_calendar_integration.py manually later")
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 DEPLOYMENT SUMMARY")
    print("=" * 60)
    
    print(f"✅ Required files: All present")
    print(f"✅ Setup guide: Created")
    print(f"{'✅' if env_valid else '❌'} Environment: {'Valid' if env_valid else 'Needs configuration'}")
    print(f"{'✅' if assistant_updated else '⚠️'} Assistant update: {'Complete' if assistant_updated else 'Pending'}")
    
    print("\n📝 NEXT STEPS:")
    print("1. Follow ROSE_GMAIL_SETUP_GUIDE.md for complete setup")
    
    if not assistant_updated:
        print("2. Configure missing environment variables")
        print("3. Run: python3 rose_direct_work_calendar_integration.py")
    
    print(f"4. Update your main.py with rose_calendar_functions.py code")
    print("5. Add requirements_additions.txt to your requirements.txt")
    print("6. Configure Google Cloud service account")
    print("7. Deploy to Railway and test with !calendar-status")
    
    if assistant_updated:
        print("\n🎉 ROSE ASSISTANT UPDATE COMPLETE!")
        print("   Rose now has direct work calendar capabilities")
    
    print("\n👑 Rose will soon have complete calendar autonomy!")

if __name__ == "__main__":
    main()