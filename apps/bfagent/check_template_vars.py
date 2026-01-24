import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.bfagent.models import PromptTemplate

t = PromptTemplate.objects.get(template_key='chapter_outline', version='1.0')
print('Template:', t.name)
print('Required Variables:', t.required_variables)
print()
print('User Prompt Template (first 800 chars):')
print(t.user_prompt_template[:800])
