from sqlalchemy import Column, Integer, Date, DateTime
from sqlalchemy.sql import func
from sqlalchemy import ForeignKey, UniqueConstraint
from app.database import Base


class DailyStats(Base):
    __tablename__ = "daily_stats"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False)
    activities_completed = Column(Integer, default=0)
    total_points = Column(Integer, default=0)
    total_time_minutes = Column(Integer, default=0)
    
    # Ensure unique user-date combination
    __table_args__ = (UniqueConstraint('user_id', 'date', name='uq_user_date'),)
    
    def __repr__(self):
        return f"<DailyStats(id={self.id}, user_id={self.user_id}, date={self.date})>" 