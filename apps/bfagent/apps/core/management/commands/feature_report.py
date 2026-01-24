"""
Management command to generate feature reports across all domains
"""

from django.core.management.base import BaseCommand
from apps.core.features import get_global_feature_registry, get_domain_registry
import json


class Command(BaseCommand):
    help = 'Generate feature reports for domains'

    def add_arguments(self, parser):
        parser.add_argument(
            '--domain',
            type=str,
            help='Specific domain to report (leave empty for all domains)'
        )
        parser.add_argument(
            '--format',
            type=str,
            default='text',
            choices=['text', 'json'],
            help='Output format'
        )
        parser.add_argument(
            '--show-cross-domain',
            action='store_true',
            help='Show cross-domain features'
        )
        parser.add_argument(
            '--show-handlers',
            action='store_true',
            help='Show handler details'
        )

    def handle(self, *args, **options):
        domain_id = options.get('domain')
        output_format = options['format']
        show_cross_domain = options['show_cross_domain']
        show_handlers = options['show_handlers']
        
        feature_registry = get_global_feature_registry()
        domain_registry = get_domain_registry()
        
        if domain_id:
            # Single domain report
            self._show_domain_report(domain_id, feature_registry, output_format)
        else:
            # Global report
            self._show_global_report(feature_registry, domain_registry, output_format)
        
        if show_cross_domain:
            self._show_cross_domain_features(feature_registry, output_format)
        
        if show_handlers:
            self._show_handler_details(feature_registry, output_format)

    def _show_global_report(self, feature_registry, domain_registry, output_format):
        """Show global report across all domains"""
        report = feature_registry.generate_global_report()
        
        if output_format == 'json':
            self.stdout.write(json.dumps(report, indent=2))
        else:
            self.stdout.write(self.style.SUCCESS('\n=== GLOBAL FEATURE REPORT ===\n'))
            self.stdout.write(f"Total Features: {report['total_features']}")
            self.stdout.write(f"Active Features: {report['active_features']}")
            self.stdout.write(f"Planned Features: {report['planned_features']}")
            self.stdout.write(f"Cross-Domain Features: {report['cross_domain_features']}")
            self.stdout.write(f"\nTotal Handlers: {report['total_handlers']}")
            self.stdout.write(f"Shared Handlers: {report['shared_handlers']}")
            self.stdout.write(f"BaseHandler v2.0: {report['base_handler_v2_count']}")
            self.stdout.write(f"Legacy Handlers: {report['legacy_handler_count']}")
            self.stdout.write(f"Migration Progress: {report['migration_progress']}")
            self.stdout.write(f"Reusability Score: {report['reusability_score']:.2%}")
            
            self.stdout.write(self.style.SUCCESS('\n=== PER-DOMAIN BREAKDOWN ==='))
            for domain_id, domain_data in report['domain_reports'].items():
                domain = domain_registry.get_domain(domain_id)
                self.stdout.write(f"\n{domain.name} ({domain_id}):")
                self.stdout.write(f"  Features: {domain_data['total_features']} ({domain_data['active_features']} active)")
                self.stdout.write(f"  Cross-Domain: {domain_data['cross_domain_features']}")
                self.stdout.write(f"  Handlers: {domain_data['base_handler_v2_count']} v2.0, {domain_data['legacy_handler_count']} legacy")

    def _show_domain_report(self, domain_id, feature_registry, output_format):
        """Show report for specific domain"""
        report = feature_registry.get_domain_report(domain_id)
        
        if not report:
            self.stdout.write(self.style.ERROR(f"Domain '{domain_id}' not found"))
            return
        
        if output_format == 'json':
            self.stdout.write(json.dumps({
                'domain_id': report.domain_id,
                'domain_name': report.domain_name,
                'total_features': report.total_features,
                'active_features': report.active_features,
                'planned_features': report.planned_features,
                'total_handlers': report.total_handlers,
                'base_handler_v2_count': report.base_handler_v2_count,
                'legacy_handler_count': report.legacy_handler_count,
                'cross_domain_features': report.cross_domain_features,
                'categories': report.categories,
                'priority_breakdown': report.priority_breakdown
            }, indent=2))
        else:
            self.stdout.write(self.style.SUCCESS(f'\n=== {report.domain_name} Feature Report ===\n'))
            self.stdout.write(f"Total Features: {report.total_features}")
            self.stdout.write(f"  Active: {report.active_features}")
            self.stdout.write(f"  Planned: {report.planned_features}")
            self.stdout.write(f"  Deprecated: {report.deprecated_features}")
            self.stdout.write(f"\nHandlers: {report.total_handlers}")
            self.stdout.write(f"  BaseHandler v2.0: {report.base_handler_v2_count}")
            self.stdout.write(f"  Legacy: {report.legacy_handler_count}")
            self.stdout.write(f"\nCross-Domain Features: {report.cross_domain_features}")
            
            if report.categories:
                self.stdout.write(f"\nCategories:")
                for category, count in sorted(report.categories.items()):
                    self.stdout.write(f"  {category}: {count}")
            
            if report.priority_breakdown:
                self.stdout.write(f"\nPriority Breakdown:")
                for priority, count in sorted(report.priority_breakdown.items()):
                    self.stdout.write(f"  {priority}: {count}")

    def _show_cross_domain_features(self, feature_registry, output_format):
        """Show cross-domain features"""
        cross_domain = feature_registry.get_cross_domain_features()
        
        if output_format == 'json':
            self.stdout.write(json.dumps([
                {
                    'id': f.id,
                    'name': f.name,
                    'primary_domain': f.primary_domain,
                    'supported_domains': list(f.supported_domains)
                }
                for f in cross_domain
            ], indent=2))
        else:
            self.stdout.write(self.style.SUCCESS(f'\n=== CROSS-DOMAIN FEATURES ({len(cross_domain)}) ===\n'))
            for feature in cross_domain:
                domains_str = ', '.join(sorted(feature.supported_domains))
                self.stdout.write(f"{feature.name} ({feature.id})")
                self.stdout.write(f"  Primary: {feature.primary_domain}")
                self.stdout.write(f"  Domains: {domains_str}")
                self.stdout.write("")

    def _show_handler_details(self, feature_registry, output_format):
        """Show handler details"""
        shared_handlers = feature_registry.get_shared_handlers()
        
        if output_format == 'json':
            self.stdout.write(json.dumps([
                {
                    'name': h.name,
                    'class_name': h.class_name,
                    'domains': list(h.domains),
                    'is_base_handler_v2': h.is_base_handler_v2
                }
                for h in shared_handlers
            ], indent=2))
        else:
            self.stdout.write(self.style.SUCCESS(f'\n=== SHARED HANDLERS ({len(shared_handlers)}) ===\n'))
            for handler in shared_handlers:
                domains_str = ', '.join(sorted(handler.domains))
                v2_badge = " [v2.0]" if handler.is_base_handler_v2 else " [legacy]"
                self.stdout.write(f"{handler.name}{v2_badge}")
                self.stdout.write(f"  Class: {handler.class_name}")
                self.stdout.write(f"  Domains: {domains_str}")
                self.stdout.write("")
