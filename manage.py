#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    # Configure DLL path for WeasyPrint/GTK on Windows
    import os
    tess_path = r"C:\Program Files\Tesseract-OCR"
    if os.path.exists(tess_path):
        os.environ["PATH"] = tess_path + os.pathsep + os.environ.get("PATH", "")
        if hasattr(os, "add_dll_directory"):
            try:
                os.add_dll_directory(tess_path)
            except Exception:
                pass

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    # Patch Django's template context copy bug on Python 3.14
    try:
        from django.template.context import BaseContext
        def _base_context_copy(self):
            cls = self.__class__
            duplicate = cls.__new__(cls)
            duplicate.__dict__.update(self.__dict__)
            duplicate.dicts = self.dicts[:]
            return duplicate
        BaseContext.__copy__ = _base_context_copy
    except ImportError:
        pass

    execute_from_command_line(sys.argv)



if __name__ == '__main__':
    main()
