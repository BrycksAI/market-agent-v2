#!/usr/bin/env python3
"""Send the daily market briefing to Telegram."""
import json, pathlib, ssl, sys, urllib.request
import certifi

SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
PROJECT_DIR = pathlib.Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"
ENV_FILE = PROJECT_DIR / ".env"

def load_env():
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env

def send_telegram(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": text, "parse_mode": "HTML"}).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req, context=SSL_CONTEXT)
    return json.loads(resp.read()).get("ok", False)

def format_briefing(data):
    lines = ["<b>📊 Daily Market Briefing</b>", ""]

    # Price Action
    lines.append("<b>🟢 Price Action (24h)</b>")
    for name in ["S&P500", "DXY", "Gold", "Crude Oil", "BTC/USD"]:
        a = data.get(name, {})
        if "error" in a: continue
        chg = a["change_24h_pct"]
        arrow = "🟩" if chg >= 0 else "🟥"
        lines.append(f"  {arrow} {name}: {a['last_close']:,.2f} ({chg:+.2f}%)")
    lines.append("")

    # Technical Alerts
    lines.append("<b>Technical Alerts (RSI-14)</b>")
    alerts = [f"  {'🔴' if a['rsi_signal'] == 'Overbought' else '🔵'} {n}: RSI {a['rsi_14']} — {a['rsi_signal']}"
              for n, a in data.items() if "rsi_signal" in a and a["rsi_signal"] in ("Overbought", "Oversold")]
    lines.extend(alerts if alerts else ["  ✅ No extreme RSI levels"])
    lines.append("")

    # VIX
    vix = data.get("VIX", {})
    if "error" not in vix:
        regime = "Low" if vix["last_close"] < 15 else "Normal" if vix["last_close"] < 25 else "High"
        lines.append(f"<b>Volatility:</b> VIX {vix['last_close']:.2f} ({vix['change_24h_pct']:+.2f}%) — {regime}")
        lines.append("")

    # Market Bias
    dxy = data.get("DXY", {})
    sp = data.get("S&P500", {})
    if "error" not in dxy and "error" not in sp:
        bias = "Risk-On 🟢" if sp["change_24h_pct"] > 0 and dxy["change_24h_pct"] < 0 else                "Risk-Off 🔴" if sp["change_24h_pct"] < 0 and dxy["change_24h_pct"] > 0 else "Mixed ⚪"
        lines.append(f"<b>🔵 Market Bias:</b> {bias}")
        lines.append("")

    # Yield Curve
    us10 = data.get("US10Y", {})
    us02 = data.get("US02Y", {})
    if "error" not in us10 and "error" not in us02:
        spread = us10["last_close"] - us02["last_close"]
        lines.append(f"<b>🟣 Yield Curve:</b> {'⚠️ INVERTED' if spread < 0 else '✅ Normal'}")
        lines.append(f"  10Y: {us10['last_close']:.2f}% | 2Y: {us02['last_close']:.2f}% | Spread: {spread:+.2f}%")
        lines.append("")

    # News Sentiment
    news_file = DATA_DIR / "news_sentiment.json"
    if news_file.exists():
        news = json.loads(news_file.read_text())
        c = news.get("sentiment_counts", {})
        lines.append(f"<b>📰 Sentiment:</b> {news.get('overall_sentiment', 'N/A')} "
                     f"(👍 {c.get('positive',0)} / 👎 {c.get('negative',0)} / ⚪ {c.get('neutral',0)})")
        for h in news.get("top_macro_headlines", [])[:3]:
            emoji = "👍" if h["sentiment"] == "positive" else "👎" if h["sentiment"] == "negative" else "⚪"
            lines.append(f"  {emoji} {h['title'][:80]}")
        lines.append("")

    # Macro Calendar
    cal_file = DATA_DIR / "macro_calendar.json"
    if cal_file.exists():
        cal = json.loads(cal_file.read_text())
        for name in ["london_killzone", "ny_killzone"]:
            s = cal.get("sessions", {}).get(name, {})
            if s:
                lines.append(f"<b>{'🇬🇧 London' if 'london' in name else '🗽 NY'}:</b> {s.get('risk','N/A')} ({s.get('high_impact_count',0)} events)")
        if cal.get("high_impact_events"):
            lines.append("")
            lines.append("<b>⚠️ High Impact Events:</b>")
            for e in cal["high_impact_events"][:3]:
                lines.append(f"  {e['time']} | {e['country']} | {e['title']}")
        lines.append("")

    sample_date = next((a.get("date") for a in data.values() if "date" in a), "")
    if sample_date:
        lines.append(f"<i>Data: {sample_date}</i>")
    return "\n".join(lines)

def main():
    env = load_env()
    token = env.get("TELEGRAM_BOT_TOKEN")
    chat_id = env.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id or chat_id == "PLACEHOLDER":
        print("ERROR: Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env")
        sys.exit(1)

    market_file = DATA_DIR / "market_data.json"
    if not market_file.exists():
        print("ERROR: Run get_market_data.py first")
        sys.exit(1)

    data = json.loads(market_file.read_text())
    message = format_briefing(data)
    if len(message) > 4096:
        message = message[:4090] + "\n..."

    if send_telegram(token, chat_id, message):
        print("✅ Briefing sent to Telegram!")
    else:
        print("❌ Send failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
