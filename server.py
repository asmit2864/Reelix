"""
ShortReel Uploader - Local Server
Serves the UI AND receives upload config, then triggers browser automation.

Run this file, then open http://localhost:5555 in your browser.
"""

from flask import Flask, request, jsonify, send_from_directory
import threading
import subprocess
import json
import os
import webbrowser

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder=BASE_DIR)

automation_logs = []

@app.route('/logs', methods=['GET'])
def get_logs():
    """Return logs starting from a specific index."""
    after = int(request.args.get('after', 0))
    return jsonify({'logs': automation_logs[after:]})


@app.route('/')
def index():
    """Serve the UI — this avoids all CORS issues."""
    return send_from_directory(BASE_DIR, 'index.html')


@app.route('/pick-file', methods=['GET'])
def pick_file():
    """Opens a native file dialog to get the absolute path of a video file."""
    try:
        # Run tkinter in a separate process to avoid thread issues
        cmd = [
            'python', '-c',
            'import tkinter as tk, tkinter.filedialog as fd; root=tk.Tk(); root.attributes("-topmost", True); root.withdraw(); print(fd.askopenfilename(title="Select Video File", filetypes=[("Video", "*.mp4;*.mov;*.webm;*.avi"), ("All", "*.*")]))'
        ]
        result = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
        if result and os.path.exists(result):
            size = os.path.getsize(result)
            name = os.path.basename(result)
            return jsonify({'path': result, 'name': name, 'size': size})
    except Exception as e:
        print(f"File picker error: {e}")
    return jsonify({'path': ''})


@app.route('/upload', methods=['POST'])
def upload():
    data = request.json
    print("\n📦 Upload request received:")
    print(json.dumps(data, indent=2))

    # Save config for the automation script
    config_path = os.path.join(BASE_DIR, 'upload_config.json')
    with open(config_path, 'w') as f:
        json.dump(data, f, indent=2)

    global automation_logs
    automation_logs.clear()

    # Run automation in background thread and stream output
    def run_automation():
        uploader = os.path.join(BASE_DIR, 'uploader.py')
        
        # Force Python to use UTF-8 output to prevent Windows cp1252 emoji crashes
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        
        # -u forces unbuffered stdout so lines appear instantly
        process = subprocess.Popen(
            ['python', '-u', uploader],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=BASE_DIR,
            encoding='utf-8',
            env=env
        )
        
        for line in iter(process.stdout.readline, ''):
            line_str = line.rstrip() # keep leading spaces, remove trailing newlines
            if line_str:
                automation_logs.append(line_str)
                print(line_str) # Also print to terminal for visibility
                
        process.stdout.close()
        process.wait()

    thread = threading.Thread(target=run_automation, daemon=True)
    thread.start()

    return jsonify({'started': True})


if __name__ == '__main__':
    print("=" * 50)
    print("  ShortReel Uploader")
    print("=" * 50)
    print("  Opening http://localhost:5555 in your browser...")
    print("  Keep this window open while uploading.")
    print("  Press Ctrl+C to stop the server.")
    print("=" * 50)

    # Auto-open browser after a short delay
    def open_browser():
        import time
        time.sleep(1.2)
        webbrowser.open('http://localhost:5555')

    threading.Thread(target=open_browser, daemon=True).start()

    app.run(port=5555, debug=False)
