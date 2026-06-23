from PIL import Image
try:
    img = Image.open('apps/student_certificate/media/certificate (1).png')
    print(f"Image format: {img.format}")
    print(f"Image size: {img.size} (width, height)")
    print(f"Image mode: {img.mode}")
except Exception as e:
    print(f"Failed to inspect image: {e}")
