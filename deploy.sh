#!/bin/bash
set -e
echo "=== Market Agent Deployment ==="

echo "[1/4] Installing system packages..."
sudo apt-get update -qq
sudo apt-get install -y -qq python3 python3-pip python3-venv curl

echo "[2/4] Setting up project..."
mkdir -p ~/market-agent
cd ~/market-agent

echo "[3/4] Installing Python packages..."
python3 -m venv venv
source venv/bin/activate
pip install -q -r requirements.txt

echo "[4/4] Setting up cron (weekdays at 08:00 UTC)..."
CRON_JOB="0 8 * * 1-5 cd $HOME/market-agent && venv/bin/bash scripts/daily_briefing.sh >> data/cron.log 2>&1"
(crontab -l 2>/dev/null | grep -v "daily_briefing" || true; echo "$CRON_JOB") | crontab -

echo ""
echo "=== Done! ==="
echo ""
echo "Next steps:"
echo "  1. Edit ~/market-agent/.env with your Telegram bot token"
echo "  2. Test: cd ~/market-agent && venv/bin/bash scripts/daily_briefing.sh"
echo "  3. Already scheduled: weekdays at 08:00 UTC"
echo ""
echo "RAM: ~50-80 MB per run (script exits after)"
