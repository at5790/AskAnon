# defines databse tables 
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from .database import Base


class ClassSession(Base):
    __tablename__ = "class_sessions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    join_code = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    questions = relationship("Question", back_populates="session")


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text, nullable=False)
    upvotes = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    session_id = Column(Integer, ForeignKey("class_sessions.id"))

    session = relationship("ClassSession", back_populates="questions")