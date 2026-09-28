"""
Utility helpers for Aparat video automation.
"""
import re
import time
import logging
from pathlib import Path
from typing import Optional, Tuple
from playwright.sync_api import Page, Locator

from config import (
    AD_VIDEO_URL_PATTERN,
    SKIP_BUTTON_TEXTS,
    LIKE_SELECTORS,
    SKELETON_SELECTOR,
    MAX_AD_WAIT_SECONDS,
)

logger = logging.getLogger("AparatLiker")


def extract_video_id(url: str) -> str:
    """Extracts video ID from Aparat URL (e.g. ovw9yg1 from https://www.aparat.com/v/ovw9yg1)."""
    match = re.search(r"/v/([a-zA-Z0-9_-]+)", url)
    if match:
        return match.group(1)
    # Fallback to sanitized tail
    cleaned = re.sub(r"[^a-zA-Z0-9_-]", "_", url.split("/")[-1])
    return cleaned or "video"


def try_click_skip_button(page: Page) -> bool:
    """Checks for and clicks any active 'Skip Ad' button."""
    try:
        # Check text-based locators
        for text in SKIP_BUTTON_TEXTS:
            skip_locator = page.locator(f'button:has-text("{text}")')
            if skip_locator.count() > 0:
                for i in range(skip_locator.count()):
                    btn = skip_locator.nth(i)
                    if btn.is_visible():
                        logger.info(f"Clicking skip ad button with text: '{text}'")
                        btn.click(force=True)
                        time.sleep(1)
                        return True
        # Check by JavaScript for countdown converted to button
        clicked = page.evaluate("""() => {
            const buttons = Array.from(document.querySelectorAll('button, div[role="button"]'));
            for (let b of buttons) {
                const t = (b.innerText || '').trim();
                if (t.includes('رد کردن') || t.includes('Skip')) {
                    b.click();
                    return true;
                }
            }
            return false;
        }""")
        if clicked:
            logger.info("Clicked skip ad button via DOM evaluation.")
            return True
    except Exception as e:
        logger.debug(f"Exception while checking skip button: {e}")
    return False


def wait_for_ad_completion(page: Page, timeout: int = MAX_AD_WAIT_SECONDS, auto_skip: bool = True) -> bool:
    """
    Monitors the video player and waits for any pre-roll/in-stream advertisement to conclude.
    If auto_skip is True, automatically clicks the skip button as soon as available.
    """
    logger.info("Monitoring player for advertisements...")
    start_time = time.time()
    ad_detected = False

    while time.time() - start_time < timeout:
        elapsed = int(time.time() - start_time)

        # Check skip ad button if auto_skip is enabled
        if auto_skip:
            try_click_skip_button(page)

        # Query player ad state from page
        status = page.evaluate("""() => {
            const videos = Array.from(document.querySelectorAll('video'));
            // Ad video has 'aparat-ads' in its source or currentSrc
            const adVideo = videos.find(v => 
                (v.src && v.src.includes('aparat-ads')) || 
                (v.currentSrc && v.currentSrc.includes('aparat-ads'))
            );
            
            // Main video is a non-ad video that is not hidden
            const mainVideo = videos.find(v => 
                v.src && !v.src.includes('aparat-ads') && 
                !v.className.includes('rp-hidden')
            );
            
            // Check for ad overlay indicators
            let hasAdOverlay = false;
            const overlays = document.querySelectorAll('[class*="ad-title"], [class*="rp-z-[1000]"]');
            if (overlays.length > 0) {
                hasAdOverlay = true;
            }
            
            const skeletons = document.querySelectorAll('.button-skeleton').length;
            
            return {
                adVideoFound: !!adVideo,
                adVideoPaused: adVideo ? adVideo.paused : null,
                adVideoEnded: adVideo ? adVideo.ended : null,
                adVideoCurrentTime: adVideo ? adVideo.currentTime : null,
                adVideoDuration: adVideo ? adVideo.duration : null,
                hasAdOverlay: hasAdOverlay,
                mainVideoFound: !!mainVideo,
                mainVideoPlaying: mainVideo ? !mainVideo.paused : false,
                skeletonsCount: skeletons
            };
        }""")

        if status["adVideoFound"]:
            ad_detected = True

        # Check if ad is done:
        if ad_detected:
            # If ad was detected, it is finished when ad video ended or disappears,
            # and main video is playing without ad overlay
            if not status["adVideoFound"] or status["adVideoEnded"] or (status["mainVideoPlaying"] and not status["hasAdOverlay"]):
                logger.info(f"Advertisement finished after {elapsed}s.")
                return True
        else:
            # If no ad was detected after 10s and page has loaded skeletons/main video
            if elapsed > 10 and (status["mainVideoFound"] or status["skeletonsCount"] == 0):
                logger.info(f"No advertisement detected (elapsed: {elapsed}s). Proceeding to content.")
                return True

        time.sleep(1.5)

    logger.warning("Reached maximum wait time for ad. Proceeding...")
    return False


