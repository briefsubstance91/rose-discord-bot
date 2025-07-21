#!/usr/bin/env python3
"""
COMPLETE ROSE GMAIL CALENDAR DEPLOYMENT
Automated deployment of Rose's direct Gmail work calendar integration
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def create_integration_files():
    """Create all integration files for Rose's Gmail calendar"""
    print("📁 CREATING ROSE GMAIL CALENDAR INTEGRATION FILES...")
    
    files_created = []
    
    # 1. Create requirements.txt additions
    requirements_additions = """
# Rose Gmail Calendar Integration Dependencies
google-auth==2.23.4
google-auth-oauthlib==1.1.0
google-auth-httplib2==0.1.1
google-api-python-client==2.108.0
"""
    
    req_file = "rose_gmail_requirements.txt"
    with open(req_file, 'w') as f:
        f.write(requirements_additions.strip())
    files_created.append(req_file)
    
    # 2. Create environment template
    env_template = """
# Rose Gmail Calendar Integration Environment Variables
GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account",...}
GMAIL_WORK_CALENDAR_ID=primary
WEATHER_API_KEY=your_weather_key_optional
"""
    
    env_file = "rose_gmail_env_template.txt"
    with open(env_file, 'w') as f:
        f.write(env_template.strip())
    files_created.append(env_file)
    
    print(f"✅ Created integration files: {', '.join(files_created)}")
    return files_created

