# Aparat Auto Liker & Screenshot Automation

An automated script built with Python and Playwright (targeting Google Chrome) that opens Aparat video URLs, handles pre-roll video advertisements (either waiting them out or automatically skipping them when available), clicks the "Like" button, verifies the like status, and takes a viewport screenshot with the like button prominently visible, saving it locally.

---

## Features

- **Google Chrome Native Integration**: Directly launches installed Google Chrome browser (`channel="chrome"`) with anti-detection flags and native dark mode (`--force-dark-mode`).
- **Dark Theme by Default**: Sets browser context and Aparat session cookie to dark theme (`theme=dark`).
- **Chrome Address Bar in Screenshots**: Includes an authentic Google Chrome Dark Mode top bar displaying the tab with favicon, SSL lock icon, and the exact target URL (`https://www.aparat.com/v/...`).
- **Bottom-Aligned Like Button**: Dynamically scrolls the view so the active like button sits squarely at the bottom of the screenshot with the main video container prominent above it.
- **Smart Ad Detection & Handling**:
  - Automatically identifies in-stream video advertisements from Aparat CDN (`aparat-ads`).
  - Detects ad countdown timers and skip triggers (`رد کردن آگهی` / `رد کردن تبلیغ` / `Skip`).
  - Can automatically click the skip button as soon as available, or wait for the full advertisement to finish naturally (`--no-skip`).
- **Resilient Like Button Interaction**:
  - Multi-tiered selector engine matching Persian aria-labels (`پسندیدن`, `نفر پسندیدند`), element attributes, and SVG icons.
  - Automatically waits for client-side skeleton placeholders to hydrate.
  - Validates post-click state change (crimson red `#DF0F50` fill and active heart icon `icon-favoritefilled`).
  - Safeguard prevents un-liking if already liked.
- **User Profile Session Support**:
  - Allows passing `--user-data-dir` to reuse existing logged-in Chrome sessions/cookies.
- **Batch Processing**:
  - Supports single URLs, positional arguments, or a text file (`--file`) containing a list of links.

---

## Project Structure

```
aparat-auto-liker/
├── aparat_liker.py       # Main CLI script
├── config.py             # Configurable timeouts, selectors, and paths
├── utils.py              # Ad monitoring, like button actions, screenshot framing
├── requirements.txt      # Python dependencies (playwright)
├── README.md             # Project documentation
├── CHANGELOG.md          # Version history
└── screenshots/          # Default directory for output screenshots
```

---

## Prerequisites

- **Python**: 3.10+
- **Google Chrome**: Installed on the system (`C:\Program Files\Google\Chrome\Application\chrome.exe`).
- **Playwright**: Installed via pip.

---

## Installation

```powershell
# Navigate to the project directory
cd C:\Users\Hamed\.gemini\antigravity\scratch\aparat-auto-liker

# Install dependencies
pip install -r requirements.txt
```

---

## Usage Guide

### 1. Default Run (Headed Chrome with Sample URL)
Opens the sample video in a visible Google Chrome window, waits for the ad, likes the video, and saves a screenshot:
```powershell
python aparat_liker.py https://www.aparat.com/v/ovw9yg1
```

### 2. Run in Headless Mode
Runs silently in the background:
```powershell
python aparat_liker.py https://www.aparat.com/v/ovw9yg1 --headless
```

### 3. Reuse Your Logged-in Chrome Profile
If you want the like action to be recorded under your personal Aparat account:
```powershell
python aparat_liker.py https://www.aparat.com/v/ovw9yg1 --user-data-dir "C:\Users\Hamed\AppData\Local\Google\Chrome\User Data"
```
*(Make sure Chrome is closed when running with your active profile directory to prevent lock conflicts)*.

### 4. Wait Full Ad Duration Without Skipping
To wait through the complete advertisement duration without pressing the Skip button:
```powershell
python aparat_liker.py https://www.aparat.com/v/ovw9yg1 --no-skip
```

### 5. Custom Output Directory
```powershell
python aparat_liker.py https://www.aparat.com/v/ovw9yg1 --output-dir "C:\Users\Hamed\Pictures\Aparat_Likes"
```

### 6. Batch Processing Multiple URLs
Provide multiple URLs on the command line:
```powershell
python aparat_liker.py https://www.aparat.com/v/ovw9yg1 https://www.aparat.com/v/example2
```
Or use a text file containing one URL per line:
```powershell
python aparat_liker.py -f urls.txt --headless
```

---

## CLI Options

| Argument | Short | Default | Description |
| :--- | :--- | :--- | :--- |
| `urls` | Positional | `https://www.aparat.com/v/ovw9yg1` | One or more Aparat video URLs |
| `--file` | `-f` | `None` | Path to text file with URLs |
| `--output-dir` | `-o` | `./screenshots` | Folder to store captured PNGs |
| `--theme` | | `dark` | Browser theme (`dark` or `light`) |
| `--no-address-bar` | | `False` | Exclude Chrome top address bar from screenshot |
| `--headless` | | `False` | Run Chrome in background without GUI |
| `--user-data-dir`| `-u` | `None` | Path to Chrome user data profile |
| `--no-skip` | | `False` | Disable auto-clicking 'Skip Ad' |
| `--timeout` | | `90` | Maximum ad monitoring timeout (sec) |
