Quickstart
==========

Travel Beat in 5 Minuten starten.

Voraussetzungen
---------------

- Python 3.12+
- PostgreSQL 15+
- Redis 7+
- Anthropic API Key

Installation
------------

.. code-block:: bash

   # Clone repository
   git clone https://github.com/achimdehnert/travel-beat.git
   cd travel-beat

   # Virtual environment
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate

   # Dependencies
   pip install -r requirements/dev.txt

   # Environment
   cp .env.example .env
   # Edit .env with your settings

   # Database
   python manage.py migrate
   python manage.py createsuperuser

   # Run
   python manage.py runserver

Erste Reise erstellen
---------------------

1. Öffne http://localhost:8000
2. Registriere dich oder logge dich ein
3. Klicke auf "Neue Reise"
4. Folge dem Wizard (4 Schritte)
5. Warte auf die Story-Generierung
6. Lies deine personalisierte Geschichte!
