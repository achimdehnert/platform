"""
Initialize Quality System Lookups
=================================

Idempotent - kann mehrfach ausgeführt werden.
Erstellt alle Lookup-Daten für das Quality Scoring System.
"""
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = 'Initialize quality system lookup tables (idempotent)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Zeige detaillierte Ausgabe',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        verbose = options.get('verbose', False)
        
        self.stdout.write('Initializing Quality System Lookups...')
        
        dims = self._init_dimensions(verbose)
        gates = self._init_gate_decisions(verbose)
        statuses = self._init_promise_statuses(verbose)
        
        self.stdout.write(self.style.SUCCESS(
            f'✅ Quality lookups initialized: '
            f'{dims} dimensions, {gates} gate types, {statuses} promise statuses'
        ))

    def _init_dimensions(self, verbose: bool) -> int:
        """Erstellt Quality Dimensions."""
        from apps.writing_hub.models_quality import QualityDimension
        
        dimensions = [
            {
                'code': 'style',
                'name_de': 'Stilqualität',
                'name_en': 'Style Quality',
                'description': 'Konsistenz mit dem definierten Stilprofil',
                'weight': 1.5,
            },
            {
                'code': 'genre',
                'name_de': 'Genre-Erfüllung',
                'name_en': 'Genre Fulfillment',
                'description': 'Erfüllung der Genre-Konventionen und -Erwartungen',
                'weight': 1.0,
            },
            {
                'code': 'scene',
                'name_de': 'Szenenbau',
                'name_en': 'Scene Construction',
                'description': 'Qualität des Szenenaufbaus und der Dramaturgie',
                'weight': 1.0,
            },
            {
                'code': 'serial_logic',
                'name_de': 'Serienlogik',
                'name_en': 'Series Logic',
                'description': 'Konsistenz mit etablierten Fakten und Logik der Serie',
                'weight': 1.5,
            },
            {
                'code': 'pacing',
                'name_de': 'Pacing',
                'name_en': 'Pacing',
                'description': 'Tempo und Rhythmus der Erzählung',
                'weight': 0.8,
            },
            {
                'code': 'dialogue',
                'name_de': 'Dialog-Qualität',
                'name_en': 'Dialogue Quality',
                'description': 'Natürlichkeit und Charakteristik der Dialoge',
                'weight': 1.0,
            },
            {
                'code': 'character_voice',
                'name_de': 'Figurenstimme',
                'name_en': 'Character Voice',
                'description': 'Konsistenz der individuellen Figurenstimmen',
                'weight': 1.2,
            },
            {
                'code': 'atmosphere',
                'name_de': 'Atmosphäre',
                'name_en': 'Atmosphere',
                'description': 'Stimmung und sensorische Details',
                'weight': 0.8,
            },
            {
                'code': 'tension',
                'name_de': 'Spannung',
                'name_en': 'Tension',
                'description': 'Aufbau und Aufrechterhaltung von Spannung',
                'weight': 1.0,
            },
        ]
        
        count = 0
        for i, dim_data in enumerate(dimensions):
            obj, created = QualityDimension.objects.update_or_create(
                code=dim_data['code'],
                defaults={
                    'name_de': dim_data['name_de'],
                    'name_en': dim_data['name_en'],
                    'description': dim_data['description'],
                    'weight': dim_data['weight'],
                    'sort_order': i * 10,
                    'is_active': True,
                }
            )
            if verbose:
                status = 'created' if created else 'updated'
                self.stdout.write(f"  Dimension '{dim_data['code']}': {status}")
            count += 1
        
        return count

    def _init_gate_decisions(self, verbose: bool) -> int:
        """Erstellt Gate Decision Types."""
        from apps.writing_hub.models_quality import GateDecisionType
        
        decisions = [
            {
                'code': 'approve',
                'name_de': 'Freigegeben',
                'name_en': 'Approved',
                'description': 'Kapitel erfüllt alle Qualitätskriterien',
                'color': 'success',
                'icon': 'bi-check-circle-fill',
                'allows_commit': True,
            },
            {
                'code': 'review',
                'name_de': 'Zur Prüfung',
                'name_en': 'Review',
                'description': 'Kapitel benötigt manuelle Prüfung',
                'color': 'warning',
                'icon': 'bi-eye-fill',
                'allows_commit': False,
            },
            {
                'code': 'revise',
                'name_de': 'Überarbeitung',
                'name_en': 'Revise',
                'description': 'Kapitel benötigt Überarbeitung',
                'color': 'danger',
                'icon': 'bi-pencil-fill',
                'allows_commit': False,
            },
            {
                'code': 'reject',
                'name_de': 'Abgelehnt',
                'name_en': 'Rejected',
                'description': 'Kapitel erfüllt Mindestanforderungen nicht',
                'color': 'secondary',
                'icon': 'bi-x-circle-fill',
                'allows_commit': False,
            },
        ]
        
        count = 0
        for i, dec_data in enumerate(decisions):
            obj, created = GateDecisionType.objects.update_or_create(
                code=dec_data['code'],
                defaults={
                    'name_de': dec_data['name_de'],
                    'name_en': dec_data['name_en'],
                    'description': dec_data['description'],
                    'color': dec_data['color'],
                    'icon': dec_data['icon'],
                    'allows_commit': dec_data['allows_commit'],
                    'sort_order': i * 10,
                }
            )
            if verbose:
                status = 'created' if created else 'updated'
                self.stdout.write(f"  Gate Decision '{dec_data['code']}': {status}")
            count += 1
        
        return count

    def _init_promise_statuses(self, verbose: bool) -> int:
        """Erstellt Promise Status Types."""
        from apps.writing_hub.models_quality import PromiseStatus
        
        statuses = [
            {
                'code': 'open',
                'name_de': 'Offen',
                'name_en': 'Open',
                'description': 'Hook wurde eingeführt, noch nicht eingelöst',
                'color': 'primary',
                'is_terminal': False,
            },
            {
                'code': 'reinforced',
                'name_de': 'Verstärkt',
                'name_en': 'Reinforced',
                'description': 'Hook wurde erneut aufgegriffen und verstärkt',
                'color': 'info',
                'is_terminal': False,
            },
            {
                'code': 'twisted',
                'name_de': 'Verdreht',
                'name_en': 'Twisted',
                'description': 'Hook wurde überraschend umgedreht',
                'color': 'warning',
                'is_terminal': False,
            },
            {
                'code': 'paid',
                'name_de': 'Eingelöst',
                'name_en': 'Paid',
                'description': 'Hook wurde vollständig eingelöst (Payoff)',
                'color': 'success',
                'is_terminal': True,
            },
            {
                'code': 'retired',
                'name_de': 'Zurückgezogen',
                'name_en': 'Retired',
                'description': 'Hook wurde bewusst fallen gelassen',
                'color': 'secondary',
                'is_terminal': True,
            },
        ]
        
        count = 0
        for i, stat_data in enumerate(statuses):
            obj, created = PromiseStatus.objects.update_or_create(
                code=stat_data['code'],
                defaults={
                    'name_de': stat_data['name_de'],
                    'name_en': stat_data['name_en'],
                    'description': stat_data['description'],
                    'color': stat_data['color'],
                    'is_terminal': stat_data['is_terminal'],
                    'sort_order': i * 10,
                }
            )
            if verbose:
                status = 'created' if created else 'updated'
                self.stdout.write(f"  Promise Status '{stat_data['code']}': {status}")
            count += 1
        
        return count
