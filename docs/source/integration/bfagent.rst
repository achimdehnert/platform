BFAgent Integration
===================

How to integrate creative-services with BFAgent.

Installation
------------

.. code-block:: bash

   cd /path/to/bfagent
   source .venv/bin/activate
   pip install -e /path/to/platform/packages/creative-services

Configuration
-------------

Ensure environment variables are set:

.. code-block:: bash

   # In .env or environment
   OPENAI_API_KEY=sk-...
   ANTHROPIC_API_KEY=sk-ant-...  # Optional

Using DjangoLLMRegistry
-----------------------

BFAgent has an existing ``Llms`` model. Use the Django adapter:

.. code-block:: python

   from creative_services.adapters import DjangoLLMRegistry, DjangoUsageTracker
   from creative_services import DynamicLLMClient, LLMTier
   
   # Use existing Llms model
   registry = DjangoLLMRegistry()
   tracker = DjangoUsageTracker()
   client = DynamicLLMClient(registry, tracker=tracker)
   
   # Generate with tier selection
   response = await client.generate(
       prompt="Write a character description",
       tier=LLMTier.STANDARD,
       user_id=request.user.id,
   )

Backward Compatibility
----------------------

For existing synchronous code, use the bridge:

.. code-block:: python

   from creative_services.adapters import BFAgentLLMBridge
   
   bridge = BFAgentLLMBridge()
   
   # Drop-in replacement for existing LLM calls
   result = bridge.generate_text(
       prompt="Write a story",
       tier="standard",
   )

Migration Path
--------------

1. **Phase 1**: Install creative-services alongside existing code
2. **Phase 2**: Use BFAgentLLMBridge for new features
3. **Phase 3**: Gradually migrate existing handlers
4. **Phase 4**: Remove direct OpenAI/Anthropic dependencies

Example: Migrating a Handler
----------------------------

Before:

.. code-block:: python

   class StoryHandler:
       def generate(self, prompt):
           client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
           response = client.chat.completions.create(
               model="gpt-4o-mini",
               messages=[{"role": "user", "content": prompt}],
           )
           return response.choices[0].message.content

After:

.. code-block:: python

   from creative_services.adapters import BFAgentLLMBridge
   
   class StoryHandler:
       def __init__(self):
           self.bridge = BFAgentLLMBridge()
       
       def generate(self, prompt):
           return self.bridge.generate_text(
               prompt=prompt,
               tier="standard",
           )
