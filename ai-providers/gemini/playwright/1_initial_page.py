import time
from typing import Any, List, Tuple
from playwright.sync_api import sync_playwright

from google import genai
from google.genai import types
from google.genai.types import Content, Part

from google import genai
import os

# Constants for screen dimensions
SCREEN_WIDTH = 1440
SCREEN_HEIGHT = 900

# Setup Playwright
print("Initializing browser...")
playwright = sync_playwright().start()
browser = playwright.chromium.launch(headless=False)
context = browser.new_context(viewport={"width": SCREEN_WIDTH, "height": SCREEN_HEIGHT})
page = context.new_page()

try:
    # Go to initial page
    page.goto("https://ai.google.dev/gemini-api/docs")
    
    # Initialize history
    initial_screenshot = page.screenshot(type="png")
    with open("initial_screenshot.png", "wb") as f:
        f.write(initial_screenshot)   
finally:
    # Cleanup
    print("\nClosing browser...")
    browser.close()
    playwright.stop()       