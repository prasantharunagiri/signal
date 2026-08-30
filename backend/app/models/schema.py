from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from app.database import Base

class MarketData(Base):
    __tablename__ = "market_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    timeframe = Column(String(10), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, default=0.0)
    is_demo = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("symbol", "timeframe", "timestamp", "is_demo", name="uq_market_data_candle"),
        Index("idx_market_data_lookup", "symbol", "timeframe", "timestamp"),
    )


class LiquidityLevel(Base):
    __tablename__ = "liquidity_levels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    timeframe = Column(String(10), nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    level_type = Column(String(30), nullable=False)  # PDH, PDL, PSH, PSL, SESSION_HIGH, SESSION_LOW, EQUAL_HIGH, EQUAL_LOW, SWING_HIGH, SWING_LOW
    price = Column(Float, nullable=False)
    session = Column(String(30), nullable=True)     # Asian, London, New York, Overlap
    is_confirmed = Column(Boolean, default=True)
    is_demo = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class LiquiditySweep(Base):
    __tablename__ = "liquidity_sweeps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False)
    timeframe = Column(String(10), nullable=False)
    sweep_time = Column(DateTime, nullable=False, index=True)
    liquidity_type = Column(String(30), nullable=False)
    liquidity_level_price = Column(Float, nullable=False)
    sweep_price = Column(Float, nullable=False)
    reclaim_price = Column(Float, nullable=False)
    reclaim_time = Column(DateTime, nullable=False)
    sweep_distance = Column(Float, nullable=False)
    direction = Column(String(10), nullable=False)  # BULLISH, BEARISH
    is_demo = Column(Boolean, default=False, nullable=False)


