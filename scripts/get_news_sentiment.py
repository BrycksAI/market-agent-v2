#!/usr/bin/env python3
"""Fetch financial news headlines from RSS feeds and score sentiment."""
import json, pathlib, re, ssl, urllib.request
from datetime import datetime, timedelta, timezone
import certifi, feedparser

SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
DATA_DIR = pathlib.Path(__file__).resolve().parent.parent / "data"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

RSS_FEEDS = {
    "CNBC": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114",
    "BBC Business": "https://feeds.bbci.co.uk/news/business/rss.xml",
    "Google News Finance": "https://news.google.com/rss/search?q=stock+market+economy+forex&hl=en-US&gl=US&ceid=US:en",
}

POSITIVE = {"rally","surge","gain","rise","jump","soar","bull","bullish","recovery","rebound",
    "optimism","boom","growth","record high","beat","exceeded","upgrade","strong","strength",
    "profit","profits","upbeat","positive","momentum","breakout","outperform","dovish","stimulus","cut","rate cut"}
NEGATIVE = {"crash","plunge","drop","fall","decline","slump","bear","bearish","recession",
    "downturn","crisis","fear","panic","sell-off","loss","miss","downgrade","weak","weakness",
    "risk","warning","inflation","hawkish","hike","rate hike","tariff","sanctions","war","default","volatile"}
MACRO = {"fed","ecb","boj","fomc","cpi","ppi","gdp","nfp","payroll","unemployment","interest rate",
    "inflation","treasury","yields","dollar","oil","gold","s&p","nasdaq","dow","bitcoin","crypto",
    "trade war","tariff","china","europe","japan"}

def fetch_feed(name, url):
    headlines = []
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        resp = urllib.request.urlopen(req, context=SSL_CONTEXT, timeout=10)
        feed = feedparser.parse(resp.read())
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        for entry in feed.entries[:20]:
            published = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                published = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
            if published and published < cutoff: continue
            title = entry.get("title", "").strip()
            if not title: continue
            headlines.append({"source": name, "title": title,
                "published": published.isoformat() if published else None, "link": entry.get("link", "")})
    except Exception as e:
        print(f"  Warning: {name} feed failed: {e}")
    return headlines

def score_sentiment(title):
    lower = title.lower()
    pos = sum(1 for w in POSITIVE if w in lower)
    neg = sum(1 for w in NEGATIVE if w in lower)
    label = "positive" if pos > neg else "negative" if neg > pos else "neutral"
    return {"pos_score": pos, "neg_score": neg, "sentiment": label, "is_macro": any(k in lower for k in MACRO)}

def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    all_headlines = []
    print("Fetching news feeds...")
    for name, url in RSS_FEEDS.items():
        h = fetch_feed(name, url)
        all_headlines.extend(h)
        print(f"  {name}: {len(h)} headlines")

    for h in all_headlines:
        h.update(score_sentiment(h["title"]))

    pos = sum(1 for h in all_headlines if h["sentiment"] == "positive")
    neg = sum(1 for h in all_headlines if h["sentiment"] == "negative")
    neu = sum(1 for h in all_headlines if h["sentiment"] == "neutral")
    total = len(all_headlines)

    if total > 0:
        overall = "Risk-On" if pos > neg * 1.5 else "Risk-Off" if neg > pos * 1.5 else "Mixed"
    else:
        overall = "N/A"

    macro = [h for h in all_headlines if h["is_macro"]][:5]
    output = {"timestamp": datetime.now(timezone.utc).isoformat(), "total_headlines": total,
        "sentiment_counts": {"positive": pos, "negative": neg, "neutral": neu},
        "overall_sentiment": overall, "top_macro_headlines": macro}
    out = DATA_DIR / "news_sentiment.json"
    with open(out, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n{pos} positive, {neg} negative, {neu} neutral → {overall}")
    print(f"Written to {out}")

if __name__ == "__main__":
    main()
