import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.urls import reverse, NoReverseMatch
import re

# Read sidebar_config.py
with open('apps/bfagent/utils/sidebar_config.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find all URL patterns like "url": "namespace:name"
url_pattern = r'"url":\s*"([^"]+)"'
urls = re.findall(url_pattern, content)

# Valid URLs from control_center
VALID_URLS = [
    'control_center:dashboard',
    'control_center:api-status',
    'control_center:metrics',
    'control_center:model-consistency',
    'control_center:screen-documentation',
    'control_center:genagent-dashboard',
    'control_center:feature-planning-dashboard',
    'control_center:migration-registry-dashboard',
    'control_center:code-review-dashboard',
]

print("=== Checking Sidebar URLs ===\n")

invalid_control_center = []
for url in set(urls):
    if url.startswith('control_center:'):
        if url not in VALID_URLS:
            invalid_control_center.append(url)
            print(f"❌ INVALID: {url}")

print(f"\n\n=== Summary ===")
print(f"Total unique URLs found: {len(set(urls))}")
print(f"Invalid control_center URLs: {len(invalid_control_center)}")

if invalid_control_center:
    print(f"\n❌ INVALID URLs:")
    for url in sorted(set(invalid_control_center)):
        print(f"   - {url}")
