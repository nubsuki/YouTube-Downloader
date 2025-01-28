import sys
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from yt_dlp import YoutubeDL
import webbrowser
import threading

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
        ydl_opts = {'quiet': True}
        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                formats = info.get('formats', [])
                qualities = sorted(
                    set(f"{fmt['height']}p" for fmt in formats if fmt.get('height') and fmt.get('ext') == 'mp4'),
                    key=lambda x: int(x.replace('p', ''))
                )
                if not qualities:
                    messagebox.showerror("Error", "No available video qualities found.")
                    return
                # Update the quality dropdown with fetched qualities
                quality_dropdown['values'] = qualities
                quality_var.set(qualities[-1])  # Automatically set to the highest quality
                download_button.config(state=tk.NORMAL)  # Enable download button
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
        'format': f'bestvideo[height={video_quality.replace("p", "")}]+bestaudio/best',
        'outtmpl': os.path.join(output_folder, '%(title)s.%(ext)s'),
        'merge_output_format': 'mp4',
        'progress_hooks': [progress_hook],
    }

    # Disable buttons during download
    fetch_button.config(state=tk.DISABLED)
    download_button.config(state=tk.DISABLED)

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
            download_button.config(state=tk.DISABLED)

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
url_entry = tk.Entry(app, width=50, bg="#555555", fg="white")
url_entry.pack(pady=5)

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

# Download button
download_button = tk.Button(app, text="Download", command=download_video, bg="#555555", fg="white", state=tk.DISABLED)
download_button.pack(pady=10)

# Author label
name_label = tk.Label(app, text="Nubsuki", font=("Arial", 6), fg="white", bg="#2e2e2e", cursor="hand2", padx=10, pady=10)
name_label.place(relx=1.0, rely=1.0, anchor="se")

# Bind the label click to open GitHub
name_label.bind("<Button-1>", open_github)

app.mainloop()