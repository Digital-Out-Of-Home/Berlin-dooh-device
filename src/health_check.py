#!/usr/bin/env python3
"""
Simple health check script to ping a URL.
Designed to be run by systemd timer every minute.
"""
import logging
import sys
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from config import load_config, setup_logging

setup_logging()
logger = logging.getLogger(__name__)


def health_check():
    config = load_config()
    url = config.get("HEALTHCHECK_URL")

    if not url:
        logger.debug("No HEALTHCHECK_URL configured. Skipping.")
        return

    try:
        req = Request(url)
        with urlopen(req, timeout=10) as response:
            status = response.status
            if status == 200:
                logger.debug("Health check to %s returned %s", url, status)
            else:
                logger.warning("Health check to %s returned %s", url, status)
    except HTTPError as e:
        logger.error("Health check failed (HTTP %s): %s", e.code, e.reason)
        sys.exit(1)
    except URLError as e:
        logger.error("Health check connection failed: %s", e.reason)
        sys.exit(1)
    except Exception as e:
        logger.error("Health check error: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    health_check()
