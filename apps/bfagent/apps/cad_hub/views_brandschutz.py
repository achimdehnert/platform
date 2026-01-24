# apps/cad_hub/views_brandschutz.py
"""
Views für Brandschutz-Frontend.
"""
import json
from pathlib import Path
from datetime import datetime

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse, FileResponse
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.db.models import Count, Q
from django.core.paginator import Paginator

from .models import (
    BrandschutzPruefung,
    BrandschutzMangel,
    BrandschutzSymbolVorschlag,
    BrandschutzRegelwerk,
    PruefStatus,
    BrandschutzKategorie,
)
from .handlers import BrandschutzHandler, BrandschutzSymbolHandler, BrandschutzReportHandler


class BrandschutzDashboardView(LoginRequiredMixin, View):
    """Brandschutz Dashboard - Übersicht aller Prüfungen."""
    
    template_name = "cad_hub/brandschutz/dashboard.html"
    
    def get(self, request):
        # Statistiken
        pruefungen = BrandschutzPruefung.objects.all()
        stats = {
            "gesamt": pruefungen.count(),
            "entwurf": pruefungen.filter(status=PruefStatus.ENTWURF).count(),
            "in_pruefung": pruefungen.filter(status=PruefStatus.IN_PRUEFUNG).count(),
            "abgeschlossen": pruefungen.filter(status=PruefStatus.ABGESCHLOSSEN).count(),
            "maengel": pruefungen.filter(status=PruefStatus.MAENGEL).count(),
            "freigegeben": pruefungen.filter(status=PruefStatus.FREIGEGEBEN).count(),
        }
        
        # Offene Mängel
        offene_maengel = BrandschutzMangel.objects.filter(behoben=False).select_related("pruefung")
        mangel_stats = {
            "gesamt": offene_maengel.count(),
            "kritisch": offene_maengel.filter(schweregrad="kritisch").count(),
            "hoch": offene_maengel.filter(schweregrad="hoch").count(),
            "mittel": offene_maengel.filter(schweregrad="mittel").count(),
            "gering": offene_maengel.filter(schweregrad="gering").count(),
        }
        
        # Letzte Prüfungen
        letzte_pruefungen = pruefungen.order_by("-pruef_datum")[:5]
        
        # Dringende Mängel
        dringende_maengel = offene_maengel.filter(
            schweregrad__in=["kritisch", "hoch"]
        ).order_by("-erstellt_am")[:10]
        
        context = {
            "stats": stats,
            "mangel_stats": mangel_stats,
            "letzte_pruefungen": letzte_pruefungen,
            "dringende_maengel": dringende_maengel,
            "page_title": "Brandschutz Dashboard",
        }
        return render(request, self.template_name, context)


