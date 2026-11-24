#!/usr/bin/env python3
"""Submit only changed public URLs after the matching sitemap and key are live."""
import json, os, pathlib, subprocess, time, urllib.request, urllib.error
import xml.etree.ElementTree as ET
BASE = "https://zykina-art.ru"
KEY = "b8cf201da6354c28941e7c36f0a9d752"
NS = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9", "i": "http://www.google.com/schemas/sitemap-image/1.1"}
def sitemap(raw):
    root = ET.fromstring(raw)
    return {n.findtext("s:loc", namespaces=NS): sorted(set(n.findall("i:image/i:loc", NS)[i].text for i in range(len(n.findall("i:image/i:loc", NS))))) for n in root.findall("s:url", NS)}
def read_url(url):
    req = urllib.request.Request(url, headers={"User-Agent":"ZYKINA-ART-IndexNow/1.0","Cache-Control":"no-cache"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read()
current = sitemap(pathlib.Path("public/sitemap.xml").read_bytes())
if not current or any(not u.startswith(BASE + "/") for u in current):
    raise SystemExit("Invalid sitemap")
before = os.environ.get("BEFORE", "")
manual = os.environ.get("EVENT_NAME") == "workflow_dispatch"
if manual or not before or set(before) == {"0"}:
    urls = set(current)
else:
    prior = subprocess.run(["git","show",before+":public/sitemap.xml"], capture_output=True)
    if prior.returncode:
        raise SystemExit("Previous sitemap not available; use manual workflow")
    old = sitemap(prior.stdout)
    urls = {u for u in set(old) | set(current) if old.get(u) != current.get(u)}
    changes = subprocess.check_output(["git","diff","--name-only",before,"HEAD"],text=True).splitlines()
    for path in changes:
        if path == "public/index.html":
            urls.add(BASE+"/")
        elif path.startswith("public/") and path.endswith("/index.html"):
            url=BASE+"/"+path[len("public/"):-len("index.html")]
            if url in current or url in old:
                urls.add(url)
        elif path.startswith("public/assets/"):
            for url, images in current.items():
                from urllib.parse import unquote
                if any(unquote(img[len(BASE):]) == "/"+path[len("public/"):] for img in images):
                    urls.add(url)
if not urls:
    print("No indexable changes")
    raise SystemExit(0)
for attempt in range(18):
    try:
        live = sitemap(read_url(BASE+"/sitemap.xml"))
        key = read_url(BASE+"/"+KEY+".txt").decode().strip()
        if live == current and key == KEY:
            break
        print("Published sitemap or key differs; waiting for MCHost sync", flush=True)
    except Exception as exc:
        print("Site verification:", exc, flush=True)
    time.sleep(45)
else:
    raise SystemExit("Live deployment not verified. No URLs submitted.")
payload=json.dumps({"host":"zykina-art.ru","key":KEY,"keyLocation":BASE+"/"+KEY+".txt","urlList":sorted(urls)}).encode()
req=urllib.request.Request("https://yandex.com/indexnow",data=payload,headers={"Content-Type":"application/json; charset=utf-8","User-Agent":"ZYKINA-ART-IndexNow/1.0"},method="POST")
with urllib.request.urlopen(req,timeout=30) as r:
    print("IndexNow HTTP",r.status,"URLs:",len(urls))
    if r.status not in (200,202):
        raise SystemExit("IndexNow did not accept the notification")
