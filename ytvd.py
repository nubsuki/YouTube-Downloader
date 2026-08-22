import sys
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from yt_dlp import YoutubeDL
import webbrowser
import threading
import urllib.request
import urllib.error
import json
import tempfile
import subprocess

__version__ = "v2.2.2"
GITHUB_REPO = "nubsuki/YouTube-Downloader"
API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

# Detect platform and set FFmpeg path
base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
ffmpeg_path = os.path.join(base_path, "ffmpeg", "bin")
deno_dir = os.path.join(base_path, "deno", "bin")
if os.path.isdir(deno_dir):
    os.environ["PATH"] = deno_dir + os.pathsep + os.environ.get("PATH", "")
if os.path.isdir(ffmpeg_path):
    os.environ["PATH"] = ffmpeg_path + os.pathsep + os.environ.get("PATH", "")

def check_for_updates():
    """Background thread: check GitHub for a newer release."""
    # Only auto-update when running as a compiled exe
    if not getattr(sys, "frozen", False):
        return
    try:
        req = urllib.request.Request(API_URL, headers={"User-Agent": "YTDownloader-Updater"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())
        latest_tag = data.get("tag_name", "")
        if latest_tag and latest_tag != __version__:
            # Find the windows exe asset
            asset_url = None
            for asset in data.get("assets", []):
                if asset["name"].endswith(".exe"):
                    asset_url = asset["browser_download_url"]
                    break
            if asset_url:
                app.after(0, lambda: show_update_banner(latest_tag, asset_url))
    except Exception:
        pass  # Silently ignore


def show_update_banner(latest_tag, asset_url):
    """Show a dismissible update notification banner."""
    global update_banner
    update_label.config(text=f"Update {latest_tag} available!")
    update_banner.pack(side=tk.BOTTOM, fill=tk.X)
    app.geometry(f"{window_width}x{window_height + 36}+{position_left}+{position_top}")

    def on_update():
        update_btn.config(state=tk.DISABLED, text="Downloading...")
        threading.Thread(target=lambda: download_and_apply(asset_url), daemon=True).start()

    def on_dismiss():
        update_banner.pack_forget()
        app.geometry(f"{window_width}x{window_height}+{position_left}+{position_top}")

    update_btn.config(command=on_update, state=tk.NORMAL, text="Update Now")
    dismiss_btn.config(command=on_dismiss)


def download_and_apply(asset_url):
    """Download the new exe directly and apply the update."""
    try:
        tmp_dir = tempfile.mkdtemp()
        new_exe_path = os.path.join(tmp_dir, "YouTube_Downloader_new.exe")

        req = urllib.request.Request(asset_url, headers={"User-Agent": "YTDownloader-Updater"})
        with urllib.request.urlopen(req) as resp, open(new_exe_path, "wb") as f:
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            block = 8192
            while True:
                chunk = resp.read(block)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = min(downloaded / total * 100, 100)
                    app.after(0, lambda p=pct: progress_var.set(p))

        current_exe = sys.executable
        apply_update(current_exe, new_exe_path)

    except Exception as e:
        app.after(0, lambda: messagebox.showerror("Update Failed", str(e)))
        app.after(0, lambda: update_btn.config(state=tk.NORMAL, text="Update Now"))
        app.after(0, lambda: progress_var.set(0))


def apply_update(current_exe, new_exe_path):
    """Write a PowerShell updater script and launch it, then exit."""
    ps_script = f"""
$pid_to_wait = {os.getpid()}
try {{ Wait-Process -Id $pid_to_wait -Timeout 10 -ErrorAction SilentlyContinue }} catch {{}}
Start-Sleep -Milliseconds 500
Copy-Item -Path '{new_exe_path}' -Destination '{current_exe}' -Force
Start-Process -FilePath '{current_exe}'
"""
    script_path = os.path.join(tempfile.gettempdir(), "yt_updater.ps1")
    with open(script_path, "w") as f:
        f.write(ps_script)

    subprocess.Popen(
        ["powershell", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden",
         "-File", script_path],
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    app.after(0, app.destroy)


def fetch_qualities():
    """Fetch available video qualities for the given URL."""
    video_url = url_entry.get()

    if not video_url.strip():
        messagebox.showerror("Error", "Please enter a YouTube URL.")
        return

    # Disable fetch button while fetching
    fetch_button.config(state=tk.DISABLED)
    quality_dropdown.set('Fetching qualities...')

    def fetch_thread():
        ydl_opts = {
            'quiet': True,
            'noplaylist': True 
        }
        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                formats = info.get('formats', [])
                qualities = sorted(
                    set(f"{fmt['height']}p" for fmt in formats if fmt.get('height')),
                    key=lambda x: int(x.replace('p', ''))
                )
                if not qualities:
                    messagebox.showerror("Error", "No available video qualities found.")
                    return
                # Update the quality dropdown with fetched qualities
                quality_dropdown['values'] = qualities
                quality_var.set(qualities[-1])  # Automatically set to the highest quality
                download_video_button.config(state=tk.NORMAL)  # Enable download video button
                download_mp3_button.config(state=tk.NORMAL)  # Enable download MP3 button
        except Exception as e:
            messagebox.showerror("Error", f"Could not fetch qualities: {e}")
        finally:
            # Re-enable fetch button after fetching is done
            fetch_button.config(state=tk.NORMAL)
            quality_dropdown.set(quality_var.get())  # Set the dropdown to the selected quality

    # Run the fetch operation in a separate thread
    threading.Thread(target=fetch_thread, daemon=True).start()

def download_video():
    """Download the selected video quality."""
    video_url = url_entry.get()
    output_folder = folder_path.get()
    video_quality = quality_var.get()

    if not video_url.strip():
        messagebox.showerror("Error", "Please enter a YouTube URL.")
        return

    if not output_folder:
        messagebox.showerror("Error", "Please select a download folder.")
        return

    if not os.path.isdir(output_folder):
        messagebox.showerror("Error", "Invalid download folder. Please select a valid directory.")
        return

    ydl_opts = {
        'ffmpeg_location': ffmpeg_path,
        'format': f'bestvideo[height={video_quality.replace("p", "")}][vcodec^=avc]+bestaudio[ext=m4a]/bestvideo[height={video_quality.replace("p", "")}]+bestaudio/best[height={video_quality.replace("p", "")}]/best',
        'outtmpl': os.path.join(output_folder, '%(title)s (%(height)sp).%(ext)s'),
        'merge_output_format': 'mp4',
        'progress_hooks': [progress_hook],
        'noplaylist': True,
    }

    # Disable buttons during download
    fetch_button.config(state=tk.DISABLED)
    download_video_button.config(state=tk.DISABLED)
    download_mp3_button.config(state=tk.DISABLED)

    def download_thread():
        try:
            progress_var.set(0)
            progress_bar.update()
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
            messagebox.showinfo("Success", "Video downloaded successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")
        finally:
            # Reset form fields (except download folder)
            url_entry.delete(0, tk.END)
            quality_dropdown.set('')
            quality_dropdown['values'] = []
            progress_var.set(0)
            progress_bar.update()
            download_size_log.set("")
            download_size_log_label.pack_forget()

            # Re-enable fetch button and disable download button
            fetch_button.config(state=tk.NORMAL)
            download_video_button.config(state=tk.DISABLED)
            download_mp3_button.config(state=tk.DISABLED)

    threading.Thread(target=download_thread, daemon=True).start()

def download_mp3():
    """Download the audio as MP3."""
    video_url = url_entry.get()
    output_folder = folder_path.get()

    if not video_url.strip():
        messagebox.showerror("Error", "Please enter a YouTube URL.")
        return

    if not output_folder:
        messagebox.showerror("Error", "Please select a download folder.")
        return

    if not os.path.isdir(output_folder):
        messagebox.showerror("Error", "Invalid download folder. Please select a valid directory.")
        return

    # Configure ydl_opts for MP3 download
    ydl_opts = {
        'ffmpeg_location': ffmpeg_path,
        'format': 'bestaudio',  # Download the best available audio
        'outtmpl': os.path.join(output_folder, '%(title)s.%(ext)s'),  # Output file template
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',  # Extract audio
            'preferredcodec': 'mp3',      # Convert to MP3
            'preferredquality': '192',    # Set audio quality (192kbps)
        }],
        'progress_hooks': [progress_hook],
        'noplaylist': True,
    }

    # Disable buttons during download
    fetch_button.config(state=tk.DISABLED)
    download_video_button.config(state=tk.DISABLED)
    download_mp3_button.config(state=tk.DISABLED)

    def download_thread():
        try:
            progress_var.set(0)
            progress_bar.update()

            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
            messagebox.showinfo("Success", "MP3 downloaded successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")
        finally:
            # Reset form fields (except download folder)
            url_entry.delete(0, tk.END)
            quality_dropdown.set('')
            quality_dropdown['values'] = []
            progress_var.set(0)
            progress_bar.update()
            download_size_log.set("")
            download_size_log_label.pack_forget()

            # Re-enable fetch button and disable download buttons
            fetch_button.config(state=tk.NORMAL)
            download_video_button.config(state=tk.DISABLED)
            download_mp3_button.config(state=tk.DISABLED)

    threading.Thread(target=download_thread, daemon=True).start()


