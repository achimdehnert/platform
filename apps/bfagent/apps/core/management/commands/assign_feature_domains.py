"""
Management command to automatically assign domains to ComponentRegistry features
"""

from django.core.management.base import BaseCommand
from django.db import models
from apps.bfagent.models_registry import ComponentRegistry
from apps.core.features import get_domain_registry


class Command(BaseCommand):
    help = 'Automatically assign domains to features based on name, tags, and file path'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be assigned without actually updating'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Overwrite existing domain assignments'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']
        
        domain_registry = get_domain_registry()
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes will be made\n'))
        
        # Get all features without domain assignment (or all if force)
        if force:
            features = ComponentRegistry.objects.all()
            self.stdout.write(f"Processing ALL {features.count()} features (--force mode)\n")
        else:
            features = ComponentRegistry.objects.filter(
                models.Q(domain='') | models.Q(domain__isnull=True)
            )
            self.stdout.write(f"Processing {features.count()} features without domain\n")
        
        assigned = 0
        skipped = 0
        uncertain = []
        
        for feature in features:
            domain_id = self._detect_domain(feature, domain_registry)
            
            if domain_id:
                if dry_run:
                    self.stdout.write(
                        f"Would assign '{domain_id}' → {feature.name} ({feature.component_type})"
                    )
                else:
                    old_domain = feature.domain
                    feature.domain = domain_id
                    feature.save(update_fields=['domain'])
                    
                    if old_domain:
                        self.stdout.write(
                            self.style.WARNING(
                                f"↻ Changed: {feature.name} | {old_domain} → {domain_id}"
                            )
                        )
                    else:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"✓ Assigned: {feature.name} → {domain_id}"
                            )
                        )
                
                assigned += 1
            else:
                # Could not determine domain
                uncertain.append({
                    'id': feature.pk,
                    'name': feature.name,
                    'type': feature.component_type,
                    'file_path': feature.file_path,
                    'tags': feature.tags
                })
                skipped += 1
        
        # Summary
        self.stdout.write("\n" + "=" * 60)
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN COMPLETED"))
        else:
            self.stdout.write(self.style.SUCCESS("ASSIGNMENT COMPLETED"))
        
        self.stdout.write(f"Total features processed: {features.count()}")
        self.stdout.write(f"Assigned: {assigned}")
        self.stdout.write(f"Skipped (uncertain): {skipped}")
        
        # Show uncertain features
        if uncertain:
            self.stdout.write("\n" + "=" * 60)
            self.stdout.write(self.style.WARNING(
                f"UNCERTAIN FEATURES ({len(uncertain)}) - Manual assignment needed:"
            ))
            self.stdout.write("=" * 60)
            
            for feat in uncertain:
                self.stdout.write(f"\nID: {feat['id']}")
                self.stdout.write(f"  Name: {feat['name']}")
                self.stdout.write(f"  Type: {feat['type']}")
                self.stdout.write(f"  File: {feat['file_path']}")
                if feat['tags']:
                    self.stdout.write(f"  Tags: {', '.join(feat['tags'])}")
                self.stdout.write(f"  → Assign manually in admin or with:")
                self.stdout.write(
                    f"     python manage.py shell -c \"from apps.bfagent.models_registry "
                    f"import ComponentRegistry; f=ComponentRegistry.objects.get(pk={feat['id']}); "
                    f"f.domain='DOMAIN_ID'; f.save()\""
                )

    def _detect_domain(self, feature, domain_registry):
        """
        Detect domain based on feature name, file_path, tags, and module_path
        Returns domain_id or None if uncertain
        """
        name_lower = feature.name.lower()
        file_path_lower = feature.file_path.lower()
        module_path_lower = feature.module_path.lower()
        tags_lower = [tag.lower() for tag in feature.tags]
        
        # Score each domain
        scores = {}
        
        for domain_id, domain_info in domain_registry.domains.items():
            score = 0
            domain_name_lower = domain_info.name.lower()
            
            # File path contains domain path
            if domain_id in file_path_lower or domain_id.replace('_', '') in file_path_lower:
                score += 100
            
            # Module path contains domain
            if domain_id in module_path_lower:
                score += 100
            
            # Name contains domain keywords
            domain_keywords = self._get_domain_keywords(domain_id)
            for keyword in domain_keywords:
                if keyword in name_lower:
                    score += 50
                if keyword in ' '.join(tags_lower):
                    score += 30
            
            # Special patterns
            if domain_id == 'presentation_studio':
                if any(k in name_lower for k in ['pptx', 'slide', 'presentation', 'powerpoint']):
                    score += 80
            
            elif domain_id == 'genagent':
                if any(k in name_lower for k in ['ai', 'llm', 'agent', 'generation', 'prompt']):
                    score += 80
            
            elif domain_id == 'medtrans':
                if any(k in name_lower for k in ['medical', 'translation', 'terminology']):
                    score += 80
            
            elif domain_id == 'hub':
                if any(k in name_lower for k in ['integration', 'api', 'webhook', 'connector']):
                    score += 80
            
            elif domain_id == 'control_center':
                if any(k in name_lower for k in ['admin', 'dashboard', 'control', 'monitoring', 'metrics']):
                    score += 80
            
            elif domain_id == 'core':
                if any(k in name_lower for k in ['base', 'core', 'shared', 'common', 'utility']):
                    score += 60
            
            elif domain_id == 'bfagent':
                # BFAgent is catch-all for main app features
                if any(k in name_lower for k in ['book', 'character', 'dialogue', 'chapter']):
                    score += 70
            
            if score > 0:
                scores[domain_id] = score
        
        # Return domain with highest score if confident
        if scores:
            best_domain = max(scores, key=scores.get)
            best_score = scores[best_domain]
            
            # Only assign if score is high enough (confidence threshold)
            if best_score >= 50:
                return best_domain
        
        return None
    
    def _get_domain_keywords(self, domain_id):
        """Get keywords for domain detection"""
        keywords_map = {
            'presentation_studio': ['presentation', 'pptx', 'slide', 'powerpoint'],
            'genagent': ['genagent', 'generation', 'ai', 'agent', 'llm'],
            'medtrans': ['medtrans', 'medical', 'translation'],
            'hub': ['hub', 'integration', 'connector'],
            'control_center': ['control', 'admin', 'dashboard', 'monitoring'],
            'core': ['core', 'base', 'shared', 'common'],
            'bfagent': ['book', 'character', 'dialogue', 'chapter', 'story'],
        }
        
        return keywords_map.get(domain_id, [domain_id])
