import json
import os
import time
from typing import Optional
from app.providers.ea_push_provider import EAPushProvider
from app.providers.twelvedata_provider import TwelveDataProvider
from app.providers.csv_provider import CSVProvider

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_FILE = os.path.join(BASE_DIR, "data", "source_config.json")

class DataSourceManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DataSourceManager, cls).__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self.ea_push_instance = EAPushProvider()
        self.twelvedata_instance = TwelveDataProvider()
        self.csv_instance = CSVProvider()
        
        # Load mode from config
        self.mode = "AUTO"
        self._load_config()

    def _load_config(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r") as f:
                    data = json.load(f)
                    self.mode = data.get("mode", "AUTO")
        except Exception as e:
            print(f"[DataSourceManager] Error loading config: {e}")

    def _save_config(self):
        try:
            # Ensure data dir exists
            os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
            with open(CONFIG_FILE, "w") as f:
                json.dump({"mode": self.mode}, f)
        except Exception as e:
            print(f"[DataSourceManager] Error saving config: {e}")

    def set_mode(self, mode: str):
        if mode.upper() not in ["AUTO", "MT5", "TWELVEDATA", "CSV"]:
            raise ValueError(f"Invalid mode: {mode}")
        self.mode = mode.upper()
        self._save_config()

    def get_status(self) -> dict:
        mt5_healthy = self.ea_push_instance.is_active()
        td_healthy = not self.twelvedata_instance.is_quota_exceeded()
        
        active_provider = self._determine_active_provider()
        
        active_name = "Unknown"
        if active_provider == self.ea_push_instance:
            active_name = "MT5"
        elif active_provider == self.twelvedata_instance:
            active_name = "TWELVEDATA"
        elif active_provider == self.csv_instance:
            active_name = "CSV"

        return {
            "mode": self.mode,
            "active_provider": active_name,
            "mt5_healthy": mt5_healthy,
            "twelvedata_healthy": td_healthy,
            "last_mt5_push_ago": time.time() - self.ea_push_instance.get_last_push_time() if self.ea_push_instance.get_last_push_time() > 0 else -1
        }

    def _determine_active_provider(self):
        if self.mode == "MT5":
            return self.ea_push_instance
        elif self.mode == "TWELVEDATA":
            return self.twelvedata_instance
        elif self.mode == "CSV":
            return self.csv_instance
            
        # AUTO logic
        if self.ea_push_instance.is_active():
            return self.ea_push_instance
        
        if not self.twelvedata_instance.is_quota_exceeded():
            return self.twelvedata_instance
            
        # Absolute fallback if both are dead
        return self.csv_instance
        
    def get_active_provider(self):
        return self._determine_active_provider()

# Singleton instance
data_source_manager = DataSourceManager()
