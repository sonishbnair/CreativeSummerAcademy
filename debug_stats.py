#!/usr/bin/env python3
"""
Debug script to examine database contents and understand point calculation issues.
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

def debug_database_contents():
    """Examine all database contents to understand the issue"""
    print("🔍 Debugging Database Contents")
    print("=" * 50)
    
    db = next(get_db())
    
    try:
        # Get all users
        users = db.query(User).all()
        
        for user in users:
            print(f"\n👤 User: {user.name} (ID: {user.id})")
            
            # Get all activities for this user
            all_activities = db.query(ActivitySession).filter(
                ActivitySession.user_id == user.id
            ).order_by(ActivitySession.created_at).all()
            
            print(f"  📊 Total activities: {len(all_activities)}")
            
            # Count by status
            status_counts = {}
            for activity in all_activities:
                status = activity.status
                status_counts[status] = status_counts.get(status, 0) + 1
            
            print(f"  📈 Activities by status:")
            for status, count in status_counts.items():
                print(f"    - {status}: {count}")
            
            # Show detailed activity info
            print(f"  📋 Detailed activity breakdown:")
            for i, activity in enumerate(all_activities, 1):
                score_record = db.query(ActivityScore).filter(ActivityScore.session_id == activity.id).first()
                score = score_record.score if score_record else "Not scored"
                created_date = activity.created_at.date() if activity.created_at else "Unknown"
                
                print(f"    {i}. ID: {activity.id}, Status: {activity.status}, Date: {created_date}, Score: {score}")
                if activity.generated_activity and activity.generated_activity.get('title'):
                    print(f"       Title: {activity.generated_activity['title']}")
            
            # Get daily stats
            print(f"  📅 Daily stats:")
            daily_stats = db.query(DailyStats).filter(DailyStats.user_id == user.id).all()
            for stats in daily_stats:
                print(f"    - {stats.date}: {stats.activities_completed} activities, {stats.total_points} points")
            
            # Calculate what the total should be
            total_scored_activities = db.query(ActivitySession).filter(
                ActivitySession.user_id == user.id,
                ActivitySession.status == "scored"
            ).count()
            
            total_points_from_scores = db.query(func.coalesce(func.sum(ActivityScore.score), 0)).join(ActivitySession).filter(
                ActivitySession.user_id == user.id,
                ActivitySession.status == "scored"
            ).scalar()
            
            total_points_from_daily_stats = db.query(func.coalesce(func.sum(DailyStats.total_points), 0)).filter(
                DailyStats.user_id == user.id
            ).scalar()
            
            print(f"  🔢 Summary:")
            print(f"    - Scored activities: {total_scored_activities}")
            print(f"    - Total points from scores: {total_points_from_scores}")
            print(f"    - Total points from daily stats: {total_points_from_daily_stats}")
            
            if total_points_from_scores != total_points_from_daily_stats:
                print(f"    ⚠️  MISMATCH DETECTED!")
                print(f"    - Difference: {total_points_from_daily_stats - total_points_from_scores}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    debug_database_contents() 