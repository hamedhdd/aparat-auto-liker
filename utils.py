"""
Utility helpers for Aparat video automation.
"""
import os
import re
import time
import logging
from pathlib import Path
from typing import Optional, Tuple
import io
from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import Page, Locator

from config import (
    AD_VIDEO_URL_PATTERN,
    SKIP_BUTTON_TEXTS,
    LIKE_SELECTORS,
    SKELETON_SELECTOR,
    MAX_AD_WAIT_SECONDS,
    LIKE_BUTTON_BOTTOM_OFFSET,
    INCLUDE_ADDRESS_BAR_DEFAULT,
)

logger = logging.getLogger("AparatLiker")


def get_browser_executable() -> Optional[str]:
    """Detects native Chrome or Chromium binary on Linux or Windows."""
    candidates = [
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


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
            
            // Check if skip button is present
            let hasSkipBtn = false;
            for (let b of document.querySelectorAll('button')) {
                const t = (b.innerText || '').trim();
                if (t.includes('رد کردن') || t.includes('ثانیه تا رد کردن')) {
                    hasSkipBtn = true;
                    break;
                }
            }
            
            const isAdEnded = !!(adVideo && (adVideo.ended || (adVideo.duration > 0 && adVideo.currentTime >= adVideo.duration - 0.5)));
            const isAdActive = !!(adVideo && !adVideo.paused && !adVideo.ended && (adVideo.currentTime < (adVideo.duration || 999)));
            const isMainPlaying = !!(mainVideo && !mainVideo.paused && mainVideo.currentTime > 0.5);
            const skeletons = document.querySelectorAll('.button-skeleton').length;
            
            return {
                adVideoFound: !!adVideo,
                isAdEnded: isAdEnded,
                isAdActive: isAdActive,
                hasSkipBtn: hasSkipBtn,
                mainVideoFound: !!mainVideo,
                isMainPlaying: isMainPlaying,
                skeletonsCount: skeletons
            };
        }""")

        if status["adVideoFound"] or status["hasSkipBtn"]:
            ad_detected = True

        # Check if ad is done:
        # 1. Main video has started active playback
        if status["isMainPlaying"]:
            logger.info(f"Main video playback confirmed ({elapsed}s). Advertisement finished.")
            return True
            
        # 2. If ad was detected, wait until it ends and main video begins
        if ad_detected:
            if status["isAdEnded"] or (not status["isAdActive"] and not status["hasSkipBtn"] and status["mainVideoFound"]):
                logger.info(f"Advertisement concluded after {elapsed}s.")
                # Give 1 second for main video transition
                time.sleep(1)
                return True
        else:
            # 3. If no ad was ever detected after 10s and page is fully ready
            if elapsed > 10 and (status["mainVideoFound"] or status["skeletonsCount"] == 0):
                logger.info(f"No advertisement detected (elapsed: {elapsed}s). Proceeding to content.")
                return True

        time.sleep(1.5)

    logger.warning("Reached maximum wait time for ad. Proceeding...")
    return False


def is_like_button_active(page: Page) -> bool:
    """Checks whether the like button is currently in the active/liked red state."""
    return page.evaluate("""() => {
        const b = document.querySelector('button[aria-label*="پسند"], [role="button"][aria-label*="پسند"], button.action-item');
        if (!b) return false;
        const hasFilled = !!b.querySelector('svg.icon-favoritefilled, svg[class*="favoritefilled"]');
        const style = window.getComputedStyle(b);
        const isRed = style.color === 'rgb(223, 15, 80)' || style.backgroundColor.includes('223, 15, 80');
        return hasFilled || isRed;
    }""")


def find_and_click_like_button(page: Page, timeout: int = 25) -> Tuple[bool, Optional[str]]:
    """
    Locates the like button on the Aparat video page, verifies whether it is already liked,
    scrolls it into view, clicks it, and confirms it turns to the active red/pink filled heart state.
    Returns (success: bool, like_text: Optional[str]).
    """
    logger.info("Searching for like button...")
    start_time = time.time()
    like_btn: Optional[Locator] = None

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

        # Check if already liked
        if is_like_button_active(page):
            button_label = like_btn.get_attribute("aria-label") or like_btn.inner_text() or "Liked"
            logger.info(f"Like button is already in active RED state ({button_label}).")
            return True, button_label

        button_label = like_btn.get_attribute("aria-label") or like_btn.inner_text() or "Like"
        logger.info(f"Found like button (initial: '{button_label}'). Clicking...")

        # Standard click on the button
        like_btn.click()

        # Wait up to 10 seconds for the button to turn RED with filled heart
        logger.info("Waiting for like button to turn RED (icon-favoritefilled)...")
        confirmed_red = False
        wait_start = time.time()
        while time.time() - wait_start < 10:
            if is_like_button_active(page):
                confirmed_red = True
                break
            time.sleep(0.5)

        # If still not red, try direct JS click
        if not confirmed_red:
            logger.warning("Red state not registered yet. Attempting direct JS click fallback...")
            page.evaluate("""() => {
                const b = document.querySelector('button[aria-label*="پسند"], [role="button"][aria-label*="پسند"], button.action-item');
                if (b) b.click();
            }""")
            time.sleep(1.5)
            confirmed_red = is_like_button_active(page)

        updated_label = like_btn.get_attribute("aria-label") or like_btn.inner_text() or button_label
        if confirmed_red:
            logger.info(f"Like button confirmed RED! Current state: '{updated_label}'")
            return True, updated_label
        else:
            logger.warning("Like button clicked, but red state could not be strictly confirmed.")
            return False, updated_label

    except Exception as e:
        logger.error(f"Error clicking like button: {e}")
        return False, None


def render_chrome_dark_topbar(width: int, url: str, page_title: str) -> Image.Image:
    """
    Renders an authentic Google Chrome Dark Theme header including:
    - Tab bar with Aparat favicon and page title
    - Chrome window control buttons (minimize, maximize, close)
    - Navigation buttons (Back, Forward, Reload)
    - Full Omnibox Address Bar with SSL lock icon and active URL.
    """
    height = 84
    img = Image.new("RGBA", (width, height), (32, 33, 36, 255))  # #202124 Chrome Dark
    draw = ImageDraw.Draw(img)

    # 1. Window controls on top-right (Minimize, Maximize, Close)
    draw.line([(width - 25, 13), (width - 15, 23)], fill=(154, 160, 166, 255), width=1)
    draw.line([(width - 15, 13), (width - 25, 23)], fill=(154, 160, 166, 255), width=1)
    draw.rectangle([width - 55, 13, width - 45, 23], outline=(154, 160, 166, 255), width=1)
    draw.line([(width - 85, 19), (width - 75, 19)], fill=(154, 160, 166, 255), width=1)

    # 2. Active Tab
    tab_width = min(260, width // 4)
    tab_x0 = 80
    tab_x1 = tab_x0 + tab_width
    draw.rounded_rectangle([tab_x0, 8, tab_x1, 44], radius=8, fill=(41, 42, 45, 255))  # #292a2d

    # Aparat red logo dot
    draw.ellipse([tab_x0 + 12, 18, tab_x0 + 26, 32], fill=(223, 15, 80, 255))

    # Cross-platform font handling (Windows / Linux / macOS)
    def load_best_font(size: int, is_bold: bool = False):
        font_candidates = [
            "arial.ttf", "Arial.ttf",
            "DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "LiberationSans-Regular.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "FreeSans.ttf", "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
            "Vazirmatn-Regular.ttf", "/usr/share/fonts/truetype/vazirmatn/Vazirmatn-Regular.ttf",
        ]
        for candidate in font_candidates:
            try:
                return ImageFont.truetype(candidate, size)
            except Exception:
                continue
        return ImageFont.load_default()

    font_tab = load_best_font(12)
    font_url = load_best_font(13)
    font_icons = load_best_font(13)

    display_title = (page_title[:24] + "...") if len(page_title) > 24 else page_title
    draw.text((tab_x0 + 34, 18), display_title, fill=(232, 234, 237, 255), font=font_tab)
    draw.text((tab_x1 - 18, 17), "×", fill=(154, 160, 166, 255), font=font_tab)
    draw.text((tab_x1 + 10, 16), "+", fill=(154, 160, 166, 255), font=font_icons)

    # 3. Address Bar / Toolbar Row
    draw.rectangle([0, 42, width, height], fill=(41, 42, 45, 255))  # #292a2d

    # Navigation buttons: Back (←), Forward (→), Reload (↻)
    draw.line([(18, 63), (28, 63)], fill=(154, 160, 166, 255), width=2)
    draw.line([(18, 63), (23, 58)], fill=(154, 160, 166, 255), width=2)
    draw.line([(18, 63), (23, 68)], fill=(154, 160, 166, 255), width=2)

    draw.line([(42, 63), (52, 63)], fill=(95, 99, 104, 255), width=2)
    draw.line([(52, 63), (47, 58)], fill=(95, 99, 104, 255), width=2)
    draw.line([(52, 63), (47, 68)], fill=(95, 99, 104, 255), width=2)

    draw.arc([66, 57, 78, 69], start=45, end=315, fill=(154, 160, 166, 255), width=2)
    draw.polygon([(78, 56), (82, 61), (74, 61)], fill=(154, 160, 166, 255))

    # 4. Omnibox / Address Bar Pill
    omni_left = 95
    omni_right = width - 110
    omni_top = 48
    omni_bottom = 78

    draw.rounded_rectangle([omni_left, omni_top, omni_right, omni_bottom], radius=15, fill=(32, 33, 36, 255))

    # SSL Lock Icon
    lock_x = omni_left + 14
    lock_y = omni_top + 8
    draw.arc([lock_x + 2, lock_y, lock_x + 10, lock_y + 8], start=180, end=0, fill=(154, 160, 166, 255), width=2)
    draw.rectangle([lock_x, lock_y + 5, lock_x + 12, lock_y + 14], fill=(154, 160, 166, 255))

    # URL Text
    draw.text((omni_left + 36, omni_top + 7), url, fill=(232, 234, 237, 255), font=font_url)

    # Bookmark Star
    draw.text((omni_right - 24, omni_top + 6), "★", fill=(154, 160, 166, 255), font=font_tab)

    # Extensions and Profile icons
    ext_x = width - 85
    draw.rectangle([ext_x, 56, ext_x + 14, 70], outline=(154, 160, 166, 255), width=2)
    prof_x = width - 45
    draw.ellipse([prof_x, 54, prof_x + 18, 72], fill=(95, 99, 104, 255))

    return img


def capture_screenshot_with_like_button(
    page: Page,
    output_path: Path,
    url: str,
    include_address_bar: bool = INCLUDE_ADDRESS_BAR_DEFAULT,
    bottom_offset: int = LIKE_BUTTON_BOTTOM_OFFSET,
) -> Path:
    """
    Scrolls the page so the like button is positioned at the BOTTOM of the viewport,
    captures the screenshot, and optionally composites an authentic Google Chrome dark
    mode address bar at the top of the image.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Scroll page so like button is aligned at the bottom of the viewport
    page.evaluate("""(offset) => {
        const likeBtn = document.querySelector('button[aria-label*="پسند"], [role="button"][aria-label*="پسند"], button.action-item');
        if (likeBtn) {
            const rect = likeBtn.getBoundingClientRect();
            const targetBottom = window.innerHeight - offset;
            window.scrollBy({
                top: rect.bottom - targetBottom,
                behavior: 'instant'
            });
        }
    }""", bottom_offset)

    # Move cursor to top-left to avoid triggering hover tooltip overlays on the like button
    page.mouse.move(10, 10)
    time.sleep(1)

    # Take screenshot bytes
    screenshot_bytes = page.screenshot(full_page=False)
    page_img = Image.open(io.BytesIO(screenshot_bytes))

    if include_address_bar:
        video_id = extract_video_id(url)
        topbar = render_chrome_dark_topbar(
            width=page_img.width,
            url=url,
            page_title=f"Aparat - {video_id}",
        )
        combined = Image.new("RGB", (page_img.width, topbar.height + page_img.height))
        combined.paste(topbar, (0, 0))
        combined.paste(page_img, (0, topbar.height))
        combined.save(str(output_path))
    else:
        page_img.save(str(output_path))

    logger.info(f"Screenshot successfully saved to: {output_path}")
    return output_path
