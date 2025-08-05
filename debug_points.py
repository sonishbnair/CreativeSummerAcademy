#!/usr/bin/env python3
"""
Debug script to check points calculation and database state.
"""

from app.database import SessionLocal
from app.models.daily_stats import DailyStats
from app.models.reimbursement import ReimbursementHistory
from app.models.user import User
from sqlalchemy import func
from datetime import datetime


def debug_user_points(user_id):
    """Debug points calculation for a user"""
    db = SessionLocal()
    
    print(f"\n=== Debug Points for User {user_id} ===")
    
    # Get user info
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        print(f"❌ User {user_id} not found!")
        return
    
    print(f"User: {user.name}")
    
    # Get all daily stats entries
    daily_stats = db.query(DailyStats).filter(
        DailyStats.user_id == user_id
    ).order_by(DailyStats.date).all()
    
    print(f"\n📊 Daily Stats Entries ({len(daily_stats)} total):")
    total_points = 0
    for stat in daily_stats:
        print(f"  {stat.date}: {stat.total_points} points (activities: {stat.activities_completed})")
        total_points += stat.total_points
    
    print(f"\n💰 Calculated Total: {total_points}")
    
    # Get reimbursement history
    reimbursements = db.query(ReimbursementHistory).filter(
        ReimbursementHistory.user_id == user_id
    ).order_by(ReimbursementHistory.redeemed_at.desc()).all()
    
    print(f"\n🎁 Reimbursement History ({len(reimbursements)} total):")
    total_spent = 0
    for reimb in reimbursements:
        print(f"  {reimb.redeemed_at.strftime('%Y-%m-%d %H:%M')}: {reimb.item_name} ({reimb.points_cost} points)")
        total_spent += reimb.points_cost
    
    print(f"\n💸 Total Spent on Reimbursements: {total_spent}")
    
    # Calculate what the total should be
    original_points = sum([stat.total_points for stat in daily_stats if stat.total_points > 0])
    deducted_points = sum([abs(stat.total_points) for stat in daily_stats if stat.total_points < 0])
    expected_total = original_points - deducted_points
    
    print(f"\n🧮 Expected Calculation:")
    print(f"  Original Points: {original_points}")
    print(f"  Deducted Points: {deducted_points}")
    print(f"  Expected Total: {original_points} - {deducted_points} = {expected_total}")
    
    db.close()


def list_all_users():
    """List all users"""
    db = SessionLocal()
    users = db.query(User).all()
    print("\n=== Available Users ===")
    for user in users:
        print(f"User ID: {user.id}, Name: {user.name}")
    db.close()


def main():
    """Main function"""
    print("🔍 Points Debug Tool")
    print("===================")
    
    list_all_users()
    
    user_id = input("\nEnter user ID to debug: ").strip()
    try:
        debug_user_points(int(user_id))
    except ValueError:
        print("❌ Invalid user ID")


if __name__ == "__main__":
    main() 