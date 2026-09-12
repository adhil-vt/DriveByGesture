from PIL import Image

img = Image.open("resources/icons/app.png").convert("RGBA")

sizes = [
    (16, 16),
    (24, 24),
    (32, 32),
    (48, 48),
    (64, 64),
    (128, 128),
    (256, 256),
]

img.save(
    "resources/icons/app.ico",
    format="ICO",
    sizes=sizes,
)

print("✅ Professional Windows multi-resolution icon created.")