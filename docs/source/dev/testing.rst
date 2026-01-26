Testing
=======

Testing guidelines for Platform packages.

Running Tests
-------------

.. code-block:: bash

   # All tests
   pytest packages/creative-services/tests/
   
   # Specific test file
   pytest packages/creative-services/tests/test_llm_client.py
   
   # With verbose output
   pytest -v packages/creative-services/tests/

Test Structure
--------------

.. code-block:: text

   packages/creative-services/
   └── tests/
       ├── conftest.py          # Shared fixtures
       ├── test_llm_client.py   # LLMClient tests
       ├── test_llm_registry.py # Registry tests
       └── test_usage_tracker.py # Tracker tests

Writing Tests
-------------

Use pytest fixtures for common setup:

.. code-block:: python

   import pytest
   from creative_services import LLMClient, LLMConfig, LLMProvider
   
   @pytest.fixture
   def mock_config():
       return LLMConfig(
           provider=LLMProvider.OPENAI,
           model="gpt-4o-mini",
       )
   
   @pytest.mark.asyncio
   async def test_generate(mock_config):
       client = LLMClient(mock_config)
       # Use mocking for API calls
       ...

Mocking LLM Calls
-----------------

Use ``pytest-mock`` for API mocking:

.. code-block:: python

   @pytest.mark.asyncio
   async def test_generate_mocked(mocker):
       mock_response = mocker.patch.object(
           LLMClient,
           '_generate_openai_compatible',
           return_value=LLMResponse(
               content="Hello!",
               model="gpt-4o-mini",
               provider=LLMProvider.OPENAI,
           )
       )
       
       client = LLMClient(LLMConfig())
       response = await client.generate("Hi")
       
       assert response.content == "Hello!"

Coverage
--------

.. code-block:: bash

   # Run with coverage
   pytest --cov=creative_services --cov-report=html
   
   # View report
   open htmlcov/index.html
