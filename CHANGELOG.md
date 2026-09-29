# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.2] - 2026-09-29

### Fixed
- **Instant Systemd Log Streaming**: Added `PYTHONUNBUFFERED=1`, explicit stdout logging handler, and `-u` flag to ensure all bot interactions and progress events stream immediately to `journalctl`.
- **Skip Ad Click Timeout**: Scoped skip button click timeout to 3 seconds (`timeout=3000`) with error handling, preventing default 30-second Playwright actionability wait when skip elements change dynamically.

## [1.2.1] - 2026-09-29

### Added
- **Native Browser Auto-Detection (`get_browser_executable`)**: Added support for automatic detection of system-installed Chromium/Chrome binaries (`/usr/bin/chromium`, `/usr/bin/google-chrome`), bypassing geo-restricted Playwright CDN downloads on restricted Linux servers.

## [1.2.0] - 2026-09-29

### Added
- **Telegram Bot Integration (`telegram_bot.py`)**: Enables automated interaction via Telegram: send any Aparat video link and automatically receive the dark-mode framed screenshot with like confirmation.
- **Linux Server & Headless Support**: Optimized Playwright to run seamlessly on Linux servers with automatic Chromium fallback, cross-platform font loading, and `playwright install chromium --with-deps` compatibility.
- **Systemd Service Unit (`aparat-bot.service`)**: Ready-to-use daemon configuration for running the Telegram bot 24/7 on Ubuntu/Debian servers.
- **Security & Network Flexibility**: Supports user ID access control whitelist (`--allowed-users`) and proxy routing (`--proxy` for SOCKS5/HTTP proxies on filtered networks).
- **Deployment Documentation**: Created comprehensive runbook `Aparat_Telegram_Bot_Linux_Deployment_Guide.md` in `Antigravity_Docs`.

## [1.1.0] - 2026-09-29

### Added
- **Dark Theme Support**: Browser launched with `--force-dark-mode` and pre-configured with `theme=dark` Aparat cookie and `color_scheme="dark"` by default.
- **Chrome Address Bar Integration**: Built-in generator creating an authentic Google Chrome Dark Mode top bar (tab with Aparat icon and title, window controls, and Omnibox address bar showing SSL lock and video URL) seamlessly composited on top of screenshots.
- **Bottom-Aligned Like Button**: Implemented dynamic viewport scroll adjustment that aligns the active like button right at the bottom edge of the screenshot with the video player displayed directly above.
- **New CLI Flags**: Added `--theme` (choice: `dark` or `light`) and `--no-address-bar` to toggle header integration.

### Fixed
- Fixed in-stream video ad completion detection by checking `adVideo.paused` and `mainVideo.currentTime` so that skipped or concluded ads immediately advance to the like stage without waiting for maximum timeout.

## [1.0.1] - 2026-09-28

### Fixed
- Fixed like button click confirmation to strictly wait for the active red/pink filled heart state (`svg.icon-favoritefilled` and computed crimson red style `#DF0F50`) before capturing the screenshot.
- Added duplicate-click prevention: automatically skips clicking if the like button is already active/liked to prevent inadvertent un-liking.
- Scoped in-stream advertisement overlay detection strictly to the video player container to avoid false positives caused by static sidebar banner advertisements.
- Positioned mouse away from the like button prior to screenshot capture to prevent hover tooltips or focus rings from obscuring the red button.

## [1.0.0] - 2026-09-28

### Added
- Core automation script (`aparat_liker.py`) supporting Google Chrome automation via Playwright (`channel="chrome"`).
- Ad detection engine in `utils.py` capable of identifying pre-roll/in-stream advertisements from Aparat CDN (`aparat-ads`).
- Ad skip button detection and automatic trigger for `رد کردن آگهی` / `رد کردن تبلیغ` / `Skip` overlays.
- Robust like button discovery with Persian `aria-label` matching and DOM fallback.
- Viewport framing logic ensuring both the video player and the clicked like button are centrally visible in screenshots.
- Local screenshot persistence with automated file naming (`aparat_<video_id>_<timestamp>.png`).
- Configurable CLI flags for `--headless`, `--user-data-dir`, `--output-dir`, `--file`, and `--no-skip`.
- Comprehensive `README.md` and initial operational runbook documentation.
