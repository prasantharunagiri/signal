//+------------------------------------------------------------------+
//|                                XAUUSD_Signal_Receiver_EA.mq5     |
//|               XAUUSD Smart Signal Engine - Two-Way MT5 EA        |
//|                                   http://129.225.115.79         |
//+------------------------------------------------------------------+
#property copyright "XAUUSD Smart Signal Engine"
#property link      "http://129.225.115.79"
#property version   "2.00"
#property description "Two-Way MT5 EA: Pushes Exness Ticks/Candles & Auto-Executes Signals"

#include <Trade\Trade.mqh>

//--- Input Parameters
input group "=== Oracle Server Configuration ==="
input string   InpServerURL        = "http://129.225.115.79:8000/api/signals/active"; // Signal API URL
input string   InpPushURL          = "http://129.225.115.79:8000/api/market/push";    // Live Market Push URL
input int      InpPollIntervalSec  = 3;                             // Poll & Push Interval (Seconds)
input int      InpMinSignalScore   = 80;                            // Minimum Signal Score to Execute (Grade A/A+)

input group "=== Risk Management & Lot Sizing ==="
input bool     InpUseRiskPercent   = true;                          // Calculate Lot Size based on Account Risk %
input double   InpRiskPercent      = 1.0;                           // Risk Percentage per Trade (e.g. 1.0 = 1%)
input double   InpFixedLotSize     = 0.10;                          // Fixed Lot Size (if UseRiskPercent is false)
input double   InpMaxLotSize       = 5.00;                          // Maximum Allowed Lot Size Safety Limit

input group "=== Trade Management & Magic Number ==="
input ulong    InpMagicNumber      = 20260826;                      // EA Unique Magic Number
input int      InpSlippagePips     = 10;                            // Maximum Allowed Slippage (Pips)
input bool     InpEnableBreakeven  = true;                          // Move SL to Breakeven on 1:1 Risk Reward
input double   InpBreakevenTriggerR= 1.0;                           // Risk Reward ratio to trigger Breakeven

//--- Global Variables
CTrade         m_trade;
string         m_last_processed_signal_id = "";

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
  {
   m_trade.SetExpertMagicNumber(InpMagicNumber);
   m_trade.SetDeviationInPoints(InpSlippagePips * 10);
   
   // Set timer for HTTP polling & pushing
   EventSetTimer(InpPollIntervalSec);
   
   Print("✅ [XAUUSD Two-Way EA] Initialized successfully.");
   Print("📡 Pushing MT5 Market Data & Listening for Signals every ", InpPollIntervalSec, " seconds.");
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   EventKillTimer();
   Print("❌ [XAUUSD EA] Deinitialized.");
  }

//+------------------------------------------------------------------+
//| Expert timer function (Triggered every N seconds)                |
//+------------------------------------------------------------------+
void OnTimer()
  {
   // 1. Push Live Exness Ticks & Candles to Oracle Dashboard Server
   PushMarketData();

   // 2. Check for Breakeven trailing on active trades
   if(InpEnableBreakeven)
      ManageBreakeven();
      
   // 3. Poll Oracle Server for new active Grade A+ signal
   PollServerSignal();
  }

//+------------------------------------------------------------------+
//| OnTick function for immediate live tick push                     |
//+------------------------------------------------------------------+
void OnTick()
  {
   // Push tick on high volatility ticks
  }

