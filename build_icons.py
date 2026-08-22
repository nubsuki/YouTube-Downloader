"""
Rebuild icon.ico and favicon.ico from icon.png with all required Windows sizes:
16x16, 32x32, 48x48, 64x64, 128x128, 256x256
"""
from PIL import Image
import os

src = Image.open("icon.png").convert("RGBA")

sizes = [16, 32, 48, 64, 128, 256]

# Build list of resized images (high-quality Lanczos resampling)
frames = [src.resize((s, s), Image.LANCZOS) for s in sizes]

# Save multi-size icon.ico (used in taskbar / window titlebar)
src.resize((256, 256), Image.LANCZOS).save(
    "icon.ico",
    format="ICO",
    sizes=[(s, s) for s in sizes],
)
print("Saved icon.ico with sizes:", sizes)

# Save favicon.ico (same, used by PyInstaller as the exe icon)
src.resize((256, 256), Image.LANCZOS).save(
    "favicon.ico",
    format="ICO",
    sizes=[(s, s) for s in sizes],
)
print("Saved favicon.ico with sizes:", sizes)

# Also save a high-res icon.png (256x256) for tkinter PhotoImage fallback
src.resize((256, 256), Image.LANCZOS).save("icon.png")
print("Saved icon.png at 256x256")
