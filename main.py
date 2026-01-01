#!/usr/bin/env python3
"""VLC Playlist Manager. Usage: python main.py [sync|play]"""

import shutil, subprocess, sys, tempfile, zipfile
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.request import Request, build_opener, HTTPCookieProcessor, HTTPRedirectHandler

DROPBOX_URL = "https://www.dropbox.com/scl/fo/c98dl5jsxp3ae90yx9ww4/AD3YT1lVanI36T3pUaN_crU?rlkey=fzm1pc1qyhl4urkfo7kk3ftss&st=846rj2qj&dl=1"
BASE_DIR = Path(__file__).parent
MEDIA_DIR = BASE_DIR / "media"
TEMP_DIR = BASE_DIR / ".media_temp"
VLC = Path("/Applications/VLC.app/Contents/MacOS/VLC") if sys.platform == "darwin" else Path("/usr/bin/vlc")


def sync():
    """Download from Dropbox and atomic swap."""
    shutil.rmtree(TEMP_DIR, ignore_errors=True)
    TEMP_DIR.mkdir(parents=True)
    
    print("Downloading...")
    opener = build_opener(HTTPCookieProcessor(CookieJar()), HTTPRedirectHandler())
    req = Request(DROPBOX_URL, headers={"User-Agent": "Mozilla/5.0"})
    
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        f.write(opener.open(req, timeout=300).read())
        zip_path = Path(f.name)
    
    print("Extracting...")
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            if info.is_dir() or info.filename.startswith("."): continue
            parts = Path(info.filename).parts
            name = Path(*parts[1:]) if len(parts) > 1 else Path(info.filename)
            if name.name.startswith("."): continue
            dest = TEMP_DIR / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(zf.read(info))
            print(f"  {name.name}")
    zip_path.unlink()
    
    # Create local playlist
    for m3u in TEMP_DIR.glob("*.m3u"):
        lines = []
        for line in m3u.read_text().splitlines():
            if line.startswith("#") or not line.strip():
                lines.append(line)
            else:
                lines.append(str(MEDIA_DIR / Path(line).name))
        (TEMP_DIR / "playlist_local.m3u").write_text("\n".join(lines))
        break
    
    # Atomic swap
    shutil.rmtree(MEDIA_DIR, ignore_errors=True)
    TEMP_DIR.rename(MEDIA_DIR)
    print(f"Synced to {MEDIA_DIR}")


def play():
    """Play playlist with VLC."""
    playlist = MEDIA_DIR / "playlist_local.m3u"
    if not playlist.exists():
        playlist = next(MEDIA_DIR.glob("*.m3u"), None)
    if not playlist:
        sys.exit("No playlist found. Run: python main.py sync")
    print(f"Playing {playlist}")
    subprocess.run([str(VLC), "--loop", str(playlist)])


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "sync"
    {"sync": sync, "play": play}.get(cmd, lambda: print("Usage: python main.py [sync|play]"))()

