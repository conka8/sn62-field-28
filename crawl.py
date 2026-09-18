import json, pathlib, time, urllib.error, urllib.request

BASE = "https://agent-upload.ridges.ai"
GAP = 1.1           # Cloudflare rate-limits bursts; keep a >900ms floor
OUT = pathlib.Path("runs28"); OUT.mkdir(exist_ok=True)
last = [0.0]

def get(path, query=""):
    for attempt in range(5):
        wait = GAP - (time.time() - last[0])
        if wait > 0:
            time.sleep(wait)
        last[0] = time.time()
        try:
            request = urllib.request.Request(BASE + path + query,
                                             headers={"User-Agent": "ridges-dashboard-audit/1.0"})
            with urllib.request.urlopen(request, timeout=45) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as error:
            if error.code in (429, 503) and attempt < 4:
                time.sleep(2.0 * (attempt + 1))
                continue
            return {"__error__": "%s %s" % (error.code, error.reason)}
        except Exception as error:
            if attempt < 4:
                time.sleep(2.0)
                continue
            return {"__error__": repr(error)}

board = json.load(open("lb28.json"))[:20]
for row in board:
    target = OUT / ("%02d_%s.json" % (row["rank"], row["agent_id"]))
    if target.exists():
        print("cached", target.name); continue
    data = get("/retrieval/evaluations-for-agent", "?agent_id=" + row["agent_id"])
    target.write_text(json.dumps({"row": row, "evaluations": data}))
    n = len(data) if isinstance(data, list) else 0
    print("rank %2d %-10s evaluations=%d" % (row["rank"], (row.get("name") or "?")[:10], n), flush=True)
