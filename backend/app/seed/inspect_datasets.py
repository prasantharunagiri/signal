import os
import pandas as pd

def audit_directory(data_dir: str, label: str):
    if not os.path.exists(data_dir):
        return

    files = sorted(os.listdir(data_dir))
    for fname in files:
        if not fname.endswith(".csv"):
            continue
        filepath = os.path.join(data_dir, fname)
        df = pd.read_csv(filepath)
        if df.empty:
            continue
        
        parts = fname.replace(".csv", "").split("_")
        symbol = parts[0] if len(parts) > 0 else "UNKNOWN"
        tf = parts[1] if len(parts) > 1 else "UNKNOWN"
        
        min_ts = df["timestamp"].min()
        max_ts = df["timestamp"].max()
        count = len(df)
        
        print(f"{fname:<25} | {symbol:<8} | {tf:<5} | {count:<8} | {str(min_ts):<20} | {str(max_ts):<20} | {label}")

def audit_datasets():
    print(f"{'Filename':<25} | {'Symbol':<8} | {'TF':<5} | {'Candles':<8} | {'Start UTC':<20} | {'End UTC':<20} | {'Type'}")
    print("-" * 115)
    audit_directory("data/csv_genuine", "GENUINE (REAL DATA)")
    audit_directory("data/csv", "GENERATED (DEMO DATA)")

if __name__ == "__main__":
    audit_datasets()
