import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # System & Environment
    APP_NAME: str = "XAUUSD Smart Signal Engine"
    ENV: str = "development"  # development, production, test
    DATABASE_URL: str = "sqlite:///./xauusd_engine.db"
    SECRET_KEY: str = "super-secret-key-change-in-production"

    # Data Provider Settings
    MARKET_DATA_PROVIDER: str = "csv"  # csv, demo, mt5, twelvedata
    TWELVEDATA_API_KEY: Optional[str] = None
    MT5_LOGIN: Optional[str] = None
    MT5_PASSWORD: Optional[str] = None
    MT5_SERVER: Optional[str] = None
    MT5_BRIDGE_URL: Optional[str] = "http://localhost:9000"  # Windows VPS bridge address

    # Telegram / Notification Settings
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None
    DISCORD_WEBHOOK_URL: Optional[str] = None
    SLACK_WEBHOOK_URL: Optional[str] = None

    # Strategy Parameters (Configurable Defaults)
    SWING_LOOKBACK_N: int = 2
    EQUAL_HIGH_LOW_TOLERANCE_PIPS: float = 0.5  # Pips tolerance for equal highs/lows
    DISPLACEMENT_BODY_RATIO_MIN: float = 0.60   # Body/Range ratio minimum (60%)
    DISPLACEMENT_ATR_MULTIPLE: float = 1.2      # Candle range vs ATR(14)
    FVG_MIN_SIZE_PIPS: float = 0.3              # Minimum size of FVG in pips ($0.30 Gold)
    SL_BUFFER_PIPS: float = 1.0                 # SL buffer in pips ($1.00 Gold)

    # Strategy Scoring Thresholds
    SCORE_THRESHOLD_A_PLUS: int = 90
    SCORE_THRESHOLD_A: int = 80
    SCORE_THRESHOLD_B: int = 70

    # News Filter Blackout Windows (Minutes)
    NEWS_BLACKOUT_BEFORE_MINS: int = 30
    NEWS_BLACKOUT_AFTER_MINS: int = 30

    # Stale Data Threshold (Seconds)
    STALE_DATA_TIMEOUT_SECONDS: int = 600

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
