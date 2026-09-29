# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
