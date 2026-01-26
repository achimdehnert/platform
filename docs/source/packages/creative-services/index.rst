Creative Services Package
=========================

AI-powered creative writing services with unified LLM access.

Overview
--------

The ``creative-services`` package provides a unified interface for:

- **Multiple LLM Providers**: OpenAI, Anthropic, Groq, Ollama
- **Tier-Based Selection**: Economy, Standard, Premium, Local
- **Usage Tracking**: Token counts and cost calculation
- **Django Integration**: ORM adapters for database-driven configuration

Installation
------------

.. code-block:: bash

   # Basic installation
   pip install -e /path/to/platform/packages/creative-services
   
   # With OpenAI support
   pip install -e "/path/to/platform/packages/creative-services[openai]"
   
   # With all providers
   pip install -e "/path/to/platform/packages/creative-services[openai,anthropic,groq]"

Quick Start
-----------

.. code-block:: python

   from creative_services import DictRegistry, DynamicLLMClient, LLMTier
   
   # Create registry from environment variables
   registry = DictRegistry.from_env()
   
   # Create dynamic client
   client = DynamicLLMClient(registry)
   
   # Generate text with tier-based selection
   response = await client.generate(
       prompt="Write a short story about a traveler",
       system_prompt="You are a creative writer",
       tier=LLMTier.STANDARD,
       max_tokens=1000,
   )
   
   print(response.content)
   print(f"Tokens used: {response.total_tokens}")

Environment Variables
---------------------

.. code-block:: bash

   # OpenAI (required for OpenAI models)
   OPENAI_API_KEY=sk-...
   
   # Anthropic (optional)
   ANTHROPIC_API_KEY=sk-ant-...
   
   # Groq (optional, free tier available)
   GROQ_API_KEY=gsk_...

Package Structure
-----------------

.. code-block:: text

   creative_services/
   ├── core/
   │   ├── llm_client.py      # LLMClient, LLMConfig, LLMResponse
   │   ├── llm_registry.py    # LLMRegistry, DictRegistry, DynamicLLMClient
   │   ├── usage_tracker.py   # UsageTracker, InMemoryTracker
   │   └── base_handler.py    # BaseHandler pattern
   │
   ├── adapters/
   │   ├── django_adapter.py  # DjangoLLMRegistry, DjangoUsageTracker
   │   └── bfagent_compat.py  # BFAgentLLMBridge
   │
   ├── character/             # Character generation handlers
   ├── story/                 # Story generation handlers
   └── dialogue/              # Dialogue generation handlers

Contents
--------

.. toctree::
   :maxdepth: 2

   llm-client
   llm-registry
   usage-tracker
   adapters
