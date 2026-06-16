import os
import sys
import django
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / 'apps'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
User = get_user_model()
c = Client(HTTP_HOST='localhost')
c.force_login(User.objects.filter(is_superuser=True).first())
response = c.get('/salaries/')
html_content = response.content.decode('utf-8')

from html.parser import HTMLParser

class FindParent(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.found = False
        self.parents = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        self.stack.append((tag, attrs_dict))
        if attrs_dict.get('id') == 'salaryHistoryView':
            self.found = True
            self.parents = list(self.stack)

    def handle_endtag(self, tag):
        if self.stack:
            self.stack.pop()

parser = FindParent()
parser.feed(html_content)
print("Parents found:")
for tag, attrs in parser.parents:
    print(f"Tag: {tag}, ID: {attrs.get('id')}, Class: {attrs.get('class')}")
