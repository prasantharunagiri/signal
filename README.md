# XAUUSD SMART SIGNAL ENGINE

### Institutional Quantitative Gold (XAUUSD) Trading Signal, Backtesting & Performance Platform

The **XAUUSD Smart Signal Engine** is an institutional-grade, rule-based quantitative trading signal, backtesting, and performance platform for Gold (XAUUSD). It is designed for **24/7 continuous server-side production operation**, completely independent of the browser frontend.

---

## 🌟 CORE FEATURES

- **24/7 Server-First Background Architecture**:
  - The backend evaluates confirmed candle closes, tracks active signal outcomes, monitors system health, and dispatches Telegram alerts **24/7** without requiring the browser or your personal computer to stay online.
- **Shared Strategy Engine (Single Source of Truth)**:
  - Both the **Live Signal Engine** and **Chronological Backtesting Engine** share the exact same quantitative strategy implementation (`backend/app/strategies/`). Zero strategy code duplication.
- **R-Multiple Centric Performance (Preset Separated)**:
  - Performance statistics (Win Rate, Average R, Expectancy, Max Drawdown, Profit Factor) are tracked and displayed **strictly separated by strategy preset** (`SCALP`, `INTRADAY`, `SWING`).
- **No Look-Ahead Bias**:
  - Historical candles and $N=2$ swing points are evaluated strictly chronologically. Swing highs/lows are only confirmed after future $N$ candles close.
- **Strict Data Segregation**:
  - Synthetic/demo data (`is_demo = True`) is strictly isolated for UI and software testing. Real backtesting and performance analytics query genuine historical market data (`is_demo = False`).
- **Pluggable Data Architecture & MT5 Adapter**:
  - Connect via `CSVProvider` (genuine multi-timeframe datasets), `TwelveDataProvider`, or `MT5Provider` (server-side MetaTrader 5 broker terminal adapter).
- **Health Watchdog & Stale Data Detection**:
  - Monitored data latency flags `DATA STALE` or `DATA FEED OFFLINE` when candle feeds freeze, triggering automatic backfill and recovery upon reconnect.

---

## 🚀 LOCAL DEVELOPMENT SETUP

### 1. Prerequisites
- Python 3.9+
- Node.js v18+ & npm

### 2. Backend Setup
```bash
# Navigate to project root
cd /path/to/project

# Install Python dependencies
pip install -r backend/requirements.txt

# Seed genuine multi-timeframe historical CSV datasets
PYTHONPATH=backend python3 backend/app/seed/seed_data.py

# Run FastAPI backend server
PYTHONPATH=backend python3 -m uvicorn app.main:app --reload --port 8000
```
Backend API will be running at: `http://localhost:8000` (API Docs: `http://localhost:8000/docs`)

### 3. Frontend Setup
```bash
# Open a new terminal tab and navigate to frontend directory
cd frontend

# Install npm dependencies
npm install

# Run Vite development server
npm run dev
```
Frontend Terminal UI will be running at: `http://localhost:3000`

---

## 🧪 RUNNING AUTOMATED UNIT & ACCEPTANCE TESTS

To run the complete 24-test Pytest suite:
```bash
PYTHONPATH=backend python3 -m pytest backend/tests/
```

To run the 15-scenario acceptance test suite specifically:
```bash
PYTHONPATH=backend python3 -m pytest backend/tests/test_acceptance_scenarios.py
```

---

## 🗄️ PRODUCTION DATABASE SETUP (PostgreSQL)

By default, local development uses zero-config SQLite (`sqlite:///./xauusd_engine.db`).
For production deployment, switch to PostgreSQL:

1. Create PostgreSQL database:
```sql
CREATE DATABASE xauusd_db;
CREATE USER xauusd_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE xauusd_db TO xauusd_user;
```
2. Update `.env`:
```ini
DATABASE_URL="postgresql://xauusd_user:your_secure_password@localhost:5432/xauusd_db"
```

---

## 📡 METATRADER 5 (MT5) SERVER-SIDE ADAPTER SETUP

To connect live broker data via MT5:

1. Install MetaTrader 5 terminal on your Linux/Windows VPS.
2. Install Python MT5 module:
```bash
pip install MetaTrader5
```
3. Configure `.env` on the backend server:
```ini
MARKET_DATA_PROVIDER="mt5"
MT5_LOGIN=12345678
MT5_PASSWORD="YourSecretBrokerPassword"
MT5_SERVER="Broker-LiveServer"
```
*MT5 credentials remain securely on the backend server and are never exposed to the frontend.*

---

## 🤖 TELEGRAM & WEBHOOK NOTIFICATIONS

To receive instant notifications when valid setups appear:

1. Create a bot via `@BotFather` on Telegram to get your `TELEGRAM_BOT_TOKEN`.
2. Get your Chat ID via `@userinfobot` or channel ID.
3. Configure `.env`:
```ini
TELEGRAM_BOT_TOKEN="123456789:ABCdefGHIjklMNOpqrsTUVwxyZ"
TELEGRAM_CHAT_ID="-100123456789"
```
Notifications format:
```text
🟡 XAUUSD SIGNAL — SWING

Direction: LONG

Entry: 2504.80
Stop Loss: 2498.40
TP1: 2511.20 | TP2: 2517.60 | TP3: 2524.00

Score: 87/100 (Grade A)

Setup: XAUUSD swept previous session low (PSL), formed SMT divergence, followed by bullish MSS break and FVG displacement.

Time: 2026-08-22 14:00:00 UTC
```

---

## 🌐 24/7 VPS / CLOUD PRODUCTION DEPLOYMENT

### Deploying via Docker Compose (Recommended)
```bash
# Copy env template
cp .env.example .env

# Edit environment variables
nano .env

# Build and start all services in background
docker-compose up -d --build
```

### Deploying to Render / Railway / Fly.io
- **Backend Service**: Deploy `backend/` directory as a Python web service running `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
- **Database**: Attach a managed PostgreSQL database and set `DATABASE_URL`.
- **Frontend Service**: Build `frontend/` (`npm run build`) and deploy static `dist/` folder to Vercel/Netlify/Render.

---

## 🩺 SYSTEM HEALTH VERIFICATION

Check watchdog health status at any time via endpoint:
`GET http://localhost:8000/api/health/status`

Or view telemetry live in the dashboard under the **Data Health** tab!
