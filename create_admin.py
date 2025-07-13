#!/usr/bin/env python3
"""
Script to create an admin user for the Creative Summer Academy
Run this script to create the admin user with password 'admin123'
"""

import bcrypt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.parent import Parent
from app.database import Base

# Database URL - adjust if needed
DATABASE_URL = "sqlite:///./galactic_academy.db"

def create_admin_user():
    """Create admin user in the database"""
    
    # Create engine and session
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Check if admin already exists
        existing_admin = db.query(Parent).filter(Parent.name == "admin").first()
        
        if existing_admin:
            print("✅ Admin user already exists!")
            print(f"   ID: {existing_admin.id}")
            print(f"   Name: {existing_admin.name}")
            print(f"   Created: {existing_admin.created_at}")
            return
        
        # Create admin user
        password = "admin123"
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        admin = Parent(
            name="admin",
            password_hash=password_hash.decode('utf-8')
        )
        
        db.add(admin)
        db.commit()
        db.refresh(admin)
        
        print("✅ Admin user created successfully!")
        print(f"   ID: {admin.id}")
        print(f"   Name: {admin.name}")
        print(f"   Password: {password}")
        print(f"   Created: {admin.created_at}")
        print("\n🔐 Login credentials:")
        print(f"   Username: admin")
        print(f"   Password: {password}")
        
    except Exception as e:
        print(f"❌ Error creating admin user: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 Creating admin user for Creative Summer Academy...")
    create_admin_user()
    print("\n✨ Done! You can now login as admin to access user management.") 