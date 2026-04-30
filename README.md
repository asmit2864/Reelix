# 🎬 ShortReel Uploader

Upload the same video to **YouTube Shorts** and **Instagram Reels** automatically using browser automation.

---

## 📁 Files

| File | Purpose |
|---|---|
| `index.html` | Web UI — open this in your browser |
| `server.py` | Local server that receives form data |
| `uploader.py` | Playwright automation that does the uploading |
| `SETUP.bat` | Run once to install everything |
| `START.bat` | Run every time to launch the tool |
| `requirements.txt` | Python packages needed |

---

## 🚀 Getting Started (Windows)

### Step 1 — Install Python
Download from https://python.org (check "Add to PATH" during install)

### Step 2 — Run Setup (once only)
Double-click `SETUP.bat`

This installs Flask, Playwright, and downloads the Chromium browser.

### Step 3 — Launch
Double-click `START.bat`

This opens:
- The web UI in your browser
- A server window running in the background

### Step 4 — First time login
The first time you upload to each platform, a browser will open and ask you to log in.
- Log into YouTube / Instagram normally
- Press ENTER in the server window when done
- Your session is saved — you won't need to log in again next time ✅

---

## 📋 How to use

1. Drag & drop your video file into the UI
2. Select which platforms to upload to
3. Fill in YouTube details (title, description, playlist, etc.)
4. Fill in Instagram caption and location
5. Click **Start Upload Automation**
6. Watch the browser do the work!

---

## ⚠️ Notes

- If a platform updates their UI, selectors in `uploader.py` may need small tweaks
- This uses your real browser login — no API keys or tokens needed

---

## 🔧 Troubleshooting

**"Could not connect to local server"**
→ Make sure `server.py` is running (START.bat opens it automatically)

**"Video file not found"**
→ Ensure the video file hasn't been moved or deleted since you selected it

**Browser opens but gets stuck**
→ YouTube/Instagram may have updated their UI. Open an issue or tweak selectors in `uploader.py`
