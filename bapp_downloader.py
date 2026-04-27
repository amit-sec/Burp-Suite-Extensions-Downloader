#!/usr/bin/env python3
"""
BApp Store Bulk Downloader
Scrapes the PortSwigger BApp Store, extracts all extension names and hashes,
then downloads each .bapp file with a clean human-readable filename.

Usage:
    python3 bapp_downloader.py                        # Download all extensions
    python3 bapp_downloader.py --list-only            # Just print name/hash mapping
    python3 bapp_downloader.py --output ./bapps       # Custom output folder
    python3 bapp_downloader.py --filter "JWT,GraphQL" # Download only matching names
    python3 bapp_downloader.py --delay 1.5            # Seconds between requests (be polite)
"""

import re
import os
import sys
import time
import json
import argparse
import urllib.request
import urllib.error
from html.parser import HTMLParser


BAPP_STORE_URL = "https://portswigger.net/bappstore"
DOWNLOAD_BASE  = "https://portswigger.net/bappstore/bapps/download"
DETAIL_BASE    = "https://portswigger.net/bappstore"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


# ──────────────────────────────────────────────
# 1. HTML parser: extract links from the listing page
# ──────────────────────────────────────────────
class BAppListParser(HTMLParser):
    """Parse the BApp Store listing page to collect {hash: name} pairs."""

    def __init__(self):
        super().__init__()
        self.extensions = {}          # hash -> name
        self._in_link   = False
        self._current_hash = None
        self._capture  = False

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            attrs_dict = dict(attrs)
            href = attrs_dict.get("href", "")
            # Extension links look like /bappstore/<32-char-hash>
            match = re.search(r"/bappstore/([a-f0-9]{32})$", href)
            if match:
                self._current_hash = match.group(1)
                self._capture = True

    def handle_data(self, data):
        if self._capture and self._current_hash:
            text = data.strip()
            if text:
                self.extensions[self._current_hash] = text
                self._capture = False
                self._current_hash = None

    def handle_endtag(self, tag):
        if tag == "a":
            self._capture = False
            self._current_hash = None


# ──────────────────────────────────────────────
# 2. Detail page parser: get version number
# ──────────────────────────────────────────────
class BAppDetailParser(HTMLParser):
    """Parse a single BApp detail page to find version and download link."""

    def __init__(self):
        super().__init__()
        self.version       = None
        self.download_href = None
        self._next_is_ver  = False

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            attrs_dict = dict(attrs)
            href = attrs_dict.get("href", "")
            # Download link may be relative (/bappstore/bapps/download/<hash>/<ver>)
            # or absolute (https://portswigger.net/bappstore/bapps/download/<hash>/<ver>)
            match = re.search(r"/bappstore/bapps/download/([a-f0-9]{32})/(\d+)", href)
            if match:
                self.download_href = href
                self.version = match.group(2)


# ──────────────────────────────────────────────
# 3. Helpers
# ──────────────────────────────────────────────
def fetch(url, retries=3, timeout=30):
    req = urllib.request.Request(url, headers=HEADERS)
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            print(f"  HTTP {e.code} fetching {url} (attempt {attempt}/{retries})")
            if e.code in (403, 404):
                return None          # No point retrying
        except Exception as e:
            print(f"  Error fetching {url}: {e} (attempt {attempt}/{retries})")
        if attempt < retries:
            time.sleep(2 ** attempt)
    return None


def safe_filename(name):
    """Convert an extension name to a safe filename."""
    # Remove characters not safe for filenames
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    # Replace commas, slashes, and multiple spaces
    name = re.sub(r'[\s,]+', '_', name.strip())
    # Remove leading dots or dashes
    name = name.lstrip('.-')
    return name or "unknown"


def scrape_extension_list():
    """Fetch the BApp Store page and return {hash: display_name} dict."""
    print(f"[*] Fetching BApp Store listing: {BAPP_STORE_URL}")
    html = fetch(BAPP_STORE_URL)
    if not html:
        print("[-] Failed to fetch BApp Store page.")
        sys.exit(1)

    parser = BAppListParser()
    parser.feed(html.decode("utf-8", errors="replace"))

    if not parser.extensions:
        print("[-] No extensions found — the page structure may have changed.")
        sys.exit(1)

    print(f"[+] Found {len(parser.extensions)} extensions.")
    return parser.extensions


