from app.database import SessionLocal
from app.models.schema import SystemLog
db = SessionLocal()
logs = db.query(SystemLog).order_by(SystemLog.timestamp.desc()).limit(20).all()
for s in logs:
    print(s.timestamp, s.level, s.component, s.message)
