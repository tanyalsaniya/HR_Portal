from student_certificate.models import Student, Course
from django.db.models import F
from datetime import timedelta
import re

count = 0
for s in Student.objects.filter(joining_date=F('completion_date')):
    days = 180
    if s.enrolled_course:
        dur = s.enrolled_course.default_duration.lower()
        m = re.search(r'(\d+)\s*month', dur)
        w = re.search(r'(\d+)\s*week', dur)
        d = re.search(r'(\d+)\s*day', dur)
        if m:
            days = int(m.group(1)) * 30
        elif w:
            days = int(w.group(1)) * 7
        elif d:
            days = int(d.group(1))
    s.completion_date = s.joining_date + timedelta(days=days)
    s.save()
    count += 1

print(f"Fixed {count} students with matching joining and completion dates.")
