"""
Aparat Auto Liker & Screenshot Tool
-----------------------------------
Automates opening Aparat video links in Google Chrome, waiting for video ads
to finish (or skipping them), clicking the Like button, and capturing a clean screenshot
with the like button prominently visible.
"""
import sys
import time
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page

from config import (
    DEFAULT_SCREENSHOT_DIR,
    PAGE_LOAD_TIMEOUT,
    VIDEO_PLAYER_TIMEOUT,
    MAX_AD_WAIT_SECONDS,
    DEFAULT_THEME,
    INCLUDE_ADDRESS_BAR_DEFAULT,
)
from utils import (
    extract_video_id,
    wait_for_ad_completion,
    find_and_click_like_button,
    capture_screenshot_with_like_button,
)

# Ensure proper unicode terminal handling on Windows
if sys.stdout:
    sys.stdout.reconfigure(encoding="utf-8")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("AparatLiker")


def process_video_url(
    context: BrowserContext,
    url: str,
    output_dir: Path,
    auto_skip: bool = True,
    ad_timeout: int = MAX_AD_WAIT_SECONDS,
    include_address_bar: bool = INCLUDE_ADDRESS_BAR_DEFAULT,
) -> bool:
    """
    Processes a single Aparat video URL:
    1. Opens URL in Chrome tab.
    2. Waits for ad to finish (or skips it).
    3. Clicks Like button.
    4. Takes a screenshot with like button visible at bottom of frame,
       including Chrome dark address bar at the top.
    """
    logger.info(f"==> Navigating to video: {url}")
    video_id = extract_video_id(url)
    page: Optional[Page] = None

    try:
        page = context.new_page()
        # Set viewport for crisp desktop presentation
        page.set_viewport_size({"width": 1440, "height": 900})

        # Load page
        page.goto(url, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT * 1000)

        # Wait for video player initialization
        try:
            page.wait_for_selector("video", timeout=VIDEO_PLAYER_TIMEOUT * 1000)
            logger.info("Video player loaded.")
        except Exception:
            logger.warning("Video player selector not detected immediately; continuing...")

        # 1. Wait until the ad ends (or auto-skip it)
        wait_for_ad_completion(page, timeout=ad_timeout, auto_skip=auto_skip)

        # Small settle delay for page elements
        time.sleep(2)

        # 2. Click like button
        success, like_info = find_and_click_like_button(page)
        if not success:
            logger.warning(f"Could not confirm like button action for {url}")
        else:
            logger.info(f"Successfully liked video ({like_info})")

        # 3. Take screenshot with address bar and bottom-aligned like button
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_filename = f"aparat_{video_id}_{timestamp}.png"
        screenshot_path = output_dir / screenshot_filename

        saved_path = capture_screenshot_with_like_button(
            page=page,
            output_path=screenshot_path,
            url=url,
            include_address_bar=include_address_bar,
        )
        logger.info(f"==> [SUCCESS] Screenshot saved: {saved_path.resolve()}\n")
        return True

    except Exception as e:
        logger.error(f"Error processing {url}: {e}", exc_info=True)
        return False

    finally:
        if page:
            try:
                page.close()
            except Exception:
                pass