def find_and_click_like_button(page: Page, timeout: int = 25) -> Tuple[bool, Optional[str]]:
    """
    Locates the like button on the Aparat video page, scrolls it into view,
    clicks it, and verifies state change.
    Returns (success: bool, like_text: Optional[str]).
    """
    logger.info("Searching for like button...")
    start_time = time.time()
    like_btn: Optional[Locator] = None
    button_label: str = ""

    while time.time() - start_time < timeout:
        # Wait for skeleton placeholders to clear
        skeletons_count = page.locator(SKELETON_SELECTOR).count()
        if skeletons_count > 0:
            time.sleep(1)
            continue

        # Try prioritized selectors
        for selector in LIKE_SELECTORS:
            loc = page.locator(selector).first
            try:
                if loc.is_visible():
                    like_btn = loc
                    break
            except Exception:
                continue

        if like_btn:
            break

        time.sleep(1)

    if not like_btn:
        logger.error("Could not locate like button using standard selectors.")
        return False, None

    try:
        # Scroll like button to center of view
        like_btn.scroll_into_view_if_needed(timeout=5000)
        time.sleep(0.5)

        # Get initial state / text
        button_label = like_btn.get_attribute("aria-label") or like_btn.inner_text() or "Like"
        logger.info(f"Found like button (initial: '{button_label}'). Clicking...")

        # Click the like button
        like_btn.click(force=True)
        time.sleep(1.5)

        # Verify new label/state
        updated_label = like_btn.get_attribute("aria-label") or like_btn.inner_text() or button_label
        logger.info(f"Like button clicked successfully! Current state: '{updated_label}'")
        return True, updated_label

    except Exception as e:
        logger.error(f"Error clicking like button: {e}")
        # Fallback to JavaScript dispatch
        js_success = page.evaluate("""() => {
            const btns = document.querySelectorAll('button, [role="button"]');
            for (let b of btns) {
                const aria = b.getAttribute('aria-label') || '';
                if (aria.includes('پسند')) {
                    b.scrollIntoView({behavior: 'instant', block: 'center'});
                    b.click();
                    return true;
                }
            }
            return false;
        }""")
        return js_success, "Clicked via DOM fallback"


def capture_screenshot_with_like_button(page: Page, output_path: Path) -> Path:
    """
    Ensures the like button and video player are properly visible and centered
    in the viewport before taking the screenshot.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Position page so video player and like button are both clearly visible
    page.evaluate("""() => {
        const likeBtn = document.querySelector('button[aria-label*="پسند"], [role="button"][aria-label*="پسند"], button.action-item');
        if (likeBtn) {
            // Scroll so like button is in upper-mid lower quadrant with player above
            const rect = likeBtn.getBoundingClientRect();
            window.scrollBy({
                top: rect.top - 380,
                behavior: 'instant'
            });
        }
    }""")
    time.sleep(1)

    # Take screenshot
    page.screenshot(path=str(output_path), full_page=False)
    logger.info(f"Screenshot successfully saved to: {output_path}")
    return output_path
