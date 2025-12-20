#!/usr/bin/env python3
import sys
from playwright.sync_api import sync_playwright

def get_final_url(passerelle_url):
    """Get final redirected URL from passerelle URL using Playwright"""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(passerelle_url, wait_until="networkidle")
            final_url = page.url
            browser.close()
            return final_url
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return None

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python get_final_url.py <passerelle_url>")
        sys.exit(1)
    
    passerelle_url = sys.argv[1]
    final_url = get_final_url(passerelle_url)
    if final_url:
        print(final_url)
    else:
        sys.exit(1)
