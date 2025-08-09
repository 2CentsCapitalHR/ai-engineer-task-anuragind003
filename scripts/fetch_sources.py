from __future__ import annotations

import os
import json
import time
import re
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

ROOT = os.path.dirname(os.path.dirname(__file__))
REF_DIR = os.path.join(ROOT, "references")
RAW_DIR = os.path.join(REF_DIR, "raw")


CT_EXT = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "text/html": ".html",
}


def safe_filename(url: str) -> str:
    parsed = urlparse(url)
    name = os.path.basename(parsed.path) or re.sub(r"\W+", "-", parsed.netloc)
    return name.replace("%20", "_").replace("+", "_")


def guess_filename(url: str, response: requests.Response) -> str:
    # Prefer filename from Content-Disposition if present
    cd = response.headers.get("Content-Disposition", "")
    m = re.search(r"filename\*=UTF-8''([^;]+)", cd)
    if m:
        return os.path.basename(m.group(1))
    m = re.search(r'filename="?([^";]+)"?', cd)
    if m:
        return os.path.basename(m.group(1))

    base = safe_filename(url)
    ext = os.path.splitext(base)[1].lower()
    if not ext:
        ct = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
        ext = CT_EXT.get(ct, "")
        if not ext and (url.endswith("/") or not os.path.splitext(urlparse(url).path)[1]):
            # Likely HTML page
            ext = ".html"
        base = base + ext if ext else base
    return base


def fetch(url: str, timeout: int = 40) -> requests.Response:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; ADGM-Agent/1.0)"}
    r = requests.get(url, headers=headers, timeout=timeout)
    r.raise_for_status()
    return r


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    # Remove scripts/styles
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text("\n")
    lines = [ln.strip() for ln in text.splitlines()]
    text = "\n".join([ln for ln in lines if ln])
    return text


def run() -> None:
    os.makedirs(RAW_DIR, exist_ok=True)
    sources_path = os.path.join(REF_DIR, "sources.json")
    if not os.path.exists(sources_path):
        raise SystemExit("references/sources.json not found.")

    with open(sources_path, "r", encoding="utf-8") as f:
        sources = json.load(f)

    for item in sources:
        url = item.get("url")
        if not url:
            continue
        try:
            resp = fetch(url)
            fname = guess_filename(url, resp)
            raw_path = os.path.join(RAW_DIR, fname)
            with open(raw_path, "wb") as f:
                f.write(resp.content)
            ext = os.path.splitext(fname)[1].lower()
            if ext in {".html", ".htm"}:
                try:
                    text = html_to_text(resp.content.decode("utf-8", errors="ignore"))
                    out_txt = os.path.join(REF_DIR, f"{os.path.splitext(fname)[0]}.txt")
                    with open(out_txt, "w", encoding="utf-8") as tf:
                        tf.write(text)
                except Exception:
                    pass
            print(f"Downloaded {url} → {raw_path}")
            time.sleep(0.6)
        except Exception as e:
            print(f"Failed {url}: {e}")


if __name__ == "__main__":
    run()
