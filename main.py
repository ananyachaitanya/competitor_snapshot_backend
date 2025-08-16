import asyncio, json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from scraper import make_snapshot
from db import init_db, save_snapshot_obj, get_latest_snapshot, get_previous_snapshot, list_domains
from analyzer import compute_sentiment, diff_snapshots, compute_heat_score, extract_keywords
from db import delete_domain_from_db
app = FastAPI()
init_db()

clients = set()
POLL_INTERVAL = 60  # seconds (set higher for production, e.g., 300)

async def broadcast(payload):
    dead = []
    for ws in list(clients):
        try:
            await ws.send_text(json.dumps({"type":"snapshot","payload":payload}))
        except Exception:
            dead.append(ws)
    for d in dead:
        clients.discard(d)

async def poll_loop():
    loop = asyncio.get_running_loop()
    while True:
        domains = list_domains()
        if domains:
            for d in domains:
                prev_rec = get_latest_snapshot(d)
                url = prev_rec.url if prev_rec else f"https://{d}"
                # run blocking snapshot in executor
                curr = await loop.run_in_executor(None, make_snapshot, url)
                prev = get_previous_snapshot(d)
                # compute diffs and metrics
                diffs = await loop.run_in_executor(None, diff_snapshots, prev, curr) if prev else ["Initial snapshot"]
                heat = await loop.run_in_executor(None, compute_heat_score, prev, curr)
                sentiment = await loop.run_in_executor(None, compute_sentiment, curr.get("text_bundle",""))
                keywords = await loop.run_in_executor(None, extract_keywords, curr.get("text_bundle",""))
                payload = {"domain": curr["domain"], "url": curr["url"], "timestamp": curr["timestamp"], "homepage": curr["homepage"], "feed_items": curr["feed_items"], "diffs": diffs, "heat": heat, "sentiment": sentiment, "keywords": keywords}
                curr["diffs"] = diffs
                curr["heat"] = heat
                curr["sentiment"] = sentiment
                curr["keywords"] = keywords
                # save to DB
                await loop.run_in_executor(None, save_snapshot_obj, curr)
                # broadcast to websocket clients
                await broadcast(payload)
                await asyncio.sleep(1)
        await asyncio.sleep(POLL_INTERVAL)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(poll_loop())


# New /add endpoint: responds immediately, snapshot handled by poll_loop
@app.post("/add")
async def add_domain(payload: dict):
    url = payload.get("url")
    if not url:
        return JSONResponse({"error": "missing url"}, status_code=400)
    # Save domain to DB with minimal info so poll_loop will pick it up
    from db import Snapshot, SessionLocal
    domain = url.split("//")[-1].split("/")[0] if url.startswith("http") else url.split("/")[0]
    sess = SessionLocal()
    # Only add if not already present
    exists = sess.query(Snapshot).filter_by(domain=domain).first()
    if not exists:
        s = Snapshot(domain=domain, url=url)
        sess.add(s)
        sess.commit()
    sess.close()
    # Respond immediately; snapshot will be created by poll_loop
    return {"status": "ok", "domain": domain}

@app.get("/domains")
async def get_domains():
    return {"domains": list_domains()}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.add(websocket)
    try:
        while True:
            # keep connection alive; clients can send pings optionally
            await websocket.receive_text()
    except WebSocketDisconnect:
        clients.discard(websocket)

@app.delete("/domain/{domain}")
async def delete_domain(domain: str):
    from db import delete_domain_from_db  # you'll need to implement this
    deleted = delete_domain_from_db(domain)
    if deleted:
        return {"status": "ok", "message": f"{domain} deleted"}
    return JSONResponse({"error": "domain not found"}, status_code=404)

