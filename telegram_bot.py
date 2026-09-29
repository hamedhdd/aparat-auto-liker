"""
Telegram Bot Interface for Aparat Auto Liker & Screenshot Tool
--------------------------------------------------------------
Allows users to send Aparat video URLs via Telegram, automatically
handles advertisements, likes the video, and replies with the framed screenshot.
"""
import os
import sys
import time
import re
import logging
import argparse
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
import requests

from playwright.sync_api import sync_playwright

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
    get_browser_executable,
)

if sys.stdout:
    sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("AparatTelegramBot")


class TelegramBotClient:
    """Lightweight, resilient Telegram Bot API client using standard requests."""

    def __init__(self, token: str, proxy: Optional[str] = None):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.session = requests.Session()
        if proxy:
            self.session.proxies = {"http": proxy, "https": proxy}
            logger.info(f"Using proxy for Telegram: {proxy}")

    def get_updates(self, offset: Optional[int] = None, timeout: int = 30) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/getUpdates"
        params = {"timeout": timeout}
        if offset is not None:
            params["offset"] = offset
        try:
            resp = self.session.get(url, params=params, timeout=timeout + 10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("ok"):
                    return data.get("result", [])
            else:
                logger.error(f"getUpdates error HTTP {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.error(f"Error connecting to Telegram API: {e}")
        return []

    def send_message(self, chat_id: int, text: str, reply_to_message_id: Optional[int] = None) -> Optional[int]:
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
        }
        if reply_to_message_id:
            payload["reply_to_message_id"] = reply_to_message_id
        try:
            resp = self.session.post(url, json=payload, timeout=15)
            if resp.status_code == 200:
                return resp.json().get("result", {}).get("message_id")
        except Exception as e:
            logger.error(f"Failed to send message to {chat_id}: {e}")
        return None

    def edit_message(self, chat_id: int, message_id: int, text: str):
        url = f"{self.base_url}/editMessageText"
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": "HTML",
        }
        try:
            self.session.post(url, json=payload, timeout=15)
        except Exception as e:
            logger.debug(f"Failed to edit message {message_id}: {e}")

    def send_photo(
        self,
        chat_id: int,
        photo_path: Path,
        caption: str = "",
        reply_to_message_id: Optional[int] = None,
    ) -> bool:
        url = f"{self.base_url}/sendPhoto"
        data = {
            "chat_id": chat_id,
            "caption": caption,
            "parse_mode": "HTML",
        }
        if reply_to_message_id:
            data["reply_to_message_id"] = reply_to_message_id

        try:
            with open(photo_path, "rb") as f:
                files = {"photo": f}
                resp = self.session.post(url, data=data, files=files, timeout=45)
                return resp.status_code == 200 and resp.json().get("ok", False)
        except Exception as e:
            logger.error(f"Failed to send photo to {chat_id}: {e}")
            return False


