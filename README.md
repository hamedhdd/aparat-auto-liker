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
- **Telegram Bot Integration**: Built-in `telegram_bot.py` bot worker allows sending Aparat links via Telegram and receiving the captured screenshot directly in chat.
- **Linux Server Ready**: Runs completely headless on Linux VPS (Ubuntu/Debian) with zero GUI required, supported by an included systemd service unit.
- **Batch Processing**:
  - Supports single URLs, positional arguments, or a text file (`--file`) containing a list of links.

---

## Project Structure

```
aparat-auto-liker/
├── aparat_liker.py       # Main CLI script
├── telegram_bot.py       # Telegram Bot interface
├── config.py             # Configurable timeouts, selectors, and paths
├── utils.py              # Ad monitoring, like button actions, screenshot framing
├── aparat-bot.service    # Linux systemd service unit template
├── requirements.txt      # Python dependencies (playwright, requests, pillow)
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

---

## Telegram Bot & Linux Server Deployment

### 1. Launching the Telegram Bot
You can run the bot on Windows or Linux to receive links from Telegram and return screenshots:

```bash
# Direct execution with Bot Token
python telegram_bot.py --token "YOUR_TELEGRAM_BOT_TOKEN"

# Restricting to specific Telegram User IDs (whitelist)
python telegram_bot.py --token "YOUR_TELEGRAM_BOT_TOKEN" --allowed-users "12345678,87654321"

# Using proxy (for servers inside Iran)
python telegram_bot.py --token "YOUR_TELEGRAM_BOT_TOKEN" --proxy "socks5://127.0.0.1:10808"
```

### 2. Linux VPS Installation (Ubuntu / Debian)
```bash
# 1. Install system dependencies & Persian fonts
sudo apt update && sudo apt install -y git python3 python3-venv python3-pip fonts-vazirmatn fonts-dejavu

# 2. Clone repo & create virtualenv
git clone https://github.com/hamedhdd/aparat-auto-liker.git /opt/aparat-auto-liker
cd /opt/aparat-auto-liker
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Install Playwright browser & Linux dependencies
playwright install chromium --with-deps

# 4. Set up systemd service for 24/7 background operation
sudo cp aparat-bot.service /etc/systemd/system/
sudo nano /etc/systemd/system/aparat-bot.service   # Insert your Bot Token
sudo systemctl daemon-reload
sudo systemctl enable --now aparat-bot
```

*Detailed step-by-step instructions available in `Aparat_Telegram_Bot_Linux_Deployment_Guide.md`.*
