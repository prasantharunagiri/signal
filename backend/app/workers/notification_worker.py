import httpx
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.schema import Signal, NotificationLog
from app.config import settings

class NotificationDispatcher:
    def __init__(self):
        self.telegram_bot_token = settings.TELEGRAM_BOT_TOKEN
        self.telegram_chat_id = settings.TELEGRAM_CHAT_ID
        self.discord_webhook_url = settings.DISCORD_WEBHOOK_URL
        self.slack_webhook_url = settings.SLACK_WEBHOOK_URL

    def format_signal_message(self, sig: Signal) -> str:
        icon = "🟡" if sig.direction == "BUY" else "🔴"
        direction_text = "LONG" if sig.direction == "BUY" else "SHORT"

        msg = (
            f"{icon} {sig.symbol} SIGNAL — {sig.strategy_preset}\n\n"
            f"Direction: {direction_text}\n\n"
            f"Entry: {sig.entry_price:.2f}\n"
            f"Stop Loss: {sig.stop_loss:.2f}\n"
            f"TP1: {sig.tp1:.2f}\n"
            f"TP2: {sig.tp2:.2f}\n"
            f"TP3: {sig.tp3:.2f}\n\n"
            f"Score: {sig.score}/100 ({sig.score_grade})\n\n"
            f"Setup: {sig.explanation}\n\n"
            f"Time: {sig.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )
        return msg

    def dispatch_signal_alert(self, db: Session, sig: Signal) -> bool:
        """
        Dispatches alert for a newly created signal ensuring strict single-delivery idempotency.
        """
        # Check if notification log already exists for this signal
        existing = db.query(NotificationLog).filter(NotificationLog.signal_id == sig.id).first()
        if existing:
            return True  # Already dispatched, prevent duplicate alert

        message_text = self.format_signal_message(sig)
        dispatched_any = False

        # Telegram Dispatch
        if self.telegram_bot_token and self.telegram_chat_id:
            try:
                url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
                payload = {
                    "chat_id": self.telegram_chat_id,
                    "text": message_text,
                    "parse_mode": "Markdown"
                }
                res = httpx.post(url, json=payload, timeout=5.0)
                if res.status_code == 200:
                    log = NotificationLog(
                        signal_id=sig.id,
                        channel="TELEGRAM",
                        message_id=str(res.json().get("result", {}).get("message_id")),
                        recipient=self.telegram_chat_id,
                        status="SUCCESS"
                    )
                    db.add(log)
                    dispatched_any = True
            except Exception as e:
                log = NotificationLog(
                    signal_id=sig.id,
                    channel="TELEGRAM",
                    recipient=self.telegram_chat_id,
                    status="FAILED",
                    error_message=str(e)
                )
                db.add(log)

        # Discord Dispatch
        if self.discord_webhook_url:
            try:
                payload = {"content": f"```\n{message_text}\n```"}
                res = httpx.post(self.discord_webhook_url, json=payload, timeout=5.0)
                if res.status_code in [200, 204]:
                    log = NotificationLog(
                        signal_id=sig.id,
                        channel="DISCORD",
                        recipient=self.discord_webhook_url,
                        status="SUCCESS"
                    )
                    db.add(log)
                    dispatched_any = True
            except Exception as e:
                pass

        if dispatched_any:
            db.commit()

        return dispatched_any

    def dispatch_execution_failure(self, db: Session, error_message: str, signal: Optional[Signal] = None) -> bool:
        """
        Dispatches alert for a failed live execution order.
        """
        icon = "⚠️"
        msg = f"{icon} **EXECUTION FAILURE**\n\n"
        
        if signal:
            msg += f"Signal: {signal.symbol} {signal.direction} ({signal.strategy_preset})\n"
        
        msg += f"Error: {error_message}\n\n"
        msg += f"Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"

        dispatched_any = False

        # Telegram Dispatch
        if self.telegram_bot_token and self.telegram_chat_id:
            try:
                url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
                payload = {
                    "chat_id": self.telegram_chat_id,
                    "text": msg,
                    "parse_mode": "Markdown"
                }
                res = httpx.post(url, json=payload, timeout=5.0)
                if res.status_code == 200:
                    dispatched_any = True
            except Exception:
                pass

        # Discord Dispatch
        if self.discord_webhook_url:
            try:
                payload = {"content": f"```\n{msg}\n```"}
                res = httpx.post(self.discord_webhook_url, json=payload, timeout=5.0)
                if res.status_code in [200, 204]:
                    dispatched_any = True
            except Exception:
                pass

        return dispatched_any
