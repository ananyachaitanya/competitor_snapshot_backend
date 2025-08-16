from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from collections import Counter
import re, json

an = SentimentIntensityAnalyzer()

def compute_sentiment(text):
    if not text: return {"compound":0.0, "label":"neutral"}
    s = an.polarity_scores(text)
    label = "neutral"
    if s["compound"] >= 0.05: label = "positive"
    if s["compound"] <= -0.05: label = "negative"
    return {"compound": s["compound"], "label": label, "scores": s}

def extract_keywords(text, topk=8):
    words = re.findall(r'\w+', text.lower())
    stop = set(["the","and","is","in","to","for","of","a","on","with","by","as"])
    words = [w for w in words if w not in stop and len(w)>2]
    c = Counter(words)
    return [w for w,_ in c.most_common(topk)]

def diff_snapshots(prev, curr):
    diffs = []
    if not prev:
        diffs.append("Initial snapshot")
    else:
        # prev is SQLAlchemy Snapshot object (db.Snapshot)
        if prev.homepage_title != curr["homepage"].get("title",""):
            diffs.append("Homepage title changed")
        if prev.homepage_h1 != curr["homepage"].get("h1",""):
            diffs.append("Homepage H1 changed")
        # prev feed titles
        try:
            prev_feed = json.loads(prev.feed_items_json or "[]")
            prev_titles = {i.get("title","") for i in prev_feed}
        except:
            prev_titles = set()
        curr_titles = {it.get("title","") for it in curr.get("feed_items",[])}
        new = curr_titles - prev_titles
        if new:
            diffs.append(f"{len(new)} new feed post(s)")
    return diffs

def compute_heat_score(prev, curr):
    score = 0
    if not prev:
        return 50
    try:
        prev_feed = json.loads(prev.feed_items_json or "[]")
        prev_titles = {i.get("title","") for i in prev_feed}
    except:
        prev_titles = set()
    curr_titles = {it.get("title","") for it in curr.get("feed_items",[])}
    new_blogs = len(curr_titles - prev_titles)
    score += min(new_blogs,5)*40
    if prev.homepage_h1 != curr["homepage"].get("h1",""):
        score += 30
    if prev.homepage_title != curr["homepage"].get("title",""):
        score += 20
    return max(0, min(100, score))
