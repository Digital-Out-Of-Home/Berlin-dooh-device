#!/usr/bin/env python3
"""
Simple health check script to ping a URL.
Designed to be run by systemd timer every minute.
"""
import sys
import socket
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from config import load_config

def health_check():
    config = load_config()
    url = config.get("HEALTHCHECK_URL")
    
    if not url:
        print("No HEALTHCHECK_URL configured. Skipping.")
        return

    try:
        req = Request(url)
        with urlopen(req, timeout=10) as response:
            status = response.status
            print(f"Health check to {url} returned {status}")
    except HTTPError as e:
        print(f"Health check failed (HTTP {e.code}): {e.reason}", file=sys.stderr)
        sys.exit(1)
    except URLError as e:
        print(f"Health check connection failed: {e.reason}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Health check error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    health_check()