class BrandschutzPruefungListView(LoginRequiredMixin, ListView):
    """Liste aller Brandschutz-Prüfungen."""
    
    model = BrandschutzPruefung
    template_name = "cad_hub/brandschutz/pruefung_list.html"
    context_object_name = "pruefungen"
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset().annotate(
            mangel_count=Count("maengel"),
            offene_maengel=Count("maengel", filter=Q(maengel__behoben=False)),
        ).order_by("-pruef_datum")
        
        # Filter
        status = self.request.GET.get("status")
        if status:
            queryset = queryset.filter(status=status)
        
        search = self.request.GET.get("q")
        if search:
            queryset = queryset.filter(
                Q(titel__icontains=search) |
                Q(projekt_name__icontains=search) |
                Q(pruefer__icontains=search)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status_choices"] = PruefStatus.choices
        context["current_status"] = self.request.GET.get("status", "")
        context["search_query"] = self.request.GET.get("q", "")
        context["page_title"] = "Brandschutz-Prüfungen"
        return context


class BrandschutzPruefungDetailView(LoginRequiredMixin, DetailView):
    """Detail-Ansicht einer Prüfung."""
    
    model = BrandschutzPruefung
    template_name = "cad_hub/brandschutz/pruefung_detail.html"
    context_object_name = "pruefung"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pruefung = self.object
        
        # Mängel gruppiert nach Kategorie
        maengel = pruefung.maengel.all().order_by("schweregrad", "-erstellt_am")
        maengel_by_kategorie = {}
        for mangel in maengel:
            kat = mangel.kategorie
            if kat not in maengel_by_kategorie:
                maengel_by_kategorie[kat] = []
            maengel_by_kategorie[kat].append(mangel)
        
        # Symbole gruppiert nach Typ
        symbole = pruefung.symbole.all().order_by("prioritaet")
        symbole_by_typ = {}
        for symbol in symbole:
            typ = symbol.symbol_typ
            if typ not in symbole_by_typ:
                symbole_by_typ[typ] = []
            symbole_by_typ[typ].append(symbol)
        
        context["maengel"] = maengel
        context["maengel_by_kategorie"] = maengel_by_kategorie
        context["symbole"] = symbole
        context["symbole_by_typ"] = symbole_by_typ
        context["page_title"] = f"Prüfung: {pruefung.titel}"
        return context


class BrandschutzPruefungCreateView(LoginRequiredMixin, CreateView):
    """Neue Prüfung erstellen."""
    
    model = BrandschutzPruefung
    template_name = "cad_hub/brandschutz/pruefung_form.html"
    fields = [
        "titel", "projekt_name", "gebaeude_typ", "etage",
        "flaeche_qm", "beschreibung", "pruefer", "quelldatei"
    ]
    success_url = reverse_lazy("brandschutz:pruefung_list")
    
    def form_valid(self, form):
        form.instance.status = PruefStatus.ENTWURF
        messages.success(self.request, "Prüfung erfolgreich erstellt.")
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Neue Brandschutz-Prüfung"
        context["form_action"] = "Erstellen"
        return context


class BrandschutzPruefungUpdateView(LoginRequiredMixin, UpdateView):
    """Prüfung bearbeiten."""
    
    model = BrandschutzPruefung
    template_name = "cad_hub/brandschutz/pruefung_form.html"
    fields = [
        "titel", "projekt_name", "status", "gebaeude_typ", "etage",
        "flaeche_qm", "beschreibung", "pruefer", "naechste_pruefung"
    ]
    
    def get_success_url(self):
        return reverse("brandschutz:pruefung_detail", kwargs={"pk": self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, "Prüfung erfolgreich aktualisiert.")
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = f"Bearbeiten: {self.object.titel}"
        context["form_action"] = "Speichern"
        return context


class BrandschutzAnalyseView(LoginRequiredMixin, View):
    """Analyse einer CAD-Datei durchführen."""
    
    template_name = "cad_hub/brandschutz/analyse.html"
    
    def get(self, request, pk=None):
        pruefung = None
        if pk:
            pruefung = get_object_or_404(BrandschutzPruefung, pk=pk)
        
        context = {
            "pruefung": pruefung,
            "page_title": "Brandschutz-Analyse",
        }
        return render(request, self.template_name, context)
    
    def post(self, request, pk=None):
        """HTMX: Analyse durchführen."""
        pruefung = get_object_or_404(BrandschutzPruefung, pk=pk) if pk else None
        
        # Datei aus Request oder Prüfung
        uploaded_file = request.FILES.get("datei")
        if not uploaded_file and pruefung and pruefung.quelldatei:
            file_path = pruefung.quelldatei.path
        elif uploaded_file:
            # Temporär speichern
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix=uploaded_file.name) as tmp:
                for chunk in uploaded_file.chunks():
                    tmp.write(chunk)
                file_path = tmp.name
        else:
            return JsonResponse({"error": "Keine Datei angegeben"}, status=400)
        
        try:
            # Handler initialisieren
            bs_handler = BrandschutzHandler()
            sym_handler = BrandschutzSymbolHandler()
            
            # Format erkennen
            suffix = Path(file_path).suffix.lower()
            if suffix == ".dxf":
                import ezdxf
                doc = ezdxf.readfile(file_path)
                analyse_input = {"loader": doc, "format": "dxf"}
            elif suffix == ".ifc":
                import ifcopenshell
                model = ifcopenshell.open(file_path)
                analyse_input = {"loader": model, "format": "ifc"}
            else:
                return JsonResponse({"error": f"Unbekanntes Format: {suffix}"}, status=400)
            
            # Analyse durchführen
            result = bs_handler.execute(analyse_input)
            
            if result.success:
                # Symbol-Vorschläge generieren
                sym_result = sym_handler.execute({
                    "analyse_ergebnis": result.data,
                    "format": suffix.strip("."),
                })
                
                # Prüfung aktualisieren
                if pruefung:
                    pruefung.analyse_ergebnis = result.data
                    pruefung.status = PruefStatus.IN_PRUEFUNG
                    pruefung.save()
                    
                    # Mängel erstellen
                    for mangel_text in result.data.get("brandschutz", {}).get("maengel", []):
                        BrandschutzMangel.objects.create(
                            pruefung=pruefung,
                            kategorie=BrandschutzKategorie.FLUCHTWEG,
                            schweregrad="hoch",
                            beschreibung=mangel_text,
                        )
                    
                    # Symbole erstellen
                    if sym_result.success:
                        for sym in sym_result.data.get("symbole", {}).get("vorgeschlagene_symbole", []):
                            BrandschutzSymbolVorschlag.objects.create(
                                pruefung=pruefung,
                                symbol_typ=sym.get("symbol_typ", "UNBEKANNT"),
                                position_x=sym.get("position_x", 0),
                                position_y=sym.get("position_y", 0),
                                begruendung=sym.get("begruendung", ""),
                                prioritaet=sym.get("prioritaet", 3),
                                status="vorgeschlagen",
                            )
                
                return JsonResponse({
                    "success": True,
                    "analyse": result.data,
                    "symbole": sym_result.data if sym_result.success else {},
                    "redirect": reverse("brandschutz:pruefung_detail", kwargs={"pk": pruefung.pk}) if pruefung else None,
                })
            else:
                return JsonResponse({"error": str(result.errors)}, status=400)
                
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


class BrandschutzReportView(LoginRequiredMixin, View):
    """Report generieren."""
    
    def get(self, request, pk, format="html"):
        pruefung = get_object_or_404(BrandschutzPruefung, pk=pk)
        
        # Report-Handler
        handler = BrandschutzReportHandler()
        
        # Daten sammeln
        maengel = list(pruefung.maengel.values(
            "kategorie", "schweregrad", "beschreibung", "regelwerk_referenz", "behoben"
        ))
        symbole = list(pruefung.symbole.values(
            "symbol_typ", "position_x", "position_y", "status", "begruendung"
        ))
        
        result = handler.execute({
            "analyse_ergebnis": pruefung.analyse_ergebnis or {},
            "symbol_ergebnis": {"symbole": {"vorgeschlagene_symbole": symbole}},
            "format": format,
            "konfiguration": {
                "projekt_name": pruefung.projekt_name,
                "etage": pruefung.etage or "-",
                "pruefer": pruefung.pruefer or "-",
                "pruef_datum": pruefung.pruef_datum.isoformat() if pruefung.pruef_datum else "-",
                "maengel_liste": maengel,
            }
        })
        
        if not result.success:
            messages.error(request, f"Report-Fehler: {result.errors}")
            return redirect("brandschutz:pruefung_detail", pk=pk)
        
        # Response je nach Format
        if format == "html":
            return HttpResponse(
                result.data["bericht"],
                content_type="text/html"
            )
        elif format == "pdf":
            response = HttpResponse(
                result.data["bericht"],
                content_type="application/pdf"
            )
            response["Content-Disposition"] = f'attachment; filename="brandschutz_report_{pk}.pdf"'
            return response
        elif format == "excel":
            response = HttpResponse(
                result.data["bericht"],
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            response["Content-Disposition"] = f'attachment; filename="brandschutz_report_{pk}.xlsx"'
            return response
        elif format == "json":
            return JsonResponse(json.loads(result.data["bericht"].decode()))
        
        return HttpResponse(result.data["bericht"])


class BrandschutzMangelToggleView(LoginRequiredMixin, View):
    """HTMX: Mangel als behoben markieren."""
    
    def post(self, request, pk):
        mangel = get_object_or_404(BrandschutzMangel, pk=pk)
        mangel.behoben = not mangel.behoben
        if mangel.behoben:
            mangel.behoben_am = datetime.now()
        else:
            mangel.behoben_am = None
        mangel.save()
        
        # HTMX partial response
        return render(request, "cad_hub/brandschutz/partials/mangel_row.html", {
            "mangel": mangel
        })


class BrandschutzSymbolApproveView(LoginRequiredMixin, View):
    """HTMX: Symbol genehmigen/ablehnen."""
    
    def post(self, request, pk):
        symbol = get_object_or_404(BrandschutzSymbol, pk=pk)
        action = request.POST.get("action", "genehmigt")
        
        if action in ["genehmigt", "abgelehnt", "eingefuegt"]:
            symbol.status = action
            symbol.save()
        
        return render(request, "cad_hub/brandschutz/partials/symbol_row.html", {
            "symbol": symbol
        })


class BrandschutzRegelwerkListView(LoginRequiredMixin, ListView):
    """Liste aller Regelwerke."""
    
    model = BrandschutzRegelwerk
    template_name = "cad_hub/brandschutz/regelwerk_list.html"
    context_object_name = "regelwerke"
    
    def get_queryset(self):
        return super().get_queryset().filter(aktiv=True).order_by("kuerzel")
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Brandschutz-Regelwerke"
        return context


# API Endpoints für HTMX

class BrandschutzStatsAPIView(LoginRequiredMixin, View):
    """API: Dashboard-Statistiken."""
    
    def get(self, request):
        pruefungen = BrandschutzPruefung.objects.all()
        maengel = BrandschutzMangel.objects.filter(behoben=False)
        
        return JsonResponse({
            "pruefungen": {
                "gesamt": pruefungen.count(),
                "offen": pruefungen.exclude(status=PruefStatus.FREIGEGEBEN).count(),
            },
            "maengel": {
                "offen": maengel.count(),
                "kritisch": maengel.filter(schweregrad="kritisch").count(),
            }
        })


class BrandschutzSearchAPIView(LoginRequiredMixin, View):
    """API: Suche in Prüfungen."""
    
    def get(self, request):
        query = request.GET.get("q", "")
        
        if len(query) < 2:
            return JsonResponse({"results": []})
        
        pruefungen = BrandschutzPruefung.objects.filter(
            Q(titel__icontains=query) |
            Q(projekt_name__icontains=query)
        )[:10]
        
        results = [
            {
                "id": str(p.pk),
                "titel": p.titel,
                "projekt": p.projekt_name,
                "status": p.get_status_display(),
                "url": reverse("brandschutz:pruefung_detail", kwargs={"pk": p.pk}),
            }
            for p in pruefungen
        ]
        
        return JsonResponse({"results": results})
