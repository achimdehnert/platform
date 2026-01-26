Usage Tracker
=============

Track token usage and costs across LLM calls.

Classes
-------

UsageRecord
~~~~~~~~~~~

Single usage record:

.. code-block:: python

   @dataclass
   class UsageRecord:
       llm_id: int
       user_id: Optional[int]
       prompt_tokens: int
       completion_tokens: int
       total_tokens: int
       cost: float
       timestamp: datetime
       metadata: dict

UsageStats
~~~~~~~~~~

Aggregated statistics:

.. code-block:: python

   @dataclass
   class UsageStats:
       total_requests: int
       total_tokens: int
       total_prompt_tokens: int
       total_completion_tokens: int
       total_cost: float
       period_start: Optional[datetime]
       period_end: Optional[datetime]

Implementations
---------------

InMemoryTracker
~~~~~~~~~~~~~~~

Simple in-memory tracker for development:

.. code-block:: python

   from creative_services import InMemoryTracker
   
   tracker = InMemoryTracker()
   
   # Record usage
   tracker.record(
       llm_id=1,
       user_id=123,
       prompt_tokens=100,
       completion_tokens=500,
       cost=0.001,
   )
   
   # Get statistics
   stats = tracker.get_stats(user_id=123)
   print(f"Total cost: ${stats.total_cost:.4f}")
   print(f"Total tokens: {stats.total_tokens}")

DjangoUsageTracker
~~~~~~~~~~~~~~~~~~

Database-backed tracker for production:

.. code-block:: python

   from creative_services.adapters import DjangoUsageTracker
   
   tracker = DjangoUsageTracker()
   
   # Same interface as InMemoryTracker
   tracker.record(
       llm_id=1,
       user_id=request.user.id,
       prompt_tokens=100,
       completion_tokens=500,
       cost=0.001,
   )

Cost Calculation
----------------

Helper function for cost calculation:

.. code-block:: python

   from creative_services.core.usage_tracker import calculate_cost
   
   cost = calculate_cost(
       prompt_tokens=1000,
       completion_tokens=2000,
       cost_per_1k_input=0.00015,   # GPT-4o-mini input
       cost_per_1k_output=0.0006,   # GPT-4o-mini output
   )
   print(f"Cost: ${cost:.6f}")  # $0.001350

Cost Reference
--------------

.. list-table::
   :header-rows: 1
   :widths: 25 25 25 25

   * - Model
     - Input $/1K
     - Output $/1K
     - Tier
   * - GPT-3.5 Turbo
     - $0.0005
     - $0.0015
     - Economy
   * - GPT-4o-mini
     - $0.00015
     - $0.0006
     - Standard
   * - GPT-4o
     - $0.005
     - $0.015
     - Premium
   * - Claude 3 Haiku
     - $0.00025
     - $0.00125
     - Economy
   * - Claude 3.5 Sonnet
     - $0.003
     - $0.015
     - Standard
   * - Claude 3 Opus
     - $0.015
     - $0.075
     - Premium

Integration Example
-------------------

Track usage in a story generator:

.. code-block:: python

   from creative_services import DynamicLLMClient, InMemoryTracker
   
   tracker = InMemoryTracker()
   client = DynamicLLMClient(registry, tracker=tracker)
   
   # Usage is automatically tracked
   response = await client.generate(
       prompt="Write a story",
       tier=LLMTier.STANDARD,
       user_id=123,
   )
   
   # Check usage
   stats = tracker.get_stats(user_id=123)
   print(f"This session: {stats.total_tokens} tokens, ${stats.total_cost:.4f}")
