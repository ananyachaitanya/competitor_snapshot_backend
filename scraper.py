import requests
from bs4 import BeautifulSoup
import feedparser
from urllib.parse import urljoin, urlparse
from datetime import datetime

HEADERS = {"User-Agent":"CompetitorSnapshotBot/0.1 (+your-email@example.com)"}

def fetch_html(url, timeout=8):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print("fetch error", e)
        return None

def parse_homepage(html):
    soup = BeautifulSoup(html or "", "html.parser")
    title = soup.title.string.strip() if soup.title else ""
    h1 = soup.find("h1")
    h1_text = h1.get_text(strip=True) if h1 else ""
    meta = soup.find("meta", attrs={"name":"description"}) or soup.find("meta", attrs={"property":"og:description"})
    meta_desc = meta.get("content","") if meta and meta.get("content") else ""
    p = soup.find("p")
    lead = p.get_text(strip=True) if p else ""
    return {"title":title, "h1":h1_text, "meta":meta_desc, "lead":lead}

def find_rss(html, base_url):
    soup = BeautifulSoup(html or "", "html.parser")
    link = soup.find("link", type="application/rss+xml")
    if link and link.get("href"):
        return urljoin(base_url, link["href"])
    # try common feed paths
    for path in ("/feed","/rss","/atom.xml"):
        test = urljoin(base_url, path)
        try:
            r = requests.head(test, headers=HEADERS, timeout=4)
            if r.status_code == 200:
                return test
        except:
            continue
    return None

def parse_rss(feed_url, limit=5):
    try:
        d = feedparser.parse(feed_url)
        items = []
        for e in d.entries[:limit]:
            items.append({
                "title": e.get("title",""),
                "summary": e.get("summary","") or e.get("description",""),
                "link": e.get("link",""),
                "published": e.get("published","")
            })
        return items
    except Exception as e:
        print("rss error", e)
        return []

def make_snapshot(url):
    if not url.startswith("http"):
        url = "https://" + url
    domain = urlparse(url).netloc
    html = fetch_html(url)
    hp = parse_homepage(html)
    rss = find_rss(html, url)
    feed_items = parse_rss(rss) if rss else []
    texts = []
    if hp.get("title"): texts.append(hp["title"])
    if hp.get("h1"): texts.append(hp["h1"])
    for it in feed_items:
        texts.append(it.get("title",""))
        texts.append(it.get("summary",""))
    text_bundle = " ".join([t for t in texts if t])
    return {"domain": domain, "url": url, "homepage": hp, "rss": rss, "feed_items": feed_items, "text_bundle": text_bundle, "timestamp": datetime.utcnow().isoformat()}