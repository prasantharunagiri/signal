from app.database import SessionLocal
from app.models.schema import Signal
db = SessionLocal()
signals = db.query(Signal).order_by(Signal.timestamp.desc()).limit(5).all()
for s in signals:
    print(s.timestamp, s.symbol, s.direction, s.score)