def process_aparat_link(url: str, output_dir: Path, theme: str = DEFAULT_THEME) -> Tuple[bool, Optional[Path], str]:
    """
    Executes headless Playwright workflow on Linux/Windows for a single Aparat video URL:
    Waits for ad, clicks like button, captures screenshot with address bar and bottom-aligned like button.
    Returns (success: bool, screenshot_path: Optional[Path], status_text: str).
    """
    video_id = extract_video_id(url)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    screenshot_path = output_dir / f"aparat_{video_id}_{timestamp}.png"
    output_dir.mkdir(parents=True, exist_ok=True)

    chrome_args = ["--disable-blink-features=AutomationControlled"]
    if theme == "dark":
        chrome_args.extend(["--force-dark-mode", "--enable-features=WebContentsForceDark"])

    exec_path = get_browser_executable()
    with sync_playwright() as p:
        if exec_path:
            logger.info(f"Using system browser executable: {exec_path}")
            browser = p.chromium.launch(
                executable_path=exec_path,
                headless=True,
                args=chrome_args,
            )
        else:
            try:
                browser = p.chromium.launch(
                    channel="chrome",
                    headless=True,
                    args=chrome_args,
                )
            except Exception:
                logger.info("Chrome channel unavailable; using default Chromium...")
                browser = p.chromium.launch(
                    headless=True,
                    args=chrome_args,
                )

        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            color_scheme=theme,
        )
        context.add_cookies([
            {"name": "theme", "value": theme, "domain": ".aparat.com", "path": "/"}
        ])

        page = context.new_page()
        try:
            logger.info(f"Opening video: {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT * 1000)

            # Wait for player
            try:
                page.wait_for_selector("video", timeout=VIDEO_PLAYER_TIMEOUT * 1000)
            except Exception:
                pass

            # 1. Wait for ad
            wait_for_ad_completion(page, timeout=MAX_AD_WAIT_SECONDS, auto_skip=True)
            time.sleep(1.5)

            # 2. Like button
            success, like_info = find_and_click_like_button(page)

            # 3. Screenshot
            capture_screenshot_with_like_button(
                page=page,
                output_path=screenshot_path,
                url=url,
                include_address_bar=True,
            )

            context.close()
            browser.close()
            return True, screenshot_path, like_info or "Liked"

        except Exception as e:
            logger.error(f"Error processing {url}: {e}", exc_info=True)
            context.close()
            browser.close()
            return False, None, str(e)


def run_telegram_bot(
    token: str,
    output_dir: Path,
    proxy: Optional[str] = None,
    allowed_users: Optional[List[int]] = None,
):
    """Runs long-polling Telegram bot worker."""
    client = TelegramBotClient(token, proxy=proxy)
    logger.info("Telegram Bot started. Listening for Aparat video links...")
    offset: Optional[int] = None

    while True:
        try:
            updates = client.get_updates(offset=offset, timeout=25)
            for u in updates:
                offset = u["update_id"] + 1
                msg = u.get("message") or u.get("edited_message")
                if not msg:
                    continue

                chat_id = msg["chat"]["id"]
                user_id = msg.get("from", {}).get("id")
                text = (msg.get("text") or "").strip()
                msg_id = msg["message_id"]

                # Access control check
                if allowed_users and user_id not in allowed_users and chat_id not in allowed_users:
                    logger.warning(f"Unauthorized message from user {user_id} in chat {chat_id}")
                    client.send_message(
                        chat_id=chat_id,
                        text="⛔ <b>Access Denied:</b> You are not authorized to use this bot.",
                        reply_to_message_id=msg_id,
                    )
                    continue

                if text in ["/start", "/help"]:
                    welcome = (
                        "👋 <b>Welcome to Aparat Auto-Liker Bot!</b>\n\n"
                        "Send me any Aparat video link (e.g. <code>https://www.aparat.com/v/ovw9yg1</code>) "
                        "and I will:\n"
                        "1. Open the video in headless Chrome on the server.\n"
                        "2. Wait for / skip advertisements.\n"
                        "3. Click the Like button and confirm red state.\n"
                        "4. Send you the framed dark-mode screenshot with the address bar!\n\n"
                        "💡 <i>Tip: You can send links directly or use</i> <code>/like &lt;URL&gt;</code>."
                    )
                    client.send_message(chat_id=chat_id, text=welcome, reply_to_message_id=msg_id)
                    continue

                # Extract Aparat URLs from message
                found_urls = re.findall(r"https?://(?:www\.)?aparat\.com/v/[a-zA-Z0-9_-]+", text)
                if not found_urls:
                    if text.startswith("/"):
                        client.send_message(
                            chat_id=chat_id,
                            text="⚠️ Please send a valid Aparat video link (e.g., <code>https://www.aparat.com/v/ovw9yg1</code>).",
                            reply_to_message_id=msg_id,
                        )
                    continue

                for target_url in found_urls:
                    status_msg_id = client.send_message(
                        chat_id=chat_id,
                        text=f"⏳ <b>Processing video:</b>\n<code>{target_url}</code>\n\n<i>Waiting for ads & liking...</i>",
                        reply_to_message_id=msg_id,
                    )

                    ok, shot_path, status_text = process_aparat_link(target_url, output_dir=output_dir)

                    if ok and shot_path and shot_path.exists():
                        caption = (
                            f"✅ <b>Aparat Video Liked!</b>\n\n"
                            f"❤️ <b>Status:</b> {status_text}\n"
                            f"🔗 <b>Link:</b> <code>{target_url}</code>\n"
                            f"📸 <i>Captured in native dark theme with address bar.</i>"
                        )
                        client.send_photo(
                            chat_id=chat_id,
                            photo_path=shot_path,
                            caption=caption,
                            reply_to_message_id=msg_id,
                        )
                        if status_msg_id:
                            client.edit_message(
                                chat_id=chat_id,
                                message_id=status_msg_id,
                                text=f"✅ <b>Completed:</b> <code>{target_url}</code>",
                            )
                    else:
                        error_text = f"❌ <b>Failed to process video:</b>\n{status_text}"
                        if status_msg_id:
                            client.edit_message(chat_id=chat_id, message_id=status_msg_id, text=error_text)
                        else:
                            client.send_message(chat_id=chat_id, text=error_text, reply_to_message_id=msg_id)

        except Exception as e:
            logger.error(f"Unexpected error in polling loop: {e}", exc_info=True)
            time.sleep(3)


def main():
    parser = argparse.ArgumentParser(description="Run Telegram Bot for Aparat Auto Liker")
    parser.add_argument(
        "--token",
        "-t",
        type=str,
        default=os.getenv("TELEGRAM_BOT_TOKEN"),
        help="Telegram Bot Token (or set TELEGRAM_BOT_TOKEN env variable)",
    )
    parser.add_argument(
        "--proxy",
        "-p",
        type=str,
        default=os.getenv("TELEGRAM_PROXY"),
        help="HTTP/SOCKS5 Proxy for Telegram API (e.g., socks5://127.0.0.1:10808 or http://127.0.0.1:2080)",
    )
    parser.add_argument(
        "--allowed-users",
        "-u",
        type=str,
        default=os.getenv("ALLOWED_USERS"),
        help="Comma-separated Telegram user/chat IDs allowed to use the bot (e.g. 12345678,87654321)",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=str,
        default=str(DEFAULT_SCREENSHOT_DIR),
        help="Directory to save screenshots",
    )

    args = parser.parse_args()

    if not args.token:
        print("ERROR: Telegram Bot Token is required!")
        print("Please provide --token <BOT_TOKEN> or set TELEGRAM_BOT_TOKEN in environment.")
        sys.exit(1)

    allowed = None
    if args.allowed_users:
        allowed = [int(uid.strip()) for uid in args.allowed_users.split(",") if uid.strip().isdigit()]

    run_telegram_bot(
        token=args.token,
        output_dir=Path(args.output_dir),
        proxy=args.proxy,
        allowed_users=allowed,
    )


if __name__ == "__main__":
    main()
