#!/usr/bin/env python3
"""Fetch economic calendar events for the next 24 hours."""
import json, pathlib, ssl, urllib.request
from datetime import datetime, timedelta, timezone
import certifi

SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
DATA_DIR = pathlib.Path(__file__).resolve().parent.parent / "data"
CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"

SESSIONS = {
    "london_killzone": {"start": 7, "end": 10},
    "ny_killzone": {"start": 12, "end": 17},
}

def fetch_calendar():
    try:
        req = urllib.request.Request(CALENDAR_URL, headers={"User-Agent": "MarketAgent/1.0"})
        resp = urllib.request.urlopen(req, context=SSL_CONTEXT, timeout=15)
        return json.loads(resp.read())
    except Exception as e:
        print(f"Warning: Calendar fetch failed: {e}")
        return []

def classify_impact(event):
    impact = event.get("impact", "").upper()
    if impact in ("HIGH", "HIGH:"):
        return True
    # Also flag holidays
    if "holiday" in event.get("title", "").lower():
        return True
    return False

def get_session_risk(events, session_name):
    s = SESSIONS.get(session_name, {})
    now = datetime.now(timezone.utc)
    in_session = s.get("start", 0) <= now.hour < s.get("end", 24)
    high_impact = [e for e in events if classify_impact(e)]
    count = 0
    for e in high_impact:
        try:
            dt_str = e.get("_parsed_dt", "")
            if dt_str:
                hour = int(dt_str.split("T")[1].split(":")[0])
                if s.get("start", 0) <= hour < s.get("end", 24):
                    count += 1
        except:
            pass
    if count >= 2: risk = "High"
    elif count == 1: risk = "Medium"
    else: risk = "Low"
    return {"in_session": in_session, "risk": risk, "high_impact_count": count}

def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print("Fetching macro calendar...")
    events = fetch_calendar()
    print(f"  {len(events)} events found")

    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(hours=24)

    upcoming = []
    for e in events:
        try:
            raw = e.get("date", "")
            if not raw:
                continue
            # Parse ISO format like "2026-05-17T18:30:00-04:00"
            dt = datetime.fromisoformat(raw)
            if now <= dt <= cutoff:
                # Also store parsed time for display purposes
                e["_parsed_dt"] = dt.isoformat()
                upcoming.append(e)
        except Exception as ex:
            pass

    high_impact = []
    for e in upcoming:
        if classify_impact(e):
            # Format time for display
            dt_display = e.get("_parsed_dt", "")
            time_display = dt_display.split("T")[1][:5] + " UTC" if "T" in dt_display else ""
            high_impact.append({
                "time": time_display, "date": e.get("date", "")[:10],
                "country": e.get("country", ""), "title": e.get("title", ""),
                "impact": e.get("impact", ""), "forecast": e.get("forecast", ""),
                "previous": e.get("previous", ""),
            })

    sessions = {}
    for name in SESSIONS:
        sessions[name] = get_session_risk(upcoming, name)

    output = {
        "timestamp": now.isoformat(),
        "events_next_24h": len(upcoming),
        "high_impact_count": len(high_impact),
        "high_impact_events": high_impact[:5],
        "sessions": sessions,
    }

    out = DATA_DIR / "macro_calendar.json"
    with open(out, "w") as f:
        json.dump(output, f, indent=2)

    print(f"  {len(upcoming)} events in next 24h, {len(high_impact)} high impact")
    print(f"Written to {out}")

if __name__ == "__main__":
    main()
