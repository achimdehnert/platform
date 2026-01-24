=======
CAD Hub
=======

.. note::
   **Bau-CAD & IFC-Verarbeitung** | Status: Production Ready

Übersicht
=========

Der CAD Hub verarbeitet Baupläne und IFC-Dateien:

- **IFC Parsing**: IFC-Dateien analysieren und visualisieren
- **Raumbuch**: Automatische Raumbuch-Generierung
- **GAEB Export**: Export nach X83/X84 Format
- **Brandschutz**: Brandschutz-Dokumentation
- **AVB**: Allgemeine Vertragsbedingungen
- **DXF Analyse**: AutoCAD DXF-Dateien verarbeiten

Architektur
===========

.. code-block:: text

   ┌─────────────────────────────────────────────────────────────┐
   │                        CAD HUB                               │
   ├─────────────────────────────────────────────────────────────┤
   │                                                             │
   │  IFC Upload ──→ Parser ──→ Model ──→ Visualization         │
   │       │           │          │            │                 │
   │       ↓           ↓          ↓            ↓                 │
   │  Validation   Elements   Raumbuch     3D Viewer            │
   │       │           │          │            │                 │
   │       ↓           ↓          ↓            ↓                 │
   │  GAEB Export ←── Analysis ←── Brandschutz ←── Reports      │
   │                                                             │
   └─────────────────────────────────────────────────────────────┘

Models
======

IFC Models
----------

.. code-block:: python

   # models/ifc_models.py
   
   class IFCProject(models.Model):
       """IFC-Projekt Container."""
       id = models.UUIDField(primary_key=True, default=uuid.uuid4)
       name = models.CharField(max_length=200)
       created_at = models.DateTimeField(auto_now_add=True)
       status = models.CharField(choices=STATUS_CHOICES)
   
   class IFCModel(models.Model):
       """Einzelnes IFC-Modell (Version)."""
       project = models.ForeignKey(IFCProject, on_delete=models.CASCADE)
       file = models.FileField(upload_to="ifc/")
       version = models.IntegerField(default=1)
       parsed_data = models.JSONField(null=True)
   
   class IFCElement(models.Model):
       """IFC-Element (Wand, Tür, Fenster, etc.)."""
       model = models.ForeignKey(IFCModel, on_delete=models.CASCADE)
       global_id = models.CharField(max_length=50)
       ifc_type = models.CharField(max_length=100)
       name = models.CharField(max_length=200)
       properties = models.JSONField(default=dict)

AVB Models
----------

.. code-block:: python

   # models_avb.py
   
   class AVBDocument(models.Model):
       """Allgemeine Vertragsbedingungen Dokument."""
       project = models.ForeignKey(IFCProject, on_delete=models.CASCADE)
       version = models.CharField(max_length=20)
       content = models.TextField()
       generated_at = models.DateTimeField(auto_now_add=True)

IFC Parser
==========

Der CAD Hub enthält einen vollständigen IFC-Parser:

.. code-block:: python

   # ifc_complete_parser/
   
   from apps.cad_hub.ifc_complete_parser import IFCParser
   
   parser = IFCParser(ifc_file_path)
   result = parser.parse()
   
   # Zugriff auf Elemente
   walls = result.get_elements_by_type("IfcWall")
   doors = result.get_elements_by_type("IfcDoor")
   windows = result.get_elements_by_type("IfcWindow")
   spaces = result.get_elements_by_type("IfcSpace")

Element-Typen
-------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - IFC-Typ
     - Beschreibung
   * - ``IfcWall``
     - Wände
   * - ``IfcDoor``
     - Türen
   * - ``IfcWindow``
     - Fenster
   * - ``IfcSpace``
     - Räume
   * - ``IfcSlab``
     - Decken/Böden
   * - ``IfcStair``
     - Treppen
   * - ``IfcColumn``
     - Stützen

GAEB Export
===========

Export nach GAEB-Formaten:

