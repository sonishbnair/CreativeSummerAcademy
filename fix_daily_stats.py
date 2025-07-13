#!/usr/bin/env python3
"""
Utility script to recalculate daily stats for all users.
This fixes any inconsistencies in Summer Charger Points after deleting activities.
"""

import sys
import os
from datetime import date, timedelta
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

# Add the app directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import get_db
from app.models.user import User
from app.models.activity import ActivitySession
from app.models.scoring import ActivityScore
from app.models.daily_stats import DailyStats
from app.services.scoring_service import ScoringService

def recalculate_all_daily_stats():
    """Recalculate daily stats for all users"""
    print("🔧 Recalculating daily stats for all users...")
    
    # Get database session
    db = next(get_db())
    
    try:
        # Get all users
        users = db.query(User).all()
        print(f"Found {len(users)} users")
        
        scoring_service = ScoringService()
        
        for user in users:
            print(f"\n👤 Processing user: {user.name} (ID: {user.id})")
            
            # Get all unique dates where this user has scored activities
            scored_dates = db.query(func.date(ActivitySession.created_at)).join(ActivityScore).filter(
                ActivitySession.user_id == user.id,
                ActivitySession.status == "scored"
            ).distinct().all()
            
            if not scored_dates:
                print(f"  ⚠️  No scored activities found for {user.name}")
                continue
            
            print(f"  📅 Found {len(scored_dates)} days with scored activities")
            
            # Recalculate stats for each date
            for (activity_date,) in scored_dates:
                if activity_date:
                    # Convert string date to date object if needed
                    if isinstance(activity_date, str):
                        activity_date = date.fromisoformat(activity_date)
                    stats = scoring_service.recalculate_daily_stats(db, user.id, activity_date)
                    print(f"    📊 {activity_date}: {stats['activities_completed']} activities, {stats['total_points']} points")
            
            # Also recalculate today's stats
            today_stats = scoring_service.recalculate_daily_stats(db, user.id)
            print(f"    📊 Today: {today_stats['activities_completed']} activities, {today_stats['total_points']} points")
        
        print("\n✅ Daily stats recalculation completed!")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        db.rollback()
    finally:
        db.close()

def show_current_stats():
    """Show current daily stats for all users"""
    print("📊 Current daily stats for all users:")
    
    db = next(get_db())
    
    try:
        users = db.query(User).all()
        
        for user in users:
            print(f"\n👤 {user.name} (ID: {user.id}):")
            
            # Get today's stats
            today_stats = db.query(DailyStats).filter(
                DailyStats.user_id == user.id,
                DailyStats.date == date.today()
            ).first()
            
            if today_stats:
                print(f"  📅 Today: {today_stats.activities_completed} activities, {today_stats.total_points} points")
            else:
                print(f"  📅 Today: No stats found")
            
            # Get total scored activities
            total_scored = db.query(ActivitySession).filter(
                ActivitySession.user_id == user.id,
                ActivitySession.status == "scored"
            ).count()
            
            print(f"  📈 Total scored activities: {total_scored}")
            
            # Get total points across all days
            total_points = db.query(func.coalesce(func.sum(DailyStats.total_points), 0)).filter(
                DailyStats.user_id == user.id
            ).scalar()
            
            print(f"  ⚡ Total Summer Charger Points: {total_points}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "show":
        show_current_stats()
    else:
        print("🔧 Summer Charger Points Daily Stats Fixer")
        print("=" * 50)
        
        # Show current stats first
        show_current_stats()
        
        print("\n" + "=" * 50)
        
        # Ask for confirmation
        response = input("\nDo you want to recalculate all daily stats? (y/N): ")
        if response.lower() in ['y', 'yes']:
            recalculate_all_daily_stats()
            
            print("\n" + "=" * 50)
            print("📊 Updated stats:")
            show_current_stats()
        else:
            print("❌ Cancelled.") 