//+------------------------------------------------------------------+
//| Pushes Live Exness Ticks & 5m Candles to Oracle Server           |
//+------------------------------------------------------------------+
void PushMarketData()
  {
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   
   if(bid <= 0) return;

   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   int copied = CopyRates(_Symbol, PERIOD_M5, 0, 40, rates);
   
   string json_candles = "[";
   if(copied > 0)
     {
      for(int i = copied - 1; i >= 0; i--)
        {
         string ts = TimeToString(rates[i].time, TIME_DATE|TIME_SECONDS);
         StringReplace(ts, ".", "-");
         
         json_candles += "{\"timestamp\":\"" + ts + "\",";
         json_candles += "\"open\":" + DoubleToString(rates[i].open, 2) + ",";
         json_candles += "\"high\":" + DoubleToString(rates[i].high, 2) + ",";
         json_candles += "\"low\":" + DoubleToString(rates[i].low, 2) + ",";
         json_candles += "\"close\":" + DoubleToString(rates[i].close, 2) + ",";
         json_candles += "\"volume\":" + DoubleToString((double)rates[i].tick_volume, 0) + "}";
         
         if(i > 0) json_candles += ",";
        }
     }
   json_candles += "]";

   MqlRates rates_h1[];
   ArraySetAsSeries(rates_h1, true);
   int copied_h1 = CopyRates(_Symbol, PERIOD_H1, 0, 40, rates_h1);
   
   string json_candles_1h = "[";
   if(copied_h1 > 0)
     {
      for(int i = copied_h1 - 1; i >= 0; i--)
        {
         string ts = TimeToString(rates_h1[i].time, TIME_DATE|TIME_SECONDS);
         StringReplace(ts, ".", "-");
         
         json_candles_1h += "{\"timestamp\":\"" + ts + "\",";
         json_candles_1h += "\"open\":" + DoubleToString(rates_h1[i].open, 2) + ",";
         json_candles_1h += "\"high\":" + DoubleToString(rates_h1[i].high, 2) + ",";
         json_candles_1h += "\"low\":" + DoubleToString(rates_h1[i].low, 2) + ",";
         json_candles_1h += "\"close\":" + DoubleToString(rates_h1[i].close, 2) + ",";
         json_candles_1h += "\"volume\":" + DoubleToString((double)rates_h1[i].tick_volume, 0) + "}";
         
         if(i > 0) json_candles_1h += ",";
        }
     }
   json_candles_1h += "]";

   string payload = "{\"symbol\":\"" + _Symbol + "\",\"timeframe\":\"5m\",\"bid\":" + DoubleToString(bid, 2) + ",\"ask\":" + DoubleToString(ask, 2) + ",\"candles_5m\":" + json_candles + ",\"candles_1h\":" + json_candles_1h + "}";

   char post_data[];
   StringToCharArray(payload, post_data, 0, StringLen(payload), CP_UTF8);
   char result[];
   string result_headers;
   string headers = "Content-Type: application/json\r\n";

   ResetLastError();
   int res = WebRequest("POST", InpPushURL, headers, 2000, post_data, result, result_headers);
   if(res == 200)
     {
      // Pushed successfully
     }
  }

//+------------------------------------------------------------------+
//| Polls Oracle Cloud Server for new Grade A+ signals               |
//+------------------------------------------------------------------+
void PollServerSignal()
  {
   char server_data[];
   char result_data[];
   string result_headers;
   string headers = "Content-Type: application/json\r\n";
   int res;
   
   ResetLastError();
   res = WebRequest("GET", InpServerURL, headers, 2000, server_data, result_data, result_headers);
   
   if(res != 200) return;
     
   string response_json = CharArrayToString(result_data, 0, WHOLE_ARRAY, CP_UTF8);
   if(StringLen(response_json) < 10 || response_json == "[]" || response_json == "null")
      return; // No active signal
      
   // Parse signal fields from JSON
   string signal_id    = ExtractJsonField(response_json, "id");
   string direction    = ExtractJsonField(response_json, "direction"); // LONG or SHORT
   double entry_price  = StringToDouble(ExtractJsonField(response_json, "entry_price"));
   double stop_loss    = StringToDouble(ExtractJsonField(response_json, "stop_loss"));
   double tp1          = StringToDouble(ExtractJsonField(response_json, "tp1"));
   int score           = (int)StringToInteger(ExtractJsonField(response_json, "score"));
   
   if(signal_id == "" || signal_id == m_last_processed_signal_id)
      return; // Already processed this signal
      
   if(score < InpMinSignalScore)
     {
      m_last_processed_signal_id = signal_id;
      return;
     }
     
   Print("🚨 [XAUUSD EA] NEW GRADE A+ SIGNAL DETECTED! ID: ", signal_id, " | ", direction, " | Score: ", score);
   
   // Execute Order
   ExecuteTrade(signal_id, direction, entry_price, stop_loss, tp1);
  }

