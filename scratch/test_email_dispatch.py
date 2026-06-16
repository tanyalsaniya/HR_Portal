import os
import sys
import django

# Configure DLL path for WeasyPrint/GTK on Windows
tess_path = r"C:\Program Files\Tesseract-OCR"
if os.path.exists(tess_path):
    os.environ["PATH"] = tess_path + os.pathsep + os.environ.get("PATH", "")
    if hasattr(os, "add_dll_directory"):
        try:
            os.add_dll_directory(tess_path)
            print("Successfully added DLL directory")
        except Exception as e:
            print("Failed to add DLL directory:", e)

# Add 'apps' folder to Python path
sys.path.insert(0, os.path.abspath('apps'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from exit_formality.models import ExitRequest
from exit_formality.tasks import send_exit_documents_after_fully_exited

exit_requests = ExitRequest.objects.all()
print(f"Total ExitRequests: {exit_requests.count()}")
for req in exit_requests:
    print(f"ID: {req.id}, Employee: {req.employee.first_name} {req.employee.last_name}, Status: {req.status}, Email docs: {req.email_documents}")

# Let's test generating documents or executing the task for the latest fully exited request if any
latest = exit_requests.filter(status='FULLY_EXITED').first()
if latest:
    print(f"Testing document generation for ExitRequest ID: {latest.id}")
    res = send_exit_documents_after_fully_exited(latest.id)
    print(f"Result: {res}")
else:
    latest = exit_requests.first()
    if latest:
        print(f"Testing document generation for latest non-fully exited ExitRequest ID: {latest.id}")
        res = send_exit_documents_after_fully_exited(latest.id)
        print(f"Result: {res}")
