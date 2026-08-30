import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db
from app.api import market, signals, backtest, performance, journal, health, websocket, execution

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="XAUUSD Smart Signal Engine Backend API"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(market.router)
app.include_router(signals.router)
app.include_router(backtest.router)
app.include_router(performance.router)
app.include_router(journal.router)
app.include_router(health.router)
app.include_router(websocket.router)
app.include_router(execution.router)

import asyncio
from app.workers.signal_evaluator import start_signal_evaluator_loop, start_live_price_ticker_loop

@app.on_event("startup")
async def startup_event():
    init_db()
    asyncio.create_task(start_signal_evaluator_loop(interval_seconds=60))
    asyncio.create_task(start_live_price_ticker_loop(interval_seconds=1))

@app.get("/")
def root():
    return {
        "app": settings.APP_NAME,
        "environment": settings.ENV,
        "status": "RUNNING",
        "docs_url": "/docs"
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
