"""
Django ORM Tools for MCP
=========================

Pure Django ORM operations - NO SQL STRINGS!
"""

from django.db.models import Count, Q, Avg, F


class DomainTools:
    """
    Pure Django ORM operations for Domain management.
    NO SQL STRINGS - Only Django Querysets!
    """
    
    def get_active_domains(self):
        """
        Get all active domains with statistics.
        
        Returns:
            QuerySet of active domains with handler/workflow counts
        """
        from apps.bfagent.models_domains import DomainArt
        return list(DomainArt.objects.filter(
            is_active=True
        ).values(
            'id', 'slug', 'name', 'display_name',
            'description', 'icon', 'color',
            'is_experimental', 'created_at', 'updated_at'
        ))
    
    def get_domain_by_slug(self, slug: str):
        """
        Get domain by slug.
        
        Args:
            slug: Domain slug
            
        Returns:
            Domain dict or None
        """
        from apps.bfagent.models_domains import DomainArt
        try:
            return DomainArt.objects.filter(slug=slug).values(
                'id', 'slug', 'name', 'display_name',
                'description', 'icon', 'color',
                'is_active', 'is_experimental'
            ).first()
        except DomainArt.DoesNotExist:
            return None
    
    def get_domain_statistics(self):
        """
        Get domain statistics summary.
        
        Returns:
            Dict with domain counts and stats
        """
        from apps.bfagent.models_domains import DomainArt
        total = DomainArt.objects.count()
        active = DomainArt.objects.filter(is_active=True).count()
        experimental = DomainArt.objects.filter(is_experimental=True).count()
        
        return {
            'total': total,
            'active': active,
            'inactive': total - active,
            'experimental': experimental,
        }
    
    def search_domains(self, query: str):
        """
        Search domains by name or description.
        
        Args:
            query: Search query
            
        Returns:
            List of matching domains
        """
        from apps.bfagent.models_domains import DomainArt
        return list(DomainArt.objects.filter(
            Q(name__icontains=query) |
            Q(display_name__icontains=query) |
            Q(description__icontains=query)
        ).values(
            'id', 'slug', 'name', 'display_name',
            'icon', 'color', 'is_active'
        ))