def create_setup_guide():
    """Create comprehensive setup guide"""
    print("📋 CREATING GMAIL INTEGRATION SETUP GUIDE...")
    
    guide_file = "ROSE_GMAIL_SETUP_GUIDE.md"
    guide_content = '''# 🚀 Rose Direct Gmail Calendar Integration Setup Guide

## 📋 Overview
Rose now has DIRECT access to your Gmail work calendar, eliminating dependency on Vivian for work scheduling intelligence.

## 🔧 Setup Steps

### 1. Google Cloud Service Account Setup
```bash
1. Go to Google Cloud Console (console.cloud.google.com)
2. Select your project or create new one
3. Enable APIs:
   - Navigate to "APIs & Services" > "Library"
   - Search and enable "Google Calendar API"
   - Search and enable "Gmail API" (if needed)
4. Create Service Account:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "Service Account"
   - Name: "rose-gmail-calendar-integration"
   - Grant role: "Project > Viewer" (minimal permissions)
   - Create and download JSON key file
5. Copy JSON content to GOOGLE_SERVICE_ACCOUNT_JSON environment variable
```

### 2. Share Gmail Calendar with Service Account
```bash
1. Open Gmail Calendar (calendar.google.com)
2. Find your work calendar (usually "Primary" or your work email)
3. Click the 3 dots next to calendar name > "Settings and sharing"
4. Scroll to "Share with specific people"
5. Add the service account email (from JSON file: client_email field)
6. Set permission to "See all event details"
7. Click "Send"
```

### 3. Environment Variables (Railway)
```bash
# Required Variables:
DISCORD_TOKEN=your_discord_bot_token
OPENAI_API_KEY=sk-proj-your_openai_key
ROSE_ASSISTANT_ID=asst_your_rose_assistant_id
GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account",...}

# Optional Variables:
GMAIL_WORK_CALENDAR_ID=primary
WEATHER_API_KEY=your_weather_key
```

## 🎯 New Rose Capabilities

### Enhanced Commands:
- `!briefing` - Now includes direct work calendar analysis
- `!work-calendar [timeframe]` - Direct Gmail work calendar access
- `!work-analysis [focus]` - Analyze work schedule (priorities, conflicts, prep)
- `!meeting-prep [timeframe]` - Meeting preparation summary
- `!coordinate-calendars [days]` - Cross-calendar coordination
- `!calendar-status` - Check all calendar integration health

### Natural Language Commands:
- "@Rose give me my comprehensive morning briefing"
- "@Rose analyze my work schedule for today"
- "@Rose coordinate my work and personal calendars"
- "@Rose what meetings need prep today?"
- "@Rose check my calendar integration status"

## 🧪 Testing the Integration

### 1. Test Calendar Access
```
!calendar-status
```
Expected output:
- ✅ Gmail Service: Connected
- ✅ Gmail Work Calendar: Active
- ✅ Personal Calendar Service: Connected
- ✅ Weather Service: Connected
- 📊 Integration Health: 🟢 All systems operational

### 2. Test Direct Work Calendar
```
!work-calendar today
!work-calendar week
```
Should display work events from your Gmail calendar with meeting categorization.

### 3. Test Enhanced Briefing
```
!briefing
```
Should include:
- Weather update for Toronto
- Work calendar events (direct from Gmail)
- Work priorities analysis
- Personal calendar events
- Cross-calendar coordination
- Meeting preparation summary

### 4. Test Work Analysis
```
!work-analysis priorities
!work-analysis conflicts
!meeting-prep today
```

## 🔧 Troubleshooting

### "Gmail Service: ❌ Disconnected"
- Check GOOGLE_SERVICE_ACCOUNT_JSON is valid JSON (use JSON validator)
- Verify Gmail API is enabled in Google Cloud Console
- Ensure service account has proper project permissions

### "Work calendar not accessible"
- Verify GMAIL_WORK_CALENDAR_ID (try 'primary' for main Gmail calendar)
- Check Gmail calendar sharing with service account email
- Ensure service account email has "See all event details" permission
- Calendar sharing can take 5-10 minutes to activate

### "No work events found" (but you have events)
- Check timezone settings (should auto-detect Toronto)
- Verify calendar sharing is active and saved
- Try different GMAIL_WORK_CALENDAR_ID values
- Use `!calendar-status` for diagnostic information

### Permission Issues
- Service account email must be shared on the correct calendar
- Try removing and re-adding the service account email to calendar sharing
- Ensure you're sharing your work calendar (not personal)

## 📊 Expected Enhanced Briefing Format

```
👑 Comprehensive Executive Briefing for Monday, July 21, 2025

🌤️ Weather Update (Toronto): 22°C ☀️ Clear
🌡️ Feels like: 24°C | Humidity: 60%
🔆 UV Index: 6 - Protection essential

💼 Work Calendar (Direct Access): 4 work meetings
   💼 9:00 AM: Client strategy meeting
   💼 11:00 AM: Team standup
   💼 2:00 PM: Presentation to stakeholders
   💼 4:00 PM: External partner call

💼 Work Priorities Analysis (today):
📊 Meeting Breakdown: 4 total meetings
   • Client Meetings: 1
   • Presentations: 1
   • External Calls: 1
   • Internal Meetings: 1

🎯 Priority Preparation Needed:
   🔴 Client strategy meeting - High prep needed
   🔴 Presentation to stakeholders - High prep needed

📅 Personal Schedule: 2 personal events
   📅 6:00 PM: Dinner with team
   📅 8:00 PM: Personal training session

🤝 Cross-Calendar Coordination:
✅ No conflicts detected
📊 Calendar Health: Work and personal schedules well-coordinated

📋 Meeting Prep Summary (today):
🔴 High Priority Preparation (2 meetings):
   🔴 9:00 AM: Client strategy meeting - Start prep 24-48 hours in advance
   🔴 2:00 PM: Presentation to stakeholders - Test tech, rehearse slides

📊 Strategic Focus: Balance work priorities with personal commitments.
```

## 🚀 Deployment Steps

### 1. Update Rose's Assistant
```bash
python rose_direct_work_calendar_integration.py
```

### 2. Update Rose's main.py
- Copy the Gmail calendar integration code
- Add new function handlers
- Update command processing
- Add required imports

### 3. Update Requirements
```bash
# Add to your requirements.txt:
google-auth==2.23.4
google-auth-oauthlib==1.1.0
google-auth-httplib2==0.1.1
google-api-python-client==2.108.0
```

### 4. Deploy to Railway
- Commit changes to GitHub
- Railway auto-deploys via GitHub integration
- Monitor deployment logs
- Test integration with `!calendar-status`

### 5. Verification
- Run all test commands
- Verify work calendar access
- Check briefing enhancement
- Test cross-calendar coordination

## 🎯 Benefits of Direct Integration

### ✅ Advantages:
- **No Dependencies**: Rose doesn't need Vivian for work calendar
- **Real-time Access**: Direct Gmail calendar API access
- **Better Performance**: Fewer API calls, reduced latency
- **Comprehensive Briefings**: All calendar data in one place
- **Strategic Insights**: Cross-calendar optimization
- **Meeting Intelligence**: Automatic preparation analysis
- **Complete Autonomy**: Rose is now fully calendar-autonomous

### 📈 Architecture Improvement:
- Eliminated Vivian dependency for work scheduling
- Simplified integration with better error handling
- Enhanced executive briefing capabilities
- Improved calendar coordination and conflict detection
- Strategic meeting preparation intelligence

## 💡 Next Steps

After successful deployment:
1. **Test all new commands** to ensure proper functionality
2. **Monitor integration health** with `!calendar-status`
3. **Optimize calendar sharing** for best performance
4. **Explore advanced features** like meeting prep automation
5. **Scale to other assistants** if needed

Rose is now your complete executive assistant with full calendar autonomy! 👑
'''
    
    with open(guide_file, 'w') as f:
        f.write(guide_content)
    
    print(f"✅ Created comprehensive setup guide: {guide_file}")
    return guide_file

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
        print("   These can be configured later in Railway")
    
    print("✅ Environment validation complete")
    return True

