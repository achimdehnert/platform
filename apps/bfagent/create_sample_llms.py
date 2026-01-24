#!/usr/bin/env python
"""
Create sample LLMs for testing
"""
import os
import django
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.bfagent.models import Llms

print("=" * 70)
print("CREATING SAMPLE LLMs")
print("=" * 70)
print()

# Check if LLMs already exist
if Llms.objects.exists():
    print("⚠️  LLMs already exist. Skipping creation.")
    print(f"   Found {Llms.objects.count()} LLMs")
    for llm in Llms.objects.all():
        print(f"   - {llm.provider}/{llm.name}")
    print()
    exit(0)

# Sample LLMs to create (matching actual Llms model fields)
sample_llms = [
    {
        "provider": "OpenAI",
        "name": "GPT-4 Turbo",
        "llm_name": "gpt-4-turbo-preview",
        "api_key": "",  # To be configured
        "api_endpoint": "https://api.openai.com/v1/chat/completions",
        "max_tokens": 4096,
        "temperature": 0.7,
        "top_p": 1.0,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
        "total_tokens_used": 0,
        "total_requests": 0,
        "total_cost": 0.0,
        "cost_per_1k_tokens": 0.02,  # Average
        "description": "Most capable GPT-4 model with 128k context",
        "is_active": True,
    },
    {
        "provider": "OpenAI",
        "name": "GPT-4",
        "llm_name": "gpt-4",
        "api_key": "",
        "api_endpoint": "https://api.openai.com/v1/chat/completions",
        "max_tokens": 4096,
        "temperature": 0.7,
        "top_p": 1.0,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
        "total_tokens_used": 0,
        "total_requests": 0,
        "total_cost": 0.0,
        "cost_per_1k_tokens": 0.045,
        "description": "Standard GPT-4 model",
        "is_active": True,
    },
    {
        "provider": "OpenAI",
        "name": "GPT-3.5 Turbo",
        "llm_name": "gpt-3.5-turbo",
        "api_key": "",
        "api_endpoint": "https://api.openai.com/v1/chat/completions",
        "max_tokens": 4096,
        "temperature": 0.7,
        "top_p": 1.0,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
        "total_tokens_used": 0,
        "total_requests": 0,
        "total_cost": 0.0,
        "cost_per_1k_tokens": 0.001,
        "description": "Fast and cost-effective model",
        "is_active": True,
    },
    {
        "provider": "Anthropic",
        "name": "Claude 3 Opus",
        "llm_name": "claude-3-opus-20240229",
        "api_key": "",
        "api_endpoint": "https://api.anthropic.com/v1/messages",
        "max_tokens": 4096,
        "temperature": 0.7,
        "top_p": 1.0,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
        "total_tokens_used": 0,
        "total_requests": 0,
        "total_cost": 0.0,
        "cost_per_1k_tokens": 0.045,
        "description": "Most powerful Claude model",
        "is_active": True,
    },
    {
        "provider": "Anthropic",
        "name": "Claude 3 Sonnet",
        "llm_name": "claude-3-sonnet-20240229",
        "api_key": "",
        "api_endpoint": "https://api.anthropic.com/v1/messages",
        "max_tokens": 4096,
        "temperature": 0.7,
        "top_p": 1.0,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
        "total_tokens_used": 0,
        "total_requests": 0,
        "total_cost": 0.0,
        "cost_per_1k_tokens": 0.009,
        "description": "Balanced performance and cost",
        "is_active": True,
    },
]

created_count = 0
for llm_data in sample_llms:
    llm = Llms.objects.create(
        **llm_data,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    print(f"✅ Created: {llm.provider} / {llm.name}")
    created_count += 1

print()
print("=" * 70)
print(f"🎉 CREATED {created_count} SAMPLE LLMs")
print("=" * 70)
print()
print("NEXT STEPS:")
print("1. Refresh Admin page")
print("2. Open Prompt Template")
print("3. 'Preferred llm' dropdown should now show LLMs!")
print()
