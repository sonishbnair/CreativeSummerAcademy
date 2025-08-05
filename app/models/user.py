from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships for reimbursement tracking
    reimbursements = relationship("ReimbursementHistory", back_populates="user")
    weekly_reimbursement_status = relationship("WeeklyReimbursementStatus", back_populates="user")
    point_deductions = relationship("PointDeduction", back_populates="user")
    
    def __repr__(self):
        return f"<User(id={self.id}, name='{self.name}')>" 