Architecture
============

The Platform follows a modular package architecture designed for maximum reusability.

Design Principles
-----------------

1. **Separation of Concerns**: Each package has a single responsibility
2. **Provider Agnostic**: Abstract interfaces with multiple implementations
3. **DB-Driven Configuration**: No code changes to switch providers
4. **Backward Compatible**: Adapter pattern for existing applications

Package Structure
-----------------

.. code-block:: text

   platform/
   ├── packages/
   │   └── creative-services/
   │       ├── creative_services/
   │       │   ├── core/
   │       │   │   ├── llm_client.py      # Unified LLM client
   │       │   │   ├── llm_registry.py    # Tier-based selection
   │       │   │   ├── usage_tracker.py   # Cost tracking
   │       │   │   └── base_handler.py    # Handler pattern
   │       │   │
   │       │   ├── adapters/
   │       │   │   ├── django_adapter.py  # Django ORM integration
   │       │   │   └── bfagent_compat.py  # BFAgent compatibility
   │       │   │
   │       │   ├── character/             # Character generation
   │       │   ├── story/                 # Story generation
   │       │   └── dialogue/              # Dialogue generation
   │       │
   │       ├── pyproject.toml
   │       └── README.md
   │
   └── docs/
       └── source/

Core Components
---------------

LLMClient
~~~~~~~~~

Unified client supporting multiple providers:

.. code-block:: python

   from creative_services import LLMClient, LLMConfig, LLMProvider
   
   config = LLMConfig(
       provider=LLMProvider.OPENAI,
       model="gpt-4o-mini",
   )
   client = LLMClient(config)
   
   response = await client.generate(
       prompt="Write a story",
       system_prompt="You are a creative writer",
   )

LLMRegistry
~~~~~~~~~~~

Tier-based model selection:

.. code-block:: python

   from creative_services import DictRegistry, DynamicLLMClient, LLMTier
   
   registry = DictRegistry.from_env()
   client = DynamicLLMClient(registry)
   
   # Automatically selects best model for tier
   response = await client.generate(
       prompt="Write a story",
       tier=LLMTier.STANDARD,  # GPT-4o-mini or Claude Sonnet
   )

UsageTracker
~~~~~~~~~~~~

Track token usage and costs:

.. code-block:: python

   from creative_services import InMemoryTracker
   
   tracker = InMemoryTracker()
   tracker.record(
       llm_id=1,
       prompt_tokens=100,
       completion_tokens=500,
       cost=0.001,
   )
   
   stats = tracker.get_stats(user_id=123)
   print(f"Total cost: ${stats.total_cost}")

Tier System
-----------

.. list-table::
   :header-rows: 1
   :widths: 15 25 25 35

   * - Tier
     - Use Case
     - OpenAI
     - Anthropic
   * - ECONOMY
     - High volume, low cost
     - GPT-3.5 Turbo
     - Claude 3 Haiku
   * - STANDARD
     - Balanced quality/cost
     - GPT-4o-mini
     - Claude 3.5 Sonnet
   * - PREMIUM
     - Maximum quality
     - GPT-4o
     - Claude 3 Opus
   * - LOCAL
     - Privacy, offline
     - N/A
     - Ollama (Llama 3.2)

Adapter Pattern
---------------

For integrating with existing applications:

.. code-block:: python

   # Django ORM adapter
   from creative_services.adapters import DjangoLLMRegistry
   
   registry = DjangoLLMRegistry()  # Uses Django Llms model
   
   # BFAgent compatibility
   from creative_services.adapters import BFAgentLLMBridge
   
   bridge = BFAgentLLMBridge()
   result = bridge.generate_text("Write a story")  # Sync API
