# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
