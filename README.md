# BApp Store Bulk Downloader

A zero-dependency Python script that downloads all [PortSwigger BApp Store](https://portswigger.net/bappstore) extensions with **clean, human-readable filenames** instead of the hash-based names returned by the server.

Designed for air-gapped / offline environments where you need to mirror all Burp Suite extensions on an internet-connected machine first, then transfer them.

---

## The Problem

When you download a BApp extension manually, the server returns a file named after its internal hash:

```
e2a137ad44984ccb908375fa5b2c618d
```

With 400+ extensions this becomes unmanageable. This script maps each hash to its display name and saves files as:

```
NET_Beautifier.bapp
JWT_Editor.bapp
Logger++.bapp
Param_Miner.bapp
...
```

---

## Requirements

- Python 3.6+
- No third-party packages — uses only the standard library (`urllib`, `html.parser`, `argparse`, `json`)

---

## Usage

```bash
# Download all 400+ extensions to ./bapps
python bapp_downloader.py

# Preview what would be downloaded (no files written)
python bapp_downloader.py --list-only

# Custom output folder
python bapp_downloader.py --output /path/to/folder

# Download only extensions whose names contain these keywords
python bapp_downloader.py --filter "JWT,GraphQL,Logger"

# Resume an interrupted download (skips already-downloaded files)
python bapp_downloader.py --resume

# Save a JSON map of hash -> name alongside the downloads
python bapp_downloader.py --save-map

# Slow down requests to be polite to the server (default: 1.0s)
python bapp_downloader.py --delay 2.0

# Combine options
python bapp_downloader.py --output ./bapps --resume --save-map --delay 1.5
```

---

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--output DIR` | `./bapps` | Folder to save `.bapp` files into |
| `--delay SECS` | `1.0` | Seconds to wait between requests |
| `--list-only` | off | Print all extension names and hashes, then exit |
| `--filter "A,B"` | (all) | Only download extensions whose names contain any of these substrings (case-insensitive) |
| `--resume` | off | Skip files that already exist in the output folder |
| `--save-map` | off | Write `extensions_map.json` (hash → name) to the output folder |

---

## Example Output

```
[*] Fetching BApp Store listing: https://portswigger.net/bappstore
[+] Found 421 extensions.

[*] Downloading 421 extensions to: C:\Users\you\Downloads\burp\bapps

[  1/421] .NET Beautifier
         -> Downloading v3 as 'NET_Beautifier.bapp' ...
         -> Saved (12.4 KB)
[  2/421] 403 Bypasser
         -> Downloading v1 as '403_Bypasser.bapp' ...
         -> Saved (8.1 KB)
...

============================================================
  Done. 421/421 downloaded, 0 skipped.
  Files saved to: C:\Users\you\Downloads\burp\bapps
============================================================
```

---

## Installing Extensions Offline in Burp Suite

Once you have the `.bapp` files on your air-gapped machine:

1. Open Burp Suite
2. Go to **Extensions** → **Installed** → **Add**
3. Set **Extension type** to `Java` (most BApps) or `Python` / `Ruby` as needed
4. Browse to the `.bapp` file and click **Next**

> **Note:** Some extensions require Jython (for Python extensions) or JRuby (for Ruby extensions) to be configured under **Extensions** → **Extension Settings** before they will load.

---

## How It Works

1. **Scrape the listing page** — parses `/bappstore` to extract every extension's display name and 32-character hash from its anchor link.
2. **Visit each detail page** — fetches `/bappstore/<hash>` to find the versioned download URL (`/bappstore/bapps/download/<hash>/<version>`).
3. **Download and rename** — saves each file as `<SafeName>.bapp`, sanitising characters that are invalid in Windows/Linux filenames.

---

## File Naming

Special characters are stripped or replaced to produce safe cross-platform filenames:

| Input name | Saved as |
|---|---|
| `.NET Beautifier` | `NET_Beautifier.bapp` |
| `Logger++` | `Logger++.bapp` |
| `InQL - GraphQL Scanner` | `InQL_-_GraphQL_Scanner.bapp` |
| `JSON Web Tokens` | `JSON_Web_Tokens.bapp` |

---

## Disclaimer

This tool is for **personal/organisational archival use** in environments without internet access. Extensions are written by third-party authors; PortSwigger makes no warranty about their quality. Always review extensions before loading them into Burp Suite.

---

## License

MIT