def run(
    urls: List[str],
    output_dir: Path,
    headless: bool = False,
    user_data_dir: Optional[str] = None,
    auto_skip: bool = True,
    ad_timeout: int = MAX_AD_WAIT_SECONDS,
    theme: str = DEFAULT_THEME,
    include_address_bar: bool = INCLUDE_ADDRESS_BAR_DEFAULT,
):
    """Launches Chrome via Playwright and executes liking workflow for all URLs."""
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Starting Aparat Auto-Liker for {len(urls)} link(s)")
    logger.info(f"Theme: {theme} | Headless: {headless} | Auto-skip ads: {auto_skip} | Address bar: {include_address_bar}")
    logger.info(f"Screenshots directory: {output_dir.resolve()}")

    chrome_args = ["--disable-blink-features=AutomationControlled"]
    if theme == "dark":
        chrome_args.extend(["--force-dark-mode", "--enable-features=WebContentsForceDark"])

    with sync_playwright() as p:
        # Launch using Google Chrome channel, with fallback to bundled Chromium
        if user_data_dir:
            logger.info(f"Using persistent Chrome user data directory: {user_data_dir}")
            try:
                context = p.chromium.launch_persistent_context(
                    user_data_dir=user_data_dir,
                    channel="chrome",
                    headless=headless,
                    args=chrome_args + ["--start-maximized"],
                    color_scheme=theme,
                    viewport=None,
                )
            except Exception:
                logger.info("Chrome channel unavailable; using default Chromium for persistent context...")
                context = p.chromium.launch_persistent_context(
                    user_data_dir=user_data_dir,
                    headless=headless,
                    args=chrome_args + ["--start-maximized"],
                    color_scheme=theme,
                    viewport=None,
                )
            browser = None
        else:
            try:
                browser = p.chromium.launch(
                    channel="chrome",
                    headless=headless,
                    args=chrome_args,
                )
            except Exception:
                logger.info("Chrome channel unavailable; falling back to bundled Chromium...")
                browser = p.chromium.launch(
                    headless=headless,
                    args=chrome_args,
                )
            context = browser.new_context(
                viewport={"width": 1440, "height": 900},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                color_scheme=theme,
            )

        # Pre-set Aparat dark theme cookie
        context.add_cookies([
            {"name": "theme", "value": theme, "domain": ".aparat.com", "path": "/"}
        ])

        for index, url in enumerate(urls, start=1):
            logger.info(f"[{index}/{len(urls)}] Processing {url}")
            process_video_url(
                context=context,
                url=url.strip(),
                output_dir=output_dir,
                auto_skip=auto_skip,
                ad_timeout=ad_timeout,
                include_address_bar=include_address_bar,
            )

        # Cleanup
        context.close()
        if browser:
            browser.close()

    logger.info("All tasks completed.")


def main():
    parser = argparse.ArgumentParser(
        description="Open Aparat video in Google Chrome, wait for advertisement, click Like, and save screenshot."
    )
    parser.add_argument(
        "urls",
        nargs="*",
        default=["https://www.aparat.com/v/ovw9yg1"],
        help="One or more Aparat video URLs (default: https://www.aparat.com/v/ovw9yg1)",
    )
    parser.add_argument(
        "--file",
        "-f",
        type=str,
        default=None,
        help="Path to a text file containing Aparat video URLs (one per line)",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=str,
        default=str(DEFAULT_SCREENSHOT_DIR),
        help=f"Directory to save screenshots (default: {DEFAULT_SCREENSHOT_DIR})",
    )
    parser.add_argument(
        "--theme",
        type=str,
        default=DEFAULT_THEME,
        choices=["dark", "light"],
        help=f"Browser theme (default: {DEFAULT_THEME})",
    )
    parser.add_argument(
        "--no-address-bar",
        action="store_true",
        default=False,
        help="Do not include the Chrome address bar at the top of the screenshot",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=False,
        help="Run Chrome in headless mode (default: False, runs visible Chrome window)",
    )
    parser.add_argument(
        "--user-data-dir",
        "-u",
        type=str,
        default=None,
        help="Path to existing Chrome User Data directory to reuse your logged-in Aparat session",
    )
    parser.add_argument(
        "--no-skip",
        action="store_true",
        default=False,
        help="Do not auto-click 'Skip Ad' button; wait for the full advertisement duration to elapse",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=MAX_AD_WAIT_SECONDS,
        help=f"Max seconds to wait for ad completion (default: {MAX_AD_WAIT_SECONDS})",
    )

    args = parser.parse_args()

    # Collect URLs
    targets = []
    if args.file:
        file_path = Path(args.file)
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                targets = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        else:
            logger.error(f"URLs file not found: {file_path}")
            sys.exit(1)
    else:
        targets = args.urls

    run(
        urls=targets,
        output_dir=Path(args.output_dir),
        headless=args.headless,
        user_data_dir=args.user_data_dir,
        auto_skip=not args.no_skip,
        ad_timeout=args.timeout,
        theme=args.theme,
        include_address_bar=not args.no_address_bar,
    )


if __name__ == "__main__":
    main()
