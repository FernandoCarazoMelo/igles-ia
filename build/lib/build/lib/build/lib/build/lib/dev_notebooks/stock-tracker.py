import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# List of tickers to track
tickers = ["AAPL", "TSLA", "MSFT", "NVDA"]

# Date range: enough to cover at least 3 trading days + margin
end_date = datetime.today()
start_date = end_date - timedelta(days=10)

# Store alerts
alerts = []

for ticker in tickers:
    # Download historical data
    df = yf.download(ticker, start=start_date, end=end_date)
    
    if df.empty:
        continue  # Skip if no data

    df = df[['Adj Close']].copy()
    # Calculate 3-day percentage change
    df['pct_change_3d'] = df['Adj Close'].pct_change(periods=3) * 100

    # Check if any of the last 3 entries had a drop of 20% or more
    recent = df.tail(3)
    if (recent['pct_change_3d'] <= -20).any():
        alerts.append({
            'ticker': ticker,
            'date': recent.index[-1].date(),
            'change_%': round(recent['pct_change_3d'].iloc[-1], 2)
        })

# Export to CSV
report = pd.DataFrame(alerts)
report.to_csv("drop_alerts.csv", index=False)

# Print results
print(report)