class DivergenceEvent(Base):
    __tablename__ = "divergence_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False)
    comparison_symbol = Column(String(20), nullable=False, default="DXY")
    timeframe = Column(String(10), nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    divergence_type = Column(String(20), nullable=False)  # BULLISH, BEARISH, NONE
    primary_high_low = Column(Float, nullable=False)
    comparison_high_low = Column(Float, nullable=False)
    is_demo = Column(Boolean, default=False, nullable=False)


class StructureEvent(Base):
    __tablename__ = "structure_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False)
    timeframe = Column(String(10), nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    event_type = Column(String(20), nullable=False)  # MSS_BULLISH, MSS_BEARISH
    broken_level = Column(Float, nullable=False)
    break_price = Column(Float, nullable=False)
    is_demo = Column(Boolean, default=False, nullable=False)


class FVGEvent(Base):
    __tablename__ = "fvg_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False)
    timeframe = Column(String(10), nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    fvg_type = Column(String(10), nullable=False)  # BULLISH, BEARISH
    fvg_high = Column(Float, nullable=False)
    fvg_low = Column(Float, nullable=False)
    fvg_size = Column(Float, nullable=False)
    filled = Column(Boolean, default=False)
    filled_at = Column(DateTime, nullable=True)
    is_demo = Column(Boolean, default=False, nullable=False)


class Signal(Base):
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    signal_key = Column(String(100), nullable=False, unique=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    timeframe = Column(String(10), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    direction = Column(String(10), nullable=False)  # BUY, SELL
    strategy_preset = Column(String(20), nullable=False, default="INTRADAY", index=True)  # SCALP, INTRADAY, SWING
    strategy_version = Column(String(30), nullable=False, default="XAU-CONFLUENCE-V1.0")
    score = Column(Integer, nullable=False)
    score_grade = Column(String(5), nullable=False)  # A+, A, B
    entry_price = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=False)
    tp1 = Column(Float, nullable=False)
    tp2 = Column(Float, nullable=False)
    tp3 = Column(Float, nullable=False)
    risk_distance = Column(Float, nullable=False)
    reward_tp1 = Column(Float, nullable=False)
    reward_tp2 = Column(Float, nullable=False)
    reward_tp3 = Column(Float, nullable=False)
    session = Column(String(30), nullable=True)
    liquidity_type = Column(String(50), nullable=True)
    liquidity_level = Column(Float, nullable=True)
    smt_status = Column(Boolean, default=False)
    mss_status = Column(Boolean, default=False)
    displacement_status = Column(Boolean, default=False)
    fvg_status = Column(Boolean, default=False)
    news_status = Column(String(30), default="NORMAL")  # NORMAL, NEWS_BLACKOUT, EXCLUDED_NEWS
    data_quality_status = Column(String(30), default="VALID")  # VALID, REJECTED_DATA
    status = Column(String(20), nullable=False, default="OPEN", index=True)  # OPEN, TP1_HIT, TP2_HIT, TP3_HIT, SL_HIT, EXPIRED, AMBIGUOUS
    explanation = Column(Text, nullable=True)
    is_demo = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    events = relationship("SignalEvent", back_populates="signal", cascade="all, delete-orphan")


class SignalEvent(Base):
    __tablename__ = "signal_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    signal_id = Column(Integer, ForeignKey("signals.id"), nullable=False, index=True)
    event_type = Column(String(30), nullable=False)  # SIGNAL_CREATED, TP1_HIT, TP2_HIT, TP3_HIT, SL_HIT, EXPIRED, AMBIGUOUS
    price = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    details = Column(Text, nullable=True)

    signal = relationship("Signal", back_populates="events")


class BacktestRun(Base):
    __tablename__ = "backtest_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    strategy_version = Column(String(30), nullable=False)
    symbol = Column(String(20), nullable=False)
    timeframe = Column(String(10), nullable=False)
    strategy_preset = Column(String(20), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    min_score = Column(Integer, nullable=False, default=70)
    data_source = Column(String(50), nullable=False, default="CSV")
    parameters_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    results = relationship("BacktestResult", back_populates="backtest_run", uselist=False, cascade="all, delete-orphan")


class BacktestResult(Base):
    __tablename__ = "backtest_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    backtest_id = Column(Integer, ForeignKey("backtest_runs.id"), nullable=False, unique=True)
    total_signals = Column(Integer, nullable=False, default=0)
    wins = Column(Integer, nullable=False, default=0)
    losses = Column(Integer, nullable=False, default=0)
    ambiguous = Column(Integer, nullable=False, default=0)
    expired = Column(Integer, nullable=False, default=0)
    win_rate = Column(Float, nullable=False, default=0.0)
    avg_r = Column(Float, nullable=False, default=0.0)
    total_r = Column(Float, nullable=False, default=0.0)
    expectancy = Column(Float, nullable=False, default=0.0)
    max_drawdown = Column(Float, nullable=False, default=0.0)
    max_consecutive_losses = Column(Integer, nullable=False, default=0)
    profit_factor = Column(Float, nullable=False, default=0.0)
    avg_duration_mins = Column(Float, nullable=False, default=0.0)

    backtest_run = relationship("BacktestRun", back_populates="results")


class NewsEvent(Base):
    __tablename__ = "news_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_name = Column(String(100), nullable=False)
    currency = Column(String(10), nullable=False, default="USD")
    impact = Column(String(10), nullable=False, default="HIGH")  # HIGH, MEDIUM, LOW
    event_time = Column(DateTime, nullable=False, index=True)
    blackout_start = Column(DateTime, nullable=False)
    blackout_end = Column(DateTime, nullable=False)


class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    signal_id = Column(Integer, ForeignKey("signals.id"), nullable=False, index=True)
    channel = Column(String(20), nullable=False)  # TELEGRAM, DISCORD, SLACK, WEBHOOK
    message_id = Column(String(100), nullable=True)
    recipient = Column(String(100), nullable=True)
    sent_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), nullable=False, default="SUCCESS")  # SUCCESS, FAILED
    error_message = Column(Text, nullable=True)


class SystemLog(Base):
    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    level = Column(String(10), nullable=False, default="INFO")  # INFO, WARNING, ERROR
    component = Column(String(30), nullable=False)  # MARKET_DATA, SIGNAL_ENGINE, OUTCOME_ENGINE, NEWS_ENGINE, WATCHDOG
    message = Column(Text, nullable=False)


class TradeExecution(Base):
    __tablename__ = "trade_executions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(String(100), nullable=False, unique=True, index=True)
    signal_id = Column(Integer, ForeignKey("signals.id"), nullable=True, index=True)
    symbol = Column(String(20), nullable=False)
    direction = Column(String(10), nullable=False)  # BUY, SELL
    order_type = Column(String(20), nullable=False, default="MARKET")
    execution_mode = Column(String(20), nullable=False, default="PAPER")  # PAPER, MT5
    lot_size = Column(Float, nullable=False, default=0.1)
    entry_price = Column(Float, nullable=False)
    fill_price = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=False)
    take_profit = Column(Float, nullable=False)
    status = Column(String(20), nullable=False, default="FILLED", index=True)  # FILLED, CLOSED, CANCELLED, REJECTED, FAILED
    error_message = Column(Text, nullable=True)
    close_price = Column(Float, nullable=True)
    pnl = Column(Float, nullable=False, default=0.0)
    executed_at = Column(DateTime, default=datetime.utcnow, index=True)
    closed_at = Column(DateTime, nullable=True)