def get_download_info(ext_hash, delay=0.5):
    """Visit the detail page to get the versioned download URL."""
    url = f"{DETAIL_BASE}/{ext_hash}"
    html = fetch(url)
    if not html:
        return None, None

    parser = BAppDetailParser()
    parser.feed(html.decode("utf-8", errors="replace"))
    time.sleep(delay)
    return parser.download_href, parser.version


def download_bapp(download_href, dest_path):
    """Download a .bapp file to dest_path."""
    # download_href may already be a full URL or just a path — normalise it
    if download_href.startswith("http"):
        url = download_href
    else:
        url = f"https://portswigger.net{download_href}"
    data = fetch(url)
    if data is None:
        return False
    with open(dest_path, "wb") as f:
        f.write(data)
    return True


# ──────────────────────────────────────────────
# 4. Main
# ──────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Bulk-download all BApp Store extensions with clean filenames.")
    parser.add_argument("--output",    default="./bapps",  help="Output folder (default: ./bapps)")
    parser.add_argument("--delay",     type=float, default=1.0, help="Seconds between requests (default: 1.0)")
    parser.add_argument("--list-only", action="store_true",  help="Only print the extension list, don't download")
    parser.add_argument("--filter",    default="",          help="Comma-separated name substrings to download (e.g. 'JWT,GraphQL')")
    parser.add_argument("--resume",    action="store_true",  help="Skip files that already exist in output folder")
    parser.add_argument("--save-map",  action="store_true",  help="Save hash->name mapping as extensions_map.json")
    args = parser.parse_args()

    # Step 1: Scrape listing
    extensions = scrape_extension_list()

    # Apply filter if given
    filters = [f.strip().lower() for f in args.filter.split(",") if f.strip()]
    if filters:
        extensions = {
            h: n for h, n in extensions.items()
            if any(f in n.lower() for f in filters)
        }
        print(f"[*] After filter: {len(extensions)} extensions match.")

    # List-only mode
    if args.list_only:
        print("\n{:<36} {}".format("HASH", "NAME"))
        print("-" * 80)
        for h, name in sorted(extensions.items(), key=lambda x: x[1].lower()):
            print(f"{h}  {name}")
        return

    # Save map if requested
    if args.save_map:
        map_path = os.path.join(args.output, "extensions_map.json")
        os.makedirs(args.output, exist_ok=True)
        with open(map_path, "w") as f:
            json.dump(extensions, f, indent=2)
        print(f"[+] Saved extension map to {map_path}")

    # Step 2: Download
    os.makedirs(args.output, exist_ok=True)
    total   = len(extensions)
    success = 0
    skipped = 0
    failed  = []

    print(f"\n[*] Downloading {total} extensions to: {os.path.abspath(args.output)}\n")

    for idx, (ext_hash, name) in enumerate(sorted(extensions.items(), key=lambda x: x[1].lower()), 1):
        safe_name = safe_filename(name)
        dest_path = os.path.join(args.output, f"{safe_name}.bapp")

        print(f"[{idx:>3}/{total}] {name}")

        # Resume: skip existing
        if args.resume and os.path.exists(dest_path):
            print(f"         -> Skipping (already exists): {safe_name}.bapp")
            skipped += 1
            continue

        # Get versioned download URL from detail page
        download_href, version = get_download_info(ext_hash, delay=args.delay)

        if not download_href:
            print(f"         -> Could not find download link, skipping.")
            failed.append(name)
            continue

        print(f"         -> Downloading v{version} as '{safe_name}.bapp' ...")
        ok = download_bapp(download_href, dest_path)

        if ok:
            size_kb = os.path.getsize(dest_path) / 1024
            print(f"         -> Saved ({size_kb:.1f} KB)")
            success += 1
        else:
            print(f"         -> Download failed!")
            failed.append(name)

        time.sleep(args.delay)

    # Summary
    print(f"\n{'='*60}")
    print(f"  Done. {success}/{total} downloaded, {skipped} skipped.")
    if failed:
        print(f"  Failed ({len(failed)}):")
        for f in failed:
            print(f"    - {f}")
    print(f"  Files saved to: {os.path.abspath(args.output)}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()