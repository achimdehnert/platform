LLM Client
==========

The ``LLMClient`` provides a unified interface for multiple LLM providers.

Classes
-------

LLMProvider
~~~~~~~~~~~

Enum for supported providers:

.. code-block:: python

   class LLMProvider(str, Enum):
       OPENAI = "openai"
       ANTHROPIC = "anthropic"
       GROQ = "groq"
       OLLAMA = "ollama"

LLMConfig
~~~~~~~~~

Configuration for LLM client:

.. code-block:: python

   @dataclass
   class LLMConfig:
       provider: LLMProvider = LLMProvider.OPENAI
       model: Optional[str] = None
       api_key: Optional[str] = None
       base_url: Optional[str] = None
       max_tokens: int = 4096
       temperature: float = 0.7

LLMResponse
~~~~~~~~~~~

Standardized response from any provider:

.. code-block:: python

   class LLMResponse(BaseModel):
       content: str
       model: str
       provider: LLMProvider
       usage: dict[str, Any]
       raw_response: Optional[dict[str, Any]]
       
       @property
       def total_tokens(self) -> int:
           """Get total tokens used."""

LLMClient
~~~~~~~~~

Main client class:

.. code-block:: python

   class LLMClient:
       def __init__(self, config: LLMConfig):
           ...
       
       async def generate(
           self,
           prompt: str,
           system_prompt: Optional[str] = None,
           **kwargs
       ) -> LLMResponse:
           """Generate text using configured LLM."""

Usage Examples
--------------

Basic Usage
~~~~~~~~~~~

.. code-block:: python

   from creative_services import LLMClient, LLMConfig, LLMProvider
   
   config = LLMConfig(
       provider=LLMProvider.OPENAI,
       model="gpt-4o-mini",
       temperature=0.7,
   )
   
   client = LLMClient(config)
   
   response = await client.generate(
       prompt="Write a haiku about coding",
       system_prompt="You are a poet",
   )
   
   print(response.content)

With Anthropic
~~~~~~~~~~~~~~

.. code-block:: python

   config = LLMConfig(
       provider=LLMProvider.ANTHROPIC,
       model="claude-3-5-sonnet-20241022",
   )
   
   client = LLMClient(config)
   response = await client.generate("Explain quantum computing")

With Local Ollama
~~~~~~~~~~~~~~~~~

.. code-block:: python

   config = LLMConfig(
       provider=LLMProvider.OLLAMA,
       model="llama3.2",
       base_url="http://localhost:11434",
   )
   
   client = LLMClient(config)
   response = await client.generate("Hello, world!")

Default Models
--------------

Each provider has a default model:

.. list-table::
   :header-rows: 1

   * - Provider
     - Default Model
   * - OpenAI
     - gpt-4o-mini
   * - Anthropic
     - claude-3-5-sonnet-20241022
   * - Groq
     - llama-3.3-70b-versatile
   * - Ollama
     - llama3.2

Error Handling
--------------

The client uses ``tenacity`` for automatic retries:

.. code-block:: python

   @retry(
       stop=stop_after_attempt(3),
       wait=wait_exponential(multiplier=1, min=1, max=10),
       retry=retry_if_exception_type((httpx.HTTPError, Exception)),
   )
   async def generate(self, ...):
       ...
