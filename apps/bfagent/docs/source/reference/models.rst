Model API-Referenz
==================

Diese Seite dokumentiert alle Django-Models im BF Agent Framework.
Die Dokumentation wird automatisch aus den Model-Definitionen generiert.

.. contents:: Inhaltsverzeichnis
   :local:
   :depth: 2


Writing Hub Models
------------------

Models für die Bucherstellung.

BookProject
~~~~~~~~~~~

.. code-block:: python

   from apps.writing_hub.models import BookProject, Chapter, Character
   
   # Buchprojekt erstellen
   project = BookProject.objects.create(
       title="Mein Roman",
       genre="fantasy",
       target_word_count=80000
   )

Chapter
~~~~~~~

Kapitel eines Buchprojekts.

.. code-block:: python

   # Kapitel hinzufügen
   chapter = Chapter.objects.create(
       book=project,
       chapter_number=1,
       title="Der Anfang",
       content="Es war einmal..."
   )

Character
~~~~~~~~~

Charaktere in einem Buchprojekt.

.. code-block:: python

   # Charakter erstellen
   character = Character.objects.create(
       book=project,
       name="Elena",
       role="protagonist",
       description="Die Hauptfigur..."
   )


CAD Hub Models
--------------

Models für die CAD-Analyse (IFC, DWG).

.. code-block:: python

   from apps.cad_hub.models import CADProject, IFCModel, Room
   
   # IFC-Modell analysieren
   model = IFCModel.objects.get(id=model_id)
   rooms = model.rooms.all()


Core Models
-----------

Zentrale Models für das gesamte System.

Handler
~~~~~~~

.. code-block:: python

   from apps.core.models import Handler
   
   # Alle aktiven Handler abrufen
   handlers = Handler.objects.filter(is_active=True)

NavigationSection / NavigationItem
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from apps.control_center.models import NavigationSection, NavigationItem
   
   # Navigation für ein Hub abrufen
   section = NavigationSection.objects.get(code='WRITING_HUB')
   items = section.items.filter(is_active=True)


Model-Beziehungen
-----------------

Entity-Relationship-Diagramm der Writing Hub Domain:

.. mermaid::

   erDiagram
       BookProject ||--o{ Chapter : contains
       BookProject ||--o{ Character : has
       BookProject ||--o{ World : has
       Chapter ||--o{ Scene : contains
       Scene }o--o{ Character : features
       World ||--o{ Location : contains


Verwendungsbeispiele
--------------------

Buchprojekt mit Kapiteln erstellen
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from apps.writing_hub.models import BookProject, Chapter
   
   # Projekt erstellen
   project = BookProject.objects.create(
       title="Die Reise",
       genre="fantasy",
       target_word_count=80000
   )
   
   # Kapitel hinzufügen
   for i in range(1, 11):
       Chapter.objects.create(
           book=project,
           chapter_number=i,
           title=f"Kapitel {i}",
           status="draft"
       )


Queries mit Prefetch
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from django.db.models import Prefetch
   from apps.writing_hub.models import BookProject, Chapter
   
   # Effiziente Abfrage mit allen Relations
   projects = BookProject.objects.prefetch_related(
       'chapters',
       'characters',
       Prefetch(
           'chapters',
           queryset=Chapter.objects.filter(status='published')
       )
   ).filter(status='active')


Model-Signals
-------------

Das System verwendet Django Signals für Automatisierung:

.. code-block:: python

   from django.db.models.signals import post_save
   from django.dispatch import receiver
   from apps.writing_hub.models import BookProject
   
   @receiver(post_save, sender=BookProject)
   def on_project_created(sender, instance, created, **kwargs):
       """Wird aufgerufen wenn ein neues Projekt erstellt wird."""
       if created:
           # Initialisiere Standard-Struktur
           from apps.writing_hub.services import initialize_project
           initialize_project(instance.id)
