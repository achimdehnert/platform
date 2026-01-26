TravelBeat Integration
======================

How creative-services is integrated with TravelBeat for story generation.

Installation
------------

.. code-block:: bash

   cd /path/to/travel-beat
   source .venv/bin/activate
   pip install -e /path/to/platform/packages/creative-services

StoryGenerator Integration
--------------------------

The ``StoryGenerator`` class uses creative-services for LLM calls:

.. code-block:: python

   from apps.stories.services import StoryGenerator
   
   # Default: uses STANDARD tier (GPT-4o-mini)
   generator = StoryGenerator(trip, user)
   
   # Specify tier explicitly
   generator = StoryGenerator(trip, user, tier="premium")
   
   # Generate story with progress updates
   for progress in generator.generate_story(story):
       print(f"{progress['phase']}: {progress['message']}")

Tier Selection
--------------

.. list-table::
   :header-rows: 1

   * - Tier
     - Model
     - Use Case
   * - economy
     - GPT-3.5 Turbo
     - Testing, drafts
   * - standard
     - GPT-4o-mini
     - Production (default)
   * - premium
     - GPT-4o
     - High-quality output

Error Recovery
--------------

The StoryGenerator includes robust error handling:

1. **Retry per Chapter**: Up to 3 attempts per chapter
2. **Recovery Pass**: Failed chapters retried after first pass
3. **Missing Chapter Fill**: Simplified prompts for stubborn failures

.. code-block:: python

   # Configuration
   MAX_CHAPTER_RETRIES = 3
   RETRY_DELAY_SECONDS = 2
   MAX_OUTLINE_RETRIES = 3

Fallback Strategy
-----------------

.. code-block:: text

   creative-services available?
       │
       ├── YES → DynamicLLMClient (tier-based)
       │         └── API call fails → Retry with backoff
       │
       └── NO → Direct OpenAI client
                └── API call fails → Mock generation

Environment Variables
---------------------

Set in ``.env``:

.. code-block:: bash

   OPENAI_API_KEY=sk-...

The key is automatically loaded via ``python-dotenv`` and passed to creative-services.
