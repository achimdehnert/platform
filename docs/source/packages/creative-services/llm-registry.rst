LLM Registry
============

The registry system enables dynamic, tier-based LLM selection without code changes.

Concepts
--------

LLMTier
~~~~~~~

Quality/cost tiers for model selection:

.. code-block:: python

   class LLMTier(str, Enum):
       ECONOMY = "economy"    # Cheapest, high volume
       STANDARD = "standard"  # Balanced quality/cost
       PREMIUM = "premium"    # Best quality
       LOCAL = "local"        # Privacy, offline

LLMEntry
~~~~~~~~

Represents a configured LLM:

.. code-block:: python

   @dataclass
   class LLMEntry:
       id: int
       name: str
       provider: str          # "openai", "anthropic", etc.
       model: str             # "gpt-4o-mini", etc.
       tier: LLMTier
       api_key: Optional[str]
       api_endpoint: Optional[str]
       max_tokens: int = 4096
       temperature: float = 0.7
       cost_per_1k_input: float
       cost_per_1k_output: float
       is_active: bool = True

Registry Implementations
------------------------

DictRegistry
~~~~~~~~~~~~

In-memory registry for simple deployments:

.. code-block:: python

   from creative_services import DictRegistry
   
   # Create from environment variables
   registry = DictRegistry.from_env()
   
   # List active LLMs
   for llm in registry.list_active():
       print(f"{llm.name} ({llm.tier.value})")
   
   # Get by tier
   llm = registry.get_by_tier(LLMTier.STANDARD)

DjangoLLMRegistry
~~~~~~~~~~~~~~~~~

Database-driven registry for production:

.. code-block:: python

   from creative_services.adapters import DjangoLLMRegistry
   
   # Uses Django Llms model
   registry = DjangoLLMRegistry()
   
   # Same interface as DictRegistry
   llm = registry.get_by_tier(LLMTier.PREMIUM)

DynamicLLMClient
----------------

Client that uses registry for model selection:

.. code-block:: python

   from creative_services import DictRegistry, DynamicLLMClient, LLMTier
   
   registry = DictRegistry.from_env()
   client = DynamicLLMClient(registry)
   
   # Automatically selects best model for tier
   response = await client.generate(
       prompt="Write a story",
       tier=LLMTier.STANDARD,
   )
   
   # Or specify LLM by ID
   response = await client.generate(
       prompt="Write a story",
       llm_id=2,
   )

Tier Mappings
-------------

Default models per tier when using ``DictRegistry.from_env()``:

.. list-table::
   :header-rows: 1
   :widths: 15 30 30 25

   * - Tier
     - OpenAI
     - Anthropic
     - Groq
   * - ECONOMY
     - GPT-3.5 Turbo
     - Claude 3 Haiku
     - Llama 3.3 70B
   * - STANDARD
     - GPT-4o-mini
     - Claude 3.5 Sonnet
     - N/A
   * - PREMIUM
     - GPT-4o
     - Claude 3 Opus
     - N/A
   * - LOCAL
     - N/A
     - N/A
     - Ollama

Selection Logic
---------------

When requesting a tier, the registry:

1. Filters active LLMs matching the tier
2. Sorts by cost (cheapest first)
3. Returns the first available LLM

.. code-block:: python

   def get_by_tier(self, tier: LLMTier) -> Optional[LLMEntry]:
       matching = [e for e in self._entries if e.tier == tier and e.is_active]
       if not matching:
           return None
       return sorted(matching, key=lambda e: e.cost_per_1k_input)[0]

Custom Registry
---------------

Implement the ``LLMRegistry`` protocol for custom backends:

.. code-block:: python

   from creative_services.core.llm_registry import LLMRegistry
   
   class MyCustomRegistry:
       def get_by_id(self, llm_id: int) -> Optional[LLMEntry]:
           ...
       
       def get_by_tier(self, tier: LLMTier) -> Optional[LLMEntry]:
           ...
       
       def list_active(self) -> list[LLMEntry]:
           ...
