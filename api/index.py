"""Vercel Serverless Function entrypoint for Aetheria Labs Stripe 2026 Reference Store."""

import os
import sys

# Ensure root directory is in sys.path so server.py can be imported in Vercel runtime
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from server import StripeDemoHandler  # noqa: E402


class handler(StripeDemoHandler):
    """Vercel @vercel/python BaseHTTPRequestHandler entrypoint."""

    pass
