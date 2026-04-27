"""Refresh now-playing.svg + README link with current Spotify track."""
import base64
import os
import re
import sys
from html import escape
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
SVG_PATH = ROOT / "now-playing.svg"
README_PATH = ROOT / "README.md"

TITLE_MAX = 38
ARTIST_MAX = 32


def truncate(s, n):
    s = s.strip()
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def get_access_token():
    cid = os.environ["SPOTIFY_CLIENT_ID"]
    secret = os.environ["SPOTIFY_CLIENT_SECRET"]
    refresh = os.environ["SPOTIFY_REFRESH_TOKEN"]
    auth = base64.b64encode(f"{cid}:{secret}".encode()).decode()
    r = requests.post(
        "https://accounts.spotify.com/api/token",
        headers={"Authorization": f"Basic {auth}"},
        data={"grant_type": "refresh_token", "refresh_token": refresh},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def get_track(token):
    """Try currently-playing, fall back to recently-played."""
    h = {"Authorization": f"Bearer {token}"}
    r = requests.get(
        "https://api.spotify.com/v1/me/player/currently-playing",
        headers=h,
        timeout=15,
    )
    if r.status_code == 200 and r.json().get("item"):
        item = r.json()["item"]
        return _parse_track(item, playing=r.json().get("is_playing", False))

    r = requests.get(
        "https://api.spotify.com/v1/me/player/recently-played?limit=1",
        headers=h,
        timeout=15,
    )
    r.raise_for_status()
    items = r.json().get("items", [])
    if not items:
        return None
    return _parse_track(items[0]["track"], playing=False)


def _parse_track(item, playing):
    return {
        "title": item["name"],
        "artist": ", ".join(a["name"] for a in item["artists"]),
        "url": item["external_urls"]["spotify"],
        "playing": playing,
    }


def update_svg(track):
    svg = SVG_PATH.read_text()
    title = escape(truncate(track["title"], TITLE_MAX))
    artist = escape(truncate(track["artist"], ARTIST_MAX))
    header = "Spotify Playing \u{1F3A7}" if track["playing"] else "Last Played \u{1F3A7}"

    svg = re.sub(
        r'(<text x="12" y="22"[^>]*>)[^<]*(</text>)',
        rf"\1{escape(header)}\2",
        svg,
        count=1,
    )
    svg = re.sub(
        r'(<text x="146" y="73"[^>]*>)[^<]*(</text>)',
        rf"\1{title}\2",
        svg,
        count=1,
    )
    svg = re.sub(
        r'(<text x="146" y="93"[^>]*>)[^<]*(</text>)',
        rf"\1{artist}\2",
        svg,
        count=1,
    )
    SVG_PATH.write_text(svg)


def update_readme(track):
    md = README_PATH.read_text()
    alt = f'{track["artist"]} - {track["title"]}'.replace('"', "'")
    md = re.sub(
        r'<a href="https://open\.spotify\.com/track/[^"]+">',
        f'<a href="{track["url"]}">',
        md,
        count=1,
    )
    md = re.sub(
        r'(<img src="now-playing\.svg" alt=")[^"]*(")',
        rf"\g<1>{alt}\g<2>",
        md,
        count=1,
    )
    README_PATH.write_text(md)


def main():
    token = get_access_token()
    track = get_track(token)
    if not track:
        print("nothing to update")
        return
    update_svg(track)
    update_readme(track)
    print(f"updated: {track['artist']} - {track['title']} (playing={track['playing']})")


if __name__ == "__main__":
    sys.exit(main())
