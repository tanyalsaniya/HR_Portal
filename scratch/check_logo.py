from PIL import Image
try:
    img = Image.open('apps/student_certificate/media/certificate (1).png')
    # Check top-left crop (logo area)
    # The image is 2380x3368. Logo would be roughly at (200, 200, 600, 600)
    logo_area = img.crop((150, 150, 650, 650))
    colors = logo_area.getcolors(maxcolors=10000)
    if colors and len(colors) > 1:
        print("Logo area contains multiple colors (logo is likely present).")
    else:
        print("Logo area is solid (logo is likely NOT present).")

    # Check top-right crop (seal area)
    seal_area = img.crop((1700, 150, 2200, 650))
    colors_seal = seal_area.getcolors(maxcolors=10000)
    if colors_seal and len(colors_seal) > 1:
        print("Seal area contains multiple colors (seal is likely present).")
    else:
        print("Seal area is solid (seal is likely NOT present).")
except Exception as e:
    print(f"Failed to analyze image: {e}")
