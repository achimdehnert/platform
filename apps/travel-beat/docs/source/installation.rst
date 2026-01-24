Installation
============

Requirements
------------

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Node.js 18+ (optional, for frontend assets)

Local Development Setup
-----------------------

1. Clone the repository:

.. code-block:: bash

   git clone https://github.com/achimdehnert/travel-beat.git
   cd travel-beat

2. Create virtual environment:

.. code-block:: bash

   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   .venv\Scripts\activate     # Windows

3. Install dependencies:

.. code-block:: bash

   pip install -r requirements/development.txt

4. Set up environment variables:

.. code-block:: bash

   cp .env.example .env
   # Edit .env with your settings

5. Start services with Docker:

.. code-block:: bash

   docker compose up -d db redis

6. Run migrations:

.. code-block:: bash

   python manage.py migrate

7. Create superuser:

.. code-block:: bash

   python manage.py createsuperuser

8. Start development server:

.. code-block:: bash

   python manage.py runserver

Visit http://localhost:8000 to access the application.

Production Deployment
---------------------

See :doc:`dev/deployment` for production deployment instructions.

Environment Variables
---------------------

Required variables:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Variable
     - Description
   * - ``SECRET_KEY``
     - Django secret key for cryptographic signing
   * - ``DATABASE_URL``
     - PostgreSQL connection string
   * - ``REDIS_URL``
     - Redis connection string
   * - ``ANTHROPIC_API_KEY``
     - API key for Claude story generation

Optional variables:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Variable
     - Description
   * - ``DEBUG``
     - Enable debug mode (default: False)
   * - ``ALLOWED_HOSTS``
     - Comma-separated list of allowed hosts
   * - ``STRIPE_SECRET_KEY``
     - Stripe API key for subscriptions
