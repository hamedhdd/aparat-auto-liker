"""
Configuration constants and selectors for Aparat Automation.
"""
from pathlib import Path

# Default Paths
BASE_DIR = Path(__file__).resolve().parent
DEFAULT_SCREENSHOT_DIR = BASE_DIR / "screenshots"

# Timeouts (in seconds)
PAGE_LOAD_TIMEOUT = 60
VIDEO_PLAYER_TIMEOUT = 30
MAX_AD_WAIT_SECONDS = 90
ELEMENT_APPEAR_TIMEOUT = 25
SETTLE_DELAY_SECONDS = 2

# Aparat Ad Selectors & Indicators
AD_VIDEO_URL_PATTERN = "aparat-ads"
SKIP_BUTTON_TEXTS = ["رد کردن", "رد کردن تبلیغ", "رد کردن آگهی", "Skip"]

# Like Button Selectors (Prioritized)
LIKE_SELECTORS = [
    # Button with aria-label containing like count or action (Persian)
    'button[aria-label*="پسند"]',
    '[role="button"][aria-label*="پسند"]',
    'button:has-text("پسند")',
    # Common Clover / Aparat action item class
    'button.action-item:first-of-type',
    # Button containing SVG heart icon
    'button:has(svg path[d*="M12"])',
]

# Ad Badge / Countdown Selectors
AD_OVERLAY_SELECTORS = [
    '.rp-ltr',
    '[class*="ad-title"]',
    '[class*="ad-caption"]',
    'button[class*="rp-z-[1000]"]',
]

# Skeletons
SKELETON_SELECTOR = ".button-skeleton"
