#!/usr/bin/env python3
"""
Test script to reset weekly reimbursement status for testing Friday reset functionality.
"""

from app.database import SessionLocal
from app.models.reimbursement import WeeklyReimbursementStatus
from app.models.user import User
from datetime import datetime, timedelta


def list_users():
    """List all users in the database"""
    db = SessionLocal()
    users = db.query(User).all()
    print("\n=== Available Users ===")
    for user in users:
        print(f"User ID: {user.id}, Name: {user.name}")
    db.close()
    return users


def check_weekly_status(user_id):
    """Check current weekly status for a user"""
    db = SessionLocal()
    status = db.query(WeeklyReimbursementStatus).filter(
        WeeklyReimbursementStatus.user_id == user_id
    ).first()
    
    if status:
        print(f"\n=== Current Weekly Status for User {user_id} ===")
        print(f"Week Start Date: {status.week_start_date}")
        print(f"Can Reimburse: {status.can_reimburse}")
        print(f"Last Reimbursement: {status.last_reimbursement_date}")
    else:
        print(f"\n=== No Weekly Status Found for User {user_id} ===")
        print("User can reimburse (no restrictions)")
    
    db.close()
    return status


def reset_weekly_status(user_id):
    """Reset weekly status for a user (simulate Friday reset)"""
    db = SessionLocal()
    
    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        print(f"❌ User {user_id} not found!")
        db.close()
        return False
    
    # Delete weekly status for the user
    deleted = db.query(WeeklyReimbursementStatus).filter(
        WeeklyReimbursementStatus.user_id == user_id
    ).delete()
    
    db.commit()
    db.close()
    
    if deleted > 0:
        print(f"✅ Weekly status reset for user {user_id} ({user.name})")
        print("   You can now reimburse again!")
    else:
        print(f"ℹ️  No weekly status found for user {user_id} ({user.name})")
        print("   User can already reimburse")
    
    return True


def reset_all_weekly_status():
    """Reset weekly status for all users"""
    db = SessionLocal()
    deleted = db.query(WeeklyReimbursementStatus).delete()
    db.commit()
    db.close()
    
    print(f"✅ Reset weekly status for all users ({deleted} records deleted)")
    print("   All users can now reimburse again!")


def main():
    """Main function with interactive menu"""
    print("🔄 Weekly Reimbursement Status Reset Tool")
    print("==========================================")
    
    while True:
        print("\nOptions:")
        print("1. List all users")
        print("2. Check weekly status for a user")
        print("3. Reset weekly status for a user")
        print("4. Reset weekly status for all users")
        print("5. Exit")
        
        choice = input("\nEnter your choice (1-5): ").strip()
        
        if choice == "1":
            list_users()
            
        elif choice == "2":
            user_id = input("Enter user ID: ").strip()
            try:
                check_weekly_status(int(user_id))
            except ValueError:
                print("❌ Invalid user ID")
                
        elif choice == "3":
            user_id = input("Enter user ID: ").strip()
            try:
                reset_weekly_status(int(user_id))
            except ValueError:
                print("❌ Invalid user ID")
                
        elif choice == "4":
            confirm = input("Are you sure you want to reset ALL users? (y/N): ").strip().lower()
            if confirm == 'y':
                reset_all_weekly_status()
            else:
                print("Operation cancelled")
                
        elif choice == "5":
            print("👋 Goodbye!")
            break
            
        else:
            print("❌ Invalid choice. Please enter 1-5.")


if __name__ == "__main__":
    main() 