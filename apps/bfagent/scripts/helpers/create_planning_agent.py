#!/usr/bin/env python
"""
Quick script to create Planning Agent in database
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

import django
django.setup()

from apps.bfagent.models import Agents, Llms

def create_planning_agent():
    """Create Planning Agent if it doesn't exist"""
    
    # Check if agent already exists
    existing = Agents.objects.filter(agent_type="planning_agent").first()
    if existing:
        print(f"✅ Planning Agent already exists: {existing.name}")
        return existing
    
    # Get default LLM
    default_llm = Llms.objects.filter(is_active=True).first()
    if not default_llm:
        print("❌ No active LLM found! Please create an LLM first.")
        return None
    
    # Create Planning Agent
    planning_agent = Agents.objects.create(
        name="Planning Agent",
        agent_type="planning_agent",
        status="active",
        description="Handles project planning, structure, and organization",
        system_prompt="You are a planning specialist focused on project structure and organization.",
        instructions="Analyze requirements, create outlines, and structure projects effectively.",
        llm_model=default_llm,
        creativity_level=0.7,
        consistency_weight=0.8
    )
    
    print(f"✅ Created Planning Agent: {planning_agent.name} (ID: {planning_agent.id})")
    print(f"   LLM: {default_llm.name}")
    print(f"   Status: {planning_agent.status}")
    
    return planning_agent

if __name__ == "__main__":
    print("🔧 Creating Planning Agent...")
    agent = create_planning_agent()
    if agent:
        print("\n✅ Done! Run 'make agent-sync' to add actions.")
