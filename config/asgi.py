"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

# Configure DLL path for WeasyPrint/GTK on Windows
tess_path = r"C:\Program Files\Tesseract-OCR"
if os.path.exists(tess_path):
    os.environ["PATH"] = tess_path + os.pathsep + os.environ.get("PATH", "")
    if hasattr(os, "add_dll_directory"):
        try:
            os.add_dll_directory(tess_path)
        except Exception:
            pass

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_asgi_application()