def progress_hook(d):
    """Update progress bar based on download progress."""
    if d['status'] == 'downloading':
        total_bytes = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
        downloaded_bytes = d.get('downloaded_bytes', 0)
        progress = (downloaded_bytes / total_bytes) * 100 if total_bytes else 0
        
        # Update progress bar
        progress_var.set(progress)
        progress_bar.update()
        
        # Update download size log
        download_size_log.set(f"Downloading: {downloaded_bytes / (1024 * 1024):.2f} MB / {total_bytes / (1024 * 1024):.2f} MB")

        # Ensure the log label is visible during the download
        if not download_size_log_label.winfo_ismapped():
            download_size_log_label.pack(pady=5)  # Show the label if it's not already visible
    else:
        # Hide the download size log once the download completes or is paused
        download_size_log.set("")  # Clear the log
        download_size_log_label.pack_forget()  # Hide the label

def browse_folder():
    folder = filedialog.askdirectory()
    if folder:
        folder_path.set(folder)

def open_github(event):
    try:
        webbrowser.open("https://github.com/nubsuki/YouTube-Downloader")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to open GitHub: {e}")

# Initialize the main window with title
app = tk.Tk()
app.title("YT Downloader")

# Configure window appearance
window_width = 320
window_height = 420
app.configure(bg="#2e2e2e") 

