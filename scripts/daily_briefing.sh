#!/bin/bash
set -e  # Stop on error

# Get the directory where this script lives
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DATA_DIR="$PROJECT_DIR/data"

echo "=== Daily Market Briefing ==="
echo "Date: $(date -u '+%Y-%m-%d %H:%M UTC')"
echo ""

# Step 1: Market Data
echo "[1/4] Fetching market data..."
python3 "$SCRIPT_DIR/get_market_data.py" || echo "  ⚠️ Market data failed"

echo ""

# Step 2: News Sentiment
echo "[2/4] Fetching news sentiment..."
python3 "$SCRIPT_DIR/get_news_sentiment.py" || echo "  ⚠️ News sentiment failed"

echo ""

# Step 3: Macro Calendar
echo "[3/4] Fetching macro calendar..."
python3 "$SCRIPT_DIR/get_macro_calendar.py" || echo "  ⚠️ Macro calendar failed"

echo ""

# Step 4: Send to Telegram
echo "[4/4] Sending briefing to Telegram..."
python3 "$SCRIPT_DIR/send_telegram.py" || echo "  ⚠️ Telegram send failed"

echo ""
echo "=== Done ==="