.. code-block:: python

   # views.py
   
   class ExportGAEBView(View):
       def get(self, request, model_id):
           model = get_object_or_404(IFCModel, id=model_id)
           format = request.GET.get("format", "xml")  # xml oder excel
           
           if format == "xml":
               return self.export_x84(model)
           else:
               return self.export_excel(model)

Formate
-------

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Format
     - Beschreibung
   * - X83
     - GAEB Angebotsanfrage
   * - X84
     - GAEB Leistungsverzeichnis
   * - Excel
     - Excel-Export für manuelle Bearbeitung

Brandschutz
===========

Brandschutz-Dokumentation:

.. code-block:: python

   # views_brandschutz.py
   
   def brandschutz_dashboard(request, project_id):
       project = get_object_or_404(IFCProject, id=project_id)
       
       # Brandschutz-relevante Elemente
       fire_doors = IFCElement.objects.filter(
           model__project=project,
           ifc_type="IfcDoor",
           properties__FireRating__isnull=False
       )
       
       fire_walls = IFCElement.objects.filter(
           model__project=project,
           ifc_type="IfcWall",
           properties__FireRating__isnull=False
       )
       
       return render(request, "cad_hub/brandschutz/dashboard.html", {
           "project": project,
           "fire_doors": fire_doors,
           "fire_walls": fire_walls,
       })

DXF Analyse
===========

AutoCAD DXF-Dateien verarbeiten:

.. code-block:: python

   # views_dxf.py
   
   def analyze_dxf(request):
       if request.method == "POST":
           dxf_file = request.FILES.get("dxf_file")
           
           from apps.cad_hub.services.dxf_analyzer import DXFAnalyzer
           
           analyzer = DXFAnalyzer(dxf_file)
           result = analyzer.analyze()
           
           return render(request, "cad_hub/dxf/result.html", {
               "layers": result.layers,
               "entities": result.entities,
               "dimensions": result.dimensions,
           })

NL2CAD
======

Natural Language to CAD - Textbeschreibungen in CAD-Elemente:

.. code-block:: python

   # views_nl2cad.py
   
   def nl2cad_generate(request):
       """Generiere CAD-Elemente aus Textbeschreibung."""
       description = request.POST.get("description")
       
       from apps.cad_hub.services.nl2cad import NL2CADGenerator
       
       generator = NL2CADGenerator()
       result = generator.generate(description)
       
       return JsonResponse({
           "elements": result.elements,
           "dxf_content": result.to_dxf(),
       })

URLs
====

.. code-block:: python

   # urls.py
   
   urlpatterns = [
       # Dashboard
       path("", views.dashboard, name="dashboard"),
       
       # Projects
       path("projects/", views.project_list, name="project_list"),
       path("projects/<uuid:pk>/", views.project_detail, name="project_detail"),
       
       # Models (IFC Versions)
       path("models/<uuid:pk>/", views.model_detail, name="model_detail"),
       path("models/<uuid:pk>/upload/", views.model_upload, name="model_upload"),
       
       # Export
       path("models/<uuid:pk>/export/gaeb/", views.ExportGAEBView.as_view()),
       path("models/<uuid:pk>/export/raumbuch/", views.export_raumbuch),
       
       # Brandschutz
       path("brandschutz/", include("apps.cad_hub.urls_brandschutz")),
       
       # DXF
       path("dxf/", views_dxf.dxf_dashboard, name="dxf_dashboard"),
       path("dxf/analyze/", views_dxf.analyze_dxf, name="dxf_analyze"),
       
       # NL2CAD
       path("nl2cad/", views_nl2cad.nl2cad_dashboard, name="nl2cad_dashboard"),
   ]

Handlers
========

.. code-block:: python

   # handlers/
   
   IFCParserHandler        # IFC-Dateien parsen
   RaumbuchGeneratorHandler # Raumbuch erstellen
   GAEBExportHandler       # GAEB-Export
   BrandschutzAnalyzer     # Brandschutz analysieren

Siehe auch
==========

.. toctree::
   :maxdepth: 1

   control_center
   writing_hub