# Calculate screen dimensions for centering
screen_width = app.winfo_screenwidth()
screen_height = app.winfo_screenheight()

# Center window on screen
position_top = int(screen_height / 2 - window_height / 2)
position_left = int(screen_width / 2 - window_width / 2)

# Apply window geometry settings
app.geometry(f'{window_width}x{window_height}+{position_left}+{position_top}')

# Lock window size
app.resizable(False, False)

# Load and set application icon
if hasattr(sys, "_MEIPASS"):
    icon_path = os.path.join(sys._MEIPASS, "icon.png")
else:
    icon_path = "icon.png"

try:
    icon = tk.PhotoImage(file=icon_path)
    app.iconphoto(True, icon)
except Exception as e:
    print(f"Failed to load icon: {e}")

# URL input
tk.Label(app, text="YouTube URL:", bg="#2e2e2e", fg="white").pack(pady=5)

url_frame = tk.Frame(app, bg="#2e2e2e")
url_frame.pack(pady=5)

url_entry = tk.Entry(url_frame, width=35, bg="#555555", fg="white")
url_entry.pack(side=tk.LEFT, padx=5)

def paste_url():
    try:
        url_entry.delete(0, tk.END)
        url_entry.insert(0, app.clipboard_get())
    except tk.TclError:
        pass

paste_button = tk.Button(url_frame, text="Paste", command=paste_url, bg="#555555", fg="white")
paste_button.pack(side=tk.LEFT)

# Fetch qualities button
fetch_button = tk.Button(app, text="Fetch Qualities", command=fetch_qualities, bg="#555555", fg="white")
fetch_button.pack(pady=5)

# Quality selection
tk.Label(app, text="Select Video Quality:", bg="#2e2e2e", fg="white").pack(pady=5)
quality_var = tk.StringVar()
quality_dropdown = ttk.Combobox(app, textvariable=quality_var, state="readonly")
quality_dropdown.pack(pady=5)

# Folder selection
tk.Label(app, text="Download Folder:", bg="#2e2e2e", fg="white").pack(pady=5)
folder_path = tk.StringVar()
folder_entry = tk.Entry(app, textvariable=folder_path, width=50, bg="#555555", fg="white")
folder_entry.pack(pady=5)
browse_button = tk.Button(app, text="Browse", command=browse_folder, bg="#555555", fg="white")
browse_button.pack(pady=5)

# Progress bar
tk.Label(app, text="Download Progress:", bg="#2e2e2e", fg="white").pack(pady=5)
progress_var = tk.DoubleVar()
progress_bar = ttk.Progressbar(app, variable=progress_var, maximum=100)
progress_bar.pack(pady=5, fill=tk.X, padx=10)

# Size log
download_size_log = tk.StringVar()
download_size_log.set("")
download_size_log_label = tk.Label(app, textvariable=download_size_log, bg="#2e2e2e", fg="white")

# Create a frame to hold the download buttons
button_frame = tk.Frame(app, bg="#2e2e2e")
button_frame.pack(pady=10)

# Download video button
download_video_button = tk.Button(button_frame, text="Download Video", command=download_video, bg="#555555", fg="white", state=tk.DISABLED)
download_video_button.pack(side=tk.LEFT, padx=5)

# Download MP3 button
download_mp3_button = tk.Button(button_frame, text="Download MP3", command=download_mp3, bg="#555555", fg="white", state=tk.DISABLED)
download_mp3_button.pack(side=tk.LEFT, padx=5)

# Update banner
update_banner = tk.Frame(app, bg="#1a6b3c", pady=4)
update_label = tk.Label(update_banner, text="", bg="#1a6b3c", fg="white", font=("Arial", 8))
update_label.pack(side=tk.LEFT, padx=8)
update_btn = tk.Button(update_banner, text="Update Now", bg="#25a35f", fg="white",
                       font=("Arial", 8, "bold"), relief=tk.FLAT, padx=6, pady=1)
update_btn.pack(side=tk.LEFT, padx=4)
dismiss_btn = tk.Button(update_banner, text="✕", bg="#1a6b3c", fg="#aaffcc",
                        font=("Arial", 8), relief=tk.FLAT, padx=4, pady=1)
dismiss_btn.pack(side=tk.RIGHT, padx=4)

# Author label
name_label = tk.Label(app, text="Nubsuki", font=("Arial", 6), fg="white", bg="#2e2e2e", cursor="hand2", padx=10, pady=10)
name_label.place(relx=1.0, rely=1.0, anchor="se")

# Bind the label click to open GitHub
name_label.bind("<Button-1>", open_github)

# Start background update check
threading.Thread(target=check_for_updates, daemon=True).start()

app.mainloop()