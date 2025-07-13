#!/usr/bin/env python3
"""
Aggressive fix script to clear all daily stats and recalculate from scratch.
This will fix any data inconsistencies by starting fresh.
"""

import sys
import os
from datetime import date
from sqlalchemy import func

# Add the app directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import get_db
from app.models.user import User
from app.models.activity import ActivitySession
from app.models.scoring import ActivityScore
from app.models.daily_stats import DailyStats

def clear_and_recalculate_all_stats():
    """Clear all daily stats and recalculate from actual scored activities"""
    print("🧹 Clearing and recalculating all daily stats...")
    
    db = next(get_db())
    
    try:
        # Get all users
        users = db.query(User).all()
        print(f"Found {len(users)} users")
        
        for user in users:
            print(f"\n👤 Processing user: {user.name} (ID: {user.id})")
            
            # Get all scored activities for this user
            scored_activities = db.query(ActivitySession).join(ActivityScore).filter(
                ActivitySession.user_id == user.id,
                ActivitySession.status == "scored"
            ).all()
            
            print(f"  📊 Found {len(scored_activities)} scored activities")
            
            # Group activities by date
            activities_by_date = {}
            for activity in scored_activities:
                activity_date = activity.created_at.date() if activity.created_at else date.today()
                if activity_date not in activities_by_date:
                    activities_by_date[activity_date] = []
                activities_by_date[activity_date].append(activity)
            
            # Delete all existing daily stats for this user
            deleted_count = db.query(DailyStats).filter(DailyStats.user_id == user.id).delete()
            print(f"  🗑️  Deleted {deleted_count} existing daily stats entries")
            
            # Create new daily stats based on actual scored activities
            total_points = 0
            for activity_date, activities in activities_by_date.items():
                daily_points = 0
                daily_time = 0
                
                for activity in activities:
                    score_record = db.query(ActivityScore).filter(ActivityScore.session_id == activity.id).first()
                    if score_record:
                        daily_points += score_record.score
                        daily_time += activity.actual_duration or 0
                
                # Create new daily stats entry
                new_stats = DailyStats(
                    user_id=user.id,
                    date=activity_date,
                    activities_completed=len(activities),
                    total_points=daily_points,
                    total_time_minutes=daily_time
                )
                db.add(new_stats)
                
                total_points += daily_points
                print(f"    📅 {activity_date}: {len(activities)} activities, {daily_points} points")
            
            # Commit changes
            db.commit()
            print(f"  ✅ Total points after fix: {total_points}")
        
        print("\n✅ All daily stats have been cleared and recalculated!")
        
        # Show final results
        print("\n📊 Final Results:")
        for user in users:
            print(f"\n👤 {user.name}:")
            
            # Get total scored activities
            total_scored = db.query(ActivitySession).filter(
                ActivitySession.user_id == user.id,
                ActivitySession.status == "scored"
            ).count()
            
            # Get total points from daily stats
            total_points = db.query(func.coalesce(func.sum(DailyStats.total_points), 0)).filter(
                DailyStats.user_id == user.id
            ).scalar()
            
            print(f"  📈 Scored activities: {total_scored}")
            print(f"  ⚡ Total Summer Charger Points: {total_points}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("🧹 Aggressive Daily Stats Fixer")
    print("=" * 50)
    print("⚠️  This will DELETE all existing daily stats and recalculate from scratch!")
    print("⚠️  Only scored activities will be counted in the new totals.")
    print("=" * 50)
    
    response = input("\nDo you want to proceed? (y/N): ")
    if response.lower() in ['y', 'yes']:
        clear_and_recalculate_all_stats()
    else:
        print("❌ Cancelled.") 