Stories API
===========

Models
------

.. automodule:: apps.stories.models
   :members:
   :undoc-members:
   :show-inheritance:

Story Model
~~~~~~~~~~~

The Story model represents a generated travel story.

**Fields:**

- ``trip`` - Associated trip (OneToOneField)
- ``title`` - Story title
- ``status`` - pending/generating/completed/failed
- ``total_chapters`` - Expected chapter count
- ``created_at`` - Creation timestamp
- ``completed_at`` - Completion timestamp

**Properties:**

- ``generated_chapters`` - Count of completed chapters
- ``progress_percent`` - Generation progress (0-100)

**Status Values:**

.. code-block:: python

   STATUS_PENDING = 'pending'
   STATUS_GENERATING = 'generating'
   STATUS_COMPLETED = 'completed'
   STATUS_FAILED = 'failed'

Chapter Model
~~~~~~~~~~~~~

The Chapter model represents individual story chapters.

**Fields:**

- ``story`` - Parent story (ForeignKey)
- ``number`` - Chapter number (1-indexed)
- ``title`` - Chapter title
- ``content`` - Chapter text content
- ``word_count`` - Automatic word count
- ``created_at`` - Generation timestamp

Views
-----

.. automodule:: apps.stories.views
   :members:
   :undoc-members:

**story_detail**
   Display complete story with all chapters

**story_progress**
   Show generation progress page

**chapter_read**
   Display individual chapter

**export_markdown**
   Download story as Markdown file

API Endpoints
~~~~~~~~~~~~~

.. code-block:: python

   # JSON API for frontend polling
   /stories/<id>/api/status/    # Get generation status

Response format:

.. code-block:: json

   {
     "status": "generating",
     "progress": 45,
     "current_chapter": 3,
     "total_chapters": 7
   }

Celery Tasks
------------

.. automodule:: apps.stories.tasks
   :members:
   :undoc-members:

**generate_story_task**
   Async task for story generation via Celery

Task Flow:

1. Receives trip_id and story_id
2. Fetches trip details and stops
3. Calls AI provider for each chapter
4. Saves chapters to database
5. Updates story status on completion

URL Patterns
------------

.. code-block:: python

   /stories/                      # Story list
   /stories/<id>/                 # Story detail/reader
   /stories/<id>/progress/        # Generation progress
   /stories/<id>/chapter/<num>/   # Individual chapter
   /stories/<id>/export/markdown/ # Markdown export
