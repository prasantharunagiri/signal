from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from app.database import get_db
from app.providers.csv_provider import CSVProvider
from app.backtesting.engine import ChronologicalBacktester
from app.models.schema import BacktestRun, BacktestResult

router = APIRouter(prefix="/api/backtest", tags=["Backtesting"])

class BacktestRequest(BaseModel):
    name: str = "Backtest Run"
    symbol: str = "XAUUSD"
    timeframe: str = "5m"
    strategy_preset: str = "INTRADAY"
    strategy_version: str = "XAU-CONFLUENCE-V1.0"
    start_date: datetime
    end_date: datetime
    min_score: int = 70

from app.api.market import get_provider

@router.post("/run")
def run_backtest_endpoint(req: BacktestRequest, db: Session = Depends(get_db)):
    provider = get_provider()
    backtester = ChronologicalBacktester(provider)

    summary = backtester.run_backtest(
        symbol=req.symbol,
        timeframe=req.timeframe,
        start_date=req.start_date,
        end_date=req.end_date,
        strategy_preset=req.strategy_preset,
        strategy_version=req.strategy_version,
        min_score=req.min_score
    )

    run_record = BacktestRun(
        name=req.name,
        strategy_version=req.strategy_version,
        symbol=req.symbol,
        timeframe=req.timeframe,
        strategy_preset=req.strategy_preset,
        start_date=req.start_date,
        end_date=req.end_date,
        min_score=req.min_score,
        data_source="CSV"
    )
    db.add(run_record)
    db.commit()
    db.refresh(run_record)

    res_record = BacktestResult(
        backtest_id=run_record.id,
        total_signals=summary.total_signals,
        wins=summary.wins,
        losses=summary.losses,
        ambiguous=summary.ambiguous,
        expired=summary.expired,
        win_rate=summary.win_rate,
        avg_r=summary.avg_r,
        total_r=summary.total_r,
        expectancy=summary.expectancy,
        max_drawdown=summary.max_drawdown,
        max_consecutive_losses=summary.max_consecutive_losses,
        profit_factor=summary.profit_factor,
        avg_duration_mins=summary.avg_duration_mins
    )
    db.add(res_record)
    db.commit()

    return summary