//+------------------------------------------------------------------+
//| Executes Market Buy or Sell order                                |
//+------------------------------------------------------------------+
void ExecuteTrade(string signal_id, string direction, double entry, double sl, double tp)
  {
   double current_bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double current_ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double sl_pips     = MathAbs(current_bid - sl) / _Point / 10.0;
   
   if(sl_pips <= 0) return;
     
   double lot_size = InpFixedLotSize;
   if(InpUseRiskPercent)
     {
      double account_balance = AccountInfoDouble(ACCOUNT_BALANCE);
      double risk_amount    = account_balance * (InpRiskPercent / 100.0);
      double tick_value      = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
      double tick_size       = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
      
      if(tick_size > 0 && tick_value > 0)
        {
         double sl_points = MathAbs(current_bid - sl) / tick_size;
         lot_size = risk_amount / (sl_points * tick_value);
        }
     }
     
   // Normalize Lot Size
   double step_vol = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double min_vol  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double max_vol  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   
   lot_size = MathFloor(lot_size / step_vol) * step_vol;
   lot_size = MathMax(min_vol, MathMin(MathMin(max_vol, InpMaxLotSize), lot_size));
   
   bool success = false;
   if(direction == "LONG" || direction == "BUY")
     {
      success = m_trade.Buy(lot_size, _Symbol, current_ask, sl, tp, "XAUUSD Signal Engine " + signal_id);
     }
   else if(direction == "SHORT" || direction == "SELL")
     {
      success = m_trade.Sell(lot_size, _Symbol, current_bid, sl, tp, "XAUUSD Signal Engine " + signal_id);
     }
     
   if(success)
     {
      Print("✅ [XAUUSD EA] ORDER EXECUTED! Type: ", direction, " | Lots: ", lot_size, " | SL: ", sl, " | TP: ", tp);
      m_last_processed_signal_id = signal_id;
     }
   else
     {
      Print("❌ [XAUUSD EA] Order execution failed: ", m_trade.ResultRetcodeDescription());
     }
  }

//+------------------------------------------------------------------+
//| Manages trailing Stop Loss to Breakeven                           |
//+------------------------------------------------------------------+
void ManageBreakeven()
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket <= 0) continue;
      
      if(PositionGetString(POSITION_SYMBOL) != _Symbol || PositionGetInteger(POSITION_MAGIC) != InpMagicNumber)
         continue;
         
      double open_price  = PositionGetDouble(POSITION_PRICE_OPEN);
      double current_sl  = PositionGetDouble(POSITION_SL);
      double current_tp  = PositionGetDouble(POSITION_TP);
      long pos_type      = PositionGetInteger(POSITION_TYPE);
      double current_price = (pos_type == POSITION_TYPE_BUY) ? SymbolInfoDouble(_Symbol, SYMBOL_BID) : SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      
      if(current_sl == open_price) continue;
      
      double risk_points = MathAbs(open_price - current_sl);
      if(risk_points <= 0) continue;
      
      if(pos_type == POSITION_TYPE_BUY)
        {
         if(current_price >= open_price + (risk_points * InpBreakevenTriggerR))
           {
            m_trade.PositionModify(ticket, open_price, current_tp);
            Print("🔒 [XAUUSD EA] Moved Stop Loss to BREAKEVEN for Buy Ticket #", ticket);
           }
        }
      else if(pos_type == POSITION_TYPE_SELL)
        {
         if(current_price <= open_price - (risk_points * InpBreakevenTriggerR))
           {
            m_trade.PositionModify(ticket, open_price, current_tp);
            Print("🔒 [XAUUSD EA] Moved Stop Loss to BREAKEVEN for Sell Ticket #", ticket);
           }
        }
     }
  }

//+------------------------------------------------------------------+
//| Helper JSON Field Extractor                                      |
//+------------------------------------------------------------------+
string ExtractJsonField(string json, string field_name)
  {
   string pattern = "\"" + field_name + "\":";
   int pos = StringFind(json, pattern);
   if(pos < 0) return "";
   
   pos += StringLen(pattern);
   while(pos < StringLen(json) && (StringSubstr(json, pos, 1) == " " || StringSubstr(json, pos, 1) == "\""))
      pos++;
      
   int end_pos = pos;
   while(end_pos < StringLen(json))
     {
      string ch = StringSubstr(json, end_pos, 1);
      if(ch == "\"" || ch == "," || ch == "}" || ch == "\r" || ch == "\n")
         break;
      end_pos++;
     }
     
   return StringSubstr(json, pos, end_pos - pos);
  }
