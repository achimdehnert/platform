"""
Test Command für Brandschutz-Handler.

Usage:
    python manage.py test_brandschutz
    python manage.py test_brandschutz --dxf path/to/file.dxf
    python manage.py test_brandschutz --pdf path/to/plan.pdf
    python manage.py test_brandschutz --demo
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Testet die Brandschutz-Handler"

    def add_arguments(self, parser):
        parser.add_argument("--dxf", type=str, help="Pfad zu DXF-Datei")
        parser.add_argument("--pdf", type=str, help="Pfad zu PDF-Datei")
        parser.add_argument("--demo", action="store_true", help="Demo mit Testdaten")
        parser.add_argument("--report", action="store_true", help="Generiere HTML-Report")

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("\n🔥 Brandschutz-Handler Test\n" + "=" * 50))

        # 1. Handler-Import testen
        self.stdout.write("\n📦 1. Handler-Import...")
        try:
            from apps.cad_hub.handlers import (
                BrandschutzHandler,
                BrandschutzSymbolHandler,
                BrandschutzReportHandler,
                PDFVisionHandler,
            )
            self.stdout.write(self.style.SUCCESS("   ✅ Alle Handler importiert"))
        except ImportError as e:
            self.stdout.write(self.style.ERROR(f"   ❌ Import-Fehler: {e}"))
            return

        # 2. Model-Import testen
        self.stdout.write("\n📦 2. Model-Import...")
        try:
            from apps.cad_hub.models import (
                BrandschutzPruefung,
                BrandschutzSymbol,
                BrandschutzMangel,
                BrandschutzRegelwerk,
            )
            self.stdout.write(self.style.SUCCESS("   ✅ Alle Models importiert"))
        except ImportError as e:
            self.stdout.write(self.style.ERROR(f"   ❌ Import-Fehler: {e}"))
            return

        # 3. Regelwerk laden
        self.stdout.write("\n📋 3. Regelwerke laden...")
        try:
            regelwerk_path = Path(__file__).parent.parent.parent / "data" / "brandschutz_regelwerke.json"
            if regelwerk_path.exists():
                with open(regelwerk_path, "r", encoding="utf-8") as f:
                    regelwerke = json.load(f)
                count = len(regelwerke.get("regelwerke", []))
                self.stdout.write(self.style.SUCCESS(f"   ✅ {count} Regelwerke geladen"))
                for rw in regelwerke.get("regelwerke", [])[:5]:
                    self.stdout.write(f"      • {rw['kuerzel']}: {rw['name']}")
            else:
                self.stdout.write(self.style.WARNING(f"   ⚠️ Datei nicht gefunden: {regelwerk_path}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   ❌ Fehler: {e}"))

        # 4. Handler instanziieren
        self.stdout.write("\n🔧 4. Handler instanziieren...")
        try:
            bs_handler = BrandschutzHandler()
            sym_handler = BrandschutzSymbolHandler()
            report_handler = BrandschutzReportHandler()
            
            self.stdout.write(f"   • {bs_handler.name}: {len(bs_handler.LAYER_KEYWORDS)} Kategorien")
            self.stdout.write(f"   • {sym_handler.name}: {len(sym_handler.REGELN)} Regeln")
            self.stdout.write(f"   • {report_handler.name}: 4 Export-Formate")
            self.stdout.write(self.style.SUCCESS("   ✅ Handler bereit"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   ❌ Fehler: {e}"))
            return

        # 5. Demo-Test mit Mock-Daten
        if options.get("demo"):
            self.stdout.write("\n🎭 5. Demo-Test mit Mock-Daten...")
            self._run_demo_test(bs_handler, sym_handler, report_handler, options.get("report"))

        # 6. DXF-Test
        if options.get("dxf"):
            self.stdout.write(f"\n📐 6. DXF-Test: {options['dxf']}")
            self._run_dxf_test(options["dxf"], bs_handler, sym_handler)

        # 7. PDF-Test
        if options.get("pdf"):
            self.stdout.write(f"\n📄 7. PDF-Test: {options['pdf']}")
            self._run_pdf_test(options["pdf"])

        self.stdout.write(self.style.SUCCESS("\n" + "=" * 50))
        self.stdout.write(self.style.SUCCESS("✅ Brandschutz-Test abgeschlossen!\n"))

    def _run_demo_test(self, bs_handler, sym_handler, report_handler, generate_report):
        """Führt Demo-Test mit Mock-Daten durch."""
        
        # Mock-Analyse-Ergebnis
        mock_analyse = {
            "brandschutz": {
                "fluchtwege": [
                    {"start": "Büro 101", "ende": "Treppenhaus", "laenge_m": 25.5},
                    {"start": "Büro 102", "ende": "Treppenhaus", "laenge_m": 18.3},
                ],
                "einrichtungen": [
                    {"typ": "feuerloescher", "position": (5000, 3000)},
                    {"typ": "rauchmelder", "position": (2500, 2500)},
                ],
                "ex_bereiche": [],
                "zusammenfassung": {
                    "notausgaenge": 2,
                    "feuerloescher": 3,
                    "rauchmelder": 8,
                    "brandabschnitte": 1,
                },
                "maengel": [
                    "Fluchtweg im Lager > 35m (ASR A2.3)",
                ],
                "warnungen": [
                    "Fluchtweg Büro 101 nahe Grenzwert (25.5m von max 35m)",
                ],
            }
        }
        
        # Mock-Symbol-Ergebnis
        mock_symbole = {
            "symbole": {
                "statistik": {
                    "feuerloescher_fehlen": 2,
                    "rauchmelder_fehlen": 4,
                    "fluchtweg_schilder_fehlen": 3,
                    "gesamt_vorgeschlagen": 9,
                },
                "vorgeschlagene_symbole": [
                    {
                        "symbol_typ": "F001",
                        "position_x": 8000,
                        "position_y": 4000,
                        "begruendung": "ASR A2.2: Feuerlöscher für 180m² Raum",
                        "prioritaet": 1,
                    },
                    {
                        "symbol_typ": "RM",
                        "position_x": 6000,
                        "position_y": 3000,
                        "begruendung": "DIN 14675: Rauchmelder für 65m² Raum",
                        "prioritaet": 2,
                    },
                ],
            }
        }
        
        self.stdout.write("   Mock-Daten erstellt:")
        self.stdout.write(f"   • Fluchtwege: {len(mock_analyse['brandschutz']['fluchtwege'])}")
        self.stdout.write(f"   • Einrichtungen: {len(mock_analyse['brandschutz']['einrichtungen'])}")
        self.stdout.write(f"   • Mängel: {len(mock_analyse['brandschutz']['maengel'])}")
        self.stdout.write(f"   • Vorgeschlagene Symbole: {mock_symbole['symbole']['statistik']['gesamt_vorgeschlagen']}")
        
        if generate_report:
            self.stdout.write("\n   📊 Generiere HTML-Report...")
            try:
                result = report_handler.execute({
                    "analyse_ergebnis": mock_analyse,
                    "symbol_ergebnis": mock_symbole,
                    "format": "html",
                    "konfiguration": {
                        "projekt_name": "Demo Bürogebäude",
                        "etage": "EG",
                        "pruefer": "Test-System",
                    }
                })
                
                if result.success:
                    # Report speichern
                    report_path = Path("brandschutz_report_demo.html")
                    report_path.write_bytes(result.data["bericht"])
                    self.stdout.write(self.style.SUCCESS(f"   ✅ Report gespeichert: {report_path}"))
                    self.stdout.write(f"   📏 Größe: {result.data['groesse_bytes']} bytes")
                else:
                    self.stdout.write(self.style.ERROR(f"   ❌ Report-Fehler: {result.errors}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"   ❌ Fehler: {e}"))

    def _run_dxf_test(self, dxf_path, bs_handler, sym_handler):
        """Testet mit echter DXF-Datei."""
        try:
            import ezdxf
            
            path = Path(dxf_path)
            if not path.exists():
                self.stdout.write(self.style.ERROR(f"   ❌ Datei nicht gefunden: {path}"))
                return
            
            self.stdout.write(f"   Lade DXF: {path.name}")
            doc = ezdxf.readfile(str(path))
            
            # Brandschutz-Analyse
            self.stdout.write("   Führe Brandschutz-Analyse durch...")
            result = bs_handler.execute({
                "loader": doc,
                "format": "dxf",
            })
            
            if result.success:
                bs = result.data.get("brandschutz", {})
                zf = bs.get("zusammenfassung", {})
                self.stdout.write(self.style.SUCCESS("   ✅ Analyse erfolgreich"))
                self.stdout.write(f"   • Fluchtwege: {len(bs.get('fluchtwege', []))}")
                self.stdout.write(f"   • Einrichtungen: {len(bs.get('einrichtungen', []))}")
                self.stdout.write(f"   • Feuerlöscher: {zf.get('feuerloescher', 0)}")
                self.stdout.write(f"   • Rauchmelder: {zf.get('rauchmelder', 0)}")
                self.stdout.write(f"   • Mängel: {len(bs.get('maengel', []))}")
                
                for mangel in bs.get("maengel", []):
                    self.stdout.write(self.style.WARNING(f"      ⚠️ {mangel}"))
            else:
                self.stdout.write(self.style.ERROR(f"   ❌ Fehler: {result.errors}"))
                
        except ImportError:
            self.stdout.write(self.style.ERROR("   ❌ ezdxf nicht installiert: pip install ezdxf"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   ❌ Fehler: {e}"))

    def _run_pdf_test(self, pdf_path):
        """Testet PDF-Vision-Handler."""
        try:
            from apps.cad_hub.handlers import PDFVisionHandler
            
            path = Path(pdf_path)
            if not path.exists():
                self.stdout.write(self.style.ERROR(f"   ❌ Datei nicht gefunden: {path}"))
                return
            
            self.stdout.write(f"   Lade PDF: {path.name}")
            handler = PDFVisionHandler()
            
            result = handler.execute({
                "pdf_path": str(path),
                "analyse_typ": "brandschutz",
                "llm_provider": "openai",
            })
            
            if result.success:
                va = result.data.get("vision_analyse", {})
                self.stdout.write(self.style.SUCCESS("   ✅ Vision-Analyse erfolgreich"))
                self.stdout.write(f"   • Erkannte Symbole: {len(va.get('erkannte_symbole', []))}")
                self.stdout.write(f"   • Erkannte Fluchtwege: {len(va.get('erkannte_fluchtwege', []))}")
                if va.get("zusammenfassung"):
                    self.stdout.write(f"   • Zusammenfassung: {va['zusammenfassung'][:200]}...")
            else:
                self.stdout.write(self.style.WARNING(f"   ⚠️ {result.errors}"))
                self.stdout.write("   (Vision-Analyse benötigt OPENAI_API_KEY)")
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   ❌ Fehler: {e}"))
