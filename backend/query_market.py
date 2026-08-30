from app.database import SessionLocal
from app.models.schema import MarketData
db = SessionLocal()
candles = db.query(MarketData).order_by(MarketData.timestamp.desc()).limit(5).all()
for c in candles:
    print(c.timestamp, c.symbol, c.timeframe, c.close)
