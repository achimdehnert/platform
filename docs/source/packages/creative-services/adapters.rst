Adapters
========

Adapters for integrating creative-services with existing applications.

Django Adapter
--------------

DjangoLLMRegistry
~~~~~~~~~~~~~~~~~

Uses Django ORM for LLM configuration:

.. code-block:: python

   from creative_services.adapters import DjangoLLMRegistry
   
   # Reads from Django Llms model
   registry = DjangoLLMRegistry()
   
   # Same interface as DictRegistry
   llm = registry.get_by_tier(LLMTier.STANDARD)
   active = registry.list_active()

Required Django Model
~~~~~~~~~~~~~~~~~~~~~

The adapter expects a Django model with these fields:

.. code-block:: python

   class Llms(models.Model):
       name = models.CharField(max_length=100)
       provider = models.CharField(max_length=50)
       model_name = models.CharField(max_length=100)
       tier = models.CharField(max_length=20)
       api_key = models.CharField(max_length=500, blank=True)
       api_endpoint = models.URLField(blank=True)
       max_tokens = models.IntegerField(default=4096)
       temperature = models.FloatField(default=0.7)
       cost_per_1k_input = models.DecimalField(...)
       cost_per_1k_output = models.DecimalField(...)
       is_active = models.BooleanField(default=True)

DjangoUsageTracker
~~~~~~~~~~~~~~~~~~

Stores usage records in Django database:

.. code-block:: python

   from creative_services.adapters import DjangoUsageTracker
   
   tracker = DjangoUsageTracker()
   
   tracker.record(
       llm_id=1,
       user_id=request.user.id,
       prompt_tokens=100,
       completion_tokens=500,
       cost=0.001,
   )

BFAgent Compatibility
---------------------

BFAgentLLMBridge
~~~~~~~~~~~~~~~~

Backward-compatible synchronous API for BFAgent:

.. code-block:: python

   from creative_services.adapters import BFAgentLLMBridge
   
   bridge = BFAgentLLMBridge()
   
   # Synchronous API (wraps async internally)
   result = bridge.generate_text(
       prompt="Write a story",
       system_prompt="You are a writer",
       tier="standard",
   )
   
   print(result)  # Generated text

Async Bridge
~~~~~~~~~~~~

For async contexts in BFAgent:

.. code-block:: python

   from creative_services.adapters import AsyncBFAgentLLMBridge
   
   bridge = AsyncBFAgentLLMBridge()
   
   result = await bridge.generate_text(
       prompt="Write a story",
       tier="premium",
   )

Migration Guide
---------------

Migrating from direct OpenAI to creative-services:

Before
~~~~~~

.. code-block:: python

   import openai
   
   client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
   response = client.chat.completions.create(
       model="gpt-4o-mini",
       messages=[{"role": "user", "content": prompt}],
   )
   content = response.choices[0].message.content

After
~~~~~

.. code-block:: python

   from creative_services import DictRegistry, DynamicLLMClient, LLMTier
   
   registry = DictRegistry.from_env()
   client = DynamicLLMClient(registry)
   
   response = await client.generate(
       prompt=prompt,
       tier=LLMTier.STANDARD,
   )
   content = response.content

Benefits of Migration
~~~~~~~~~~~~~~~~~~~~~

1. **Provider Agnostic**: Switch between OpenAI, Anthropic, etc. without code changes
2. **Tier-Based Selection**: Automatic model selection based on quality/cost needs
3. **Usage Tracking**: Built-in token and cost tracking
4. **Retry Logic**: Automatic retries with exponential backoff
5. **DB-Driven Config**: Change models via database, not code
