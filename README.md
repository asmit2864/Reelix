# 🎬 Reelix

Reelix is an automated video publishing tool designed to upload the same video to **YouTube Shorts** and **Instagram Reels** effortlessly. It features a modern, premium web interface to configure your metadata and uses browser automation to execute the uploads directly through your own logged-in sessions.

---

## ✨ Features

- **Multi-Platform Automation**: Uploads to YouTube and Instagram with a single click.
- **Premium Web UI**: A dark-themed, glassmorphic single-page application for easy configuration.
- **Real-time Logging**: Monitor the progress of your uploads live from the web interface.
- **Session Persistence**: Logs in once using a local browser profile; no need for complex API keys or tokens.
- **Smart Metadata Handling**: Native file picker, automatic tagging, location setting, and copyright wait mechanisms.

---

## 🚀 How it Works

1. **Web Interface (`index.html`)**: A modern frontend where you input your video details, title, description, tags, and specific platform configurations.
2. **Local Server (`server.py`)**: A Flask-based backend that securely bridges the web interface and the automation engine.
3. **Automation Engine (`uploader.py`)**: A Playwright-powered script that launches a real Chromium browser, navigates to YouTube Studio and Instagram, and performs human-like interactions to upload your videos.

---

## 🛠️ Setup Instructions (Windows)

### Step 1: Install Python
Ensure Python is installed on your system. You can download it from [python.org](https://python.org).
*Important: Check the "Add Python to PATH" box during installation.*

### Step 2: Run Setup (First Time Only)
Double-click `SETUP.bat` in the project folder.
This will automatically install all required Python dependencies (like Flask and Playwright) and download the necessary Chromium browser binaries.

### Step 3: Launch Reelix
Double-click `START.bat`.
This script will start the local server and automatically open `http://localhost:5555` in your default browser.

### Step 4: First-Time Login
The very first time you use the tool to upload, the automated browser will pause and ask you to log in to YouTube and/or Instagram.
- Log in manually.
- Press `ENTER` in the command prompt/server window when you are done.
- Your session is saved locally in the `browser_profile` folder, meaning you won't need to log in again for future uploads!

---

## 📋 How to Use

1. Launch Reelix using `START.bat`.
2. Click **Select Video** to pick a video file using the native file dialog.
3. Toggle the platforms you want to upload to (YouTube, Instagram).
4. Fill in the metadata (Title, Description, Tags, Playlist, Location).
5. Click **Start Upload Automation**.
6. Switch to the **Live Logs** tab to watch the automation progress in real-time.

---

## 🐙 Pushing to GitHub

If you want to back up or share your Reelix project on GitHub, follow these steps:

1. **Initialize Git**: Open your terminal or command prompt in the Reelix folder and run:
   ```bash
   git init
   ```
2. **Add Files**: Stage all your project files:
   ```bash
   git add .
   ```
3. **Commit**: Save your changes:
   ```bash
   git commit -m "Initial commit for Reelix"
   ```
4. **Create a Repository**: Go to [GitHub](https://github.com/) and create a new, empty repository.
5. **Link and Push**: Run the following commands (replace `<your-repository-url>` with your actual GitHub repo link):
   ```bash
   git branch -M main
   git remote add origin <your-repository-url>
   git push -u origin main
   ```
*(Note: A `.gitignore` file is included in the project so that your local browser sessions (`browser_profile/`) and temporary files aren't uploaded to GitHub.)*
