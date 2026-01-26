Contributing
============

Guidelines for contributing to the Platform repository.

Development Setup
-----------------

.. code-block:: bash

   # Clone repository
   git clone https://github.com/achimdehnert/platform.git
   cd platform
   
   # Create virtual environment
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   # or: .venv\Scripts\activate  # Windows
   
   # Install in development mode
   pip install -e "packages/creative-services[dev]"

Code Style
----------

- **Python**: Follow PEP 8
- **Docstrings**: Google style
- **Type Hints**: Required for all public functions
- **Line Length**: 100 characters max

Testing
-------

.. code-block:: bash

   # Run tests
   pytest packages/creative-services/tests/
   
   # With coverage
   pytest --cov=creative_services packages/creative-services/tests/

Pull Request Process
--------------------

1. Create feature branch from ``main``
2. Write tests for new functionality
3. Update documentation
4. Run linting and tests
5. Submit PR with clear description

Documentation
-------------

Build documentation locally:

.. code-block:: bash

   cd docs
   pip install -r requirements.txt
   make html
   
   # View at docs/_build/html/index.html
