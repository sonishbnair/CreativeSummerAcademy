#!/usr/bin/env python3
"""
Test script to verify timer extension functionality.
This script helps test the Hybrid Approach implementation.
"""

import sys
import os
from datetime import datetime, timedelta

# Add the app directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import get_db
from app.models.user import User
from app.models.activity import ActivitySession
from app.services.activity_service import ActivityService

def test_timer_extension():
    """Test the timer extension functionality"""
    print("🧪 Testing Timer Extension Functionality")
    print("=" * 50)
    
    db = next(get_db())
    
    try:
        # Get the first user (Sreya)
        user = db.query(User).first()
        if not user:
            print("❌ No users found in database")
            return
        
        print(f"👤 Testing with user: {user.name} (ID: {user.id})")
        
        # Get the most recent active activity
        session = db.query(ActivitySession).filter(
            ActivitySession.user_id == user.id,
            ActivitySession.status == "active"
        ).order_by(ActivitySession.created_at.desc()).first()
        
        if not session:
            print("❌ No active activity found")
            print("💡 Please start an activity first")
            return
        
        print(f"📊 Activity Session: {session.id}")
        print(f"   - Selected Duration: {session.selected_duration} minutes")
        print(f"   - Extensions Used: {session.extensions_used}")
        print(f"   - Max Possible Score: {session.max_possible_score}")
        print(f"   - Start Time: {session.start_time}")
        
        if session.start_time:
            elapsed = datetime.utcnow() - session.start_time
            elapsed_minutes = int(elapsed.total_seconds() / 60)
            remaining_minutes = max(0, session.selected_duration - elapsed_minutes)
            
            print(f"   - Elapsed Time: {elapsed_minutes} minutes")
            print(f"   - Remaining Time: {remaining_minutes} minutes")
            
            if remaining_minutes <= 0:
                print("✅ Timer has reached zero - extension should be available!")
            else:
                print(f"⏰ Timer still running - {remaining_minutes} minutes remaining")
        else:
            print("⚠️  No start time recorded")
        
        # Test extension functionality
        activity_service = ActivityService()
        
        print(f"\n🔧 Testing Extension API...")
        result = activity_service.extend_activity(db, session.id)
        
        if result["success"]:
            print(f"✅ Extension successful!")
            print(f"   - New extensions used: {result['extensions_used']}")
            print(f"   - New max possible score: {result['max_possible_score']}")
        else:
            print(f"❌ Extension failed: {result['error']}")
        
        # Refresh session data
        db.refresh(session)
        print(f"\n📊 Updated Session Data:")
        print(f"   - Extensions Used: {session.extensions_used}")
        print(f"   - Max Possible Score: {session.max_possible_score}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

def show_test_instructions():
    """Show instructions for testing the timer extension"""
    print("📋 Testing Instructions")
    print("=" * 50)
    print("1. Start the application:")
    print("   uv run uvicorn app.main:app --reload")
    print()
    print("2. Create a 1-minute activity:")
    print("   - Go to activity setup")
    print("   - Select 1 minute duration")
    print("   - Complete the setup")
    print()
    print("3. Start the activity and wait 1 minute")
    print("4. When timer hits 00:00, extension button should appear automatically")
    print("5. Click extension button - timer should reset to 5:00 immediately")
    print("6. No page refresh should be needed!")
    print()
    print("7. After testing, restore original config:")
    print("   - Change min_activity_duration back to 10")
    print("   - Change max_activity_duration back to 30")
    print("   - Change duration_increment back to 5")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_timer_extension()
    else:
        show_test_instructions() 