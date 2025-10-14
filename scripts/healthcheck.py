#!/usr/bin/env python
"""Simple container healthcheck probing Flask readiness endpoint."""

import os
import sys
from urllib import request, error


def main() -> int:
    host = os.getenv("HEALTHCHECK_HOST", "127.0.0.1")
    port = os.getenv("PORT", os.getenv("APP_PORT", "5000"))
    target = f"http://{host}:{port}/readyz"
    try:
        with request.urlopen(target, timeout=5) as resp:
            if resp.status != 200:
                return 1
            return 0
    except error.URLError:
        return 1


if __name__ == "__main__":
    sys.exit(main())
