# backend/models.py
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Snapshot(Base):
    __tablename__ = "snapshots"

    id = Column(Integer, primary_key=True, index=True)
    domain = Column(String, index=True)
    data = Column(String)  # store JSON as string if not using JSON type
    created_at = Column(DateTime, default=datetime.utcnow)
