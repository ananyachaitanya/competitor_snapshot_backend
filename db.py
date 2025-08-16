from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import json
from sqlalchemy.orm import Session
from models import Snapshot

Base = declarative_base()

class Snapshot(Base):
    __tablename__ = "snapshots"
    id = Column(Integer, primary_key=True)
    domain = Column(String, index=True)
    url = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    homepage_title = Column(String)
    homepage_h1 = Column(String)
    feed_items_json = Column(Text)  # JSON list
    text_bundle = Column(Text)
    heat_score = Column(Integer)
    sentiment_compound = Column(String)
    sentiment_label = Column(String)
    diffs_json = Column(Text)       # JSON list
    keywords_json = Column(Text)    # JSON list

engine = create_engine("sqlite:///snapshots.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def save_snapshot_obj(snap):
    sess = SessionLocal()
    s = Snapshot(
        domain=snap["domain"],
        url=snap["url"],
        homepage_title=snap["homepage"].get("title",""),
        homepage_h1=snap["homepage"].get("h1",""),
        feed_items_json=json.dumps(snap.get("feed_items",[])),
        text_bundle=snap.get("text_bundle",""),
        heat_score=snap.get("heat",0),
        sentiment_compound=str(snap.get("sentiment",{}).get("compound","0")),
        sentiment_label=snap.get("sentiment",{}).get("label","neutral"),
        diffs_json=json.dumps(snap.get("diffs",[])),
        keywords_json=json.dumps(snap.get("keywords",[]))
    )
    sess.add(s)
    sess.commit()
    snapshot_id = s.id
    sess.close()
    return snapshot_id

def get_latest_snapshot(domain):
    sess = SessionLocal()
    s = sess.query(Snapshot).filter_by(domain=domain).order_by(Snapshot.timestamp.desc()).first()
    sess.close()
    return s

def get_previous_snapshot(domain):
    sess = SessionLocal()
    s = sess.query(Snapshot).filter_by(domain=domain).order_by(Snapshot.timestamp.desc()).limit(2).all()
    sess.close()
    if len(s) == 2:
        return s[1]
    return None

def list_domains():
    sess = SessionLocal()
    rows = sess.query(Snapshot.domain).distinct().all()
    sess.close()
    return [r[0] for r in rows]

def delete_domain_from_db(domain: str):
    db: Session = SessionLocal()
    try:
        snapshots = db.query(Snapshot).filter(Snapshot.domain == domain).all()
        if not snapshots:
            return False
        for snap in snapshots:
            db.delete(snap)
        db.commit()
        return True
    finally:
        db.close()