def run_assistant_update():
    """Run the assistant update script"""
    print("🤖 RUNNING ROSE ASSISTANT UPDATE...")
    
    try:
        # Import and run the Rose update
        import subprocess
        result = subprocess.run(['python', 'rose_direct_work_calendar_integration.py'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Rose assistant update completed successfully")
            print(result.stdout)
            return True
        else:
            print(f"❌ Rose assistant update failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error running assistant update: {e}")
        return False

def main():
    """Main deployment function"""
    print("🚀 ROSE GMAIL CALENDAR INTEGRATION DEPLOYMENT")
    print("=" * 60)
    
    # Step 1: Create integration files
    files = create_integration_files()
    
    # Step 2: Create setup guide
    guide = create_setup_guide()
    
    # Step 3: Validate environment
    env_valid = validate_environment()
    
    # Step 4: Update assistant (if environment is ready)
    if env_valid and os.getenv('OPENAI_API_KEY'):
        if os.getenv('ROSE_ASSISTANT_ID') or os.getenv('ASSISTANT_ID'):
            assistant_updated = run_assistant_update()
        else:
            print("⚠️ ROSE_ASSISTANT_ID not found - skipping assistant update")
            assistant_updated = False
    else:
        assistant_updated = False
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 DEPLOYMENT SUMMARY")
    print("=" * 60)
    
    print(f"✅ Integration files created: {len(files)} files")
    print(f"✅ Setup guide created: {guide}")
    print(f"{'✅' if env_valid else '❌'} Environment validation: {'Passed' if env_valid else 'Failed'}")
    print(f"{'✅' if assistant_updated else '⚠️'} Assistant update: {'Complete' if assistant_updated else 'Skipped'}")
    
    if assistant_updated:
        print("\n🎉 ROSE GMAIL CALENDAR INTEGRATION COMPLETE!")
        print("\n📝 NEXT STEPS:")
        print("1. Update Rose's main.py with the integration code")
        print("2. Configure Google Cloud service account")
        print("3. Share Gmail calendar with service account")
        print("4. Deploy to Railway")
        print("5. Test with !calendar-status")
    else:
        print("\n📝 NEXT STEPS:")
        print("1. Configure missing environment variables")
        print("2. Run: python rose_direct_work_calendar_integration.py")
        print("3. Follow the setup guide for Google Cloud configuration")
        print("4. Update main.py and deploy to Railway")
    
    print(f"\n📖 Full setup instructions: {guide}")
    print("\n👑 Rose will soon have complete calendar autonomy!")

if __name__ == "__main__":
    main()