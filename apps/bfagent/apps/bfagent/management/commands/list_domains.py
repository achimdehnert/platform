"""Management command to list all domains"""
from django.core.management.base import BaseCommand
from apps.bfagent.models_domains import DomainArt


class Command(BaseCommand):
    help = 'Liste alle Domains im System'

    def handle(self, *args, **options):
        domains = DomainArt.objects.all().order_by('id')
        
        self.stdout.write("\n" + "="*90)
        self.stdout.write("ALLE DOMAINS IM SYSTEM")
        self.stdout.write("="*90 + "\n")
        
        for d in domains:
            status = self.style.SUCCESS("AKTIV") if d.is_active else self.style.ERROR("INAKTIV")
            exp = self.style.WARNING(" [EXPERIMENTAL]") if d.is_experimental else ""
            
            self.stdout.write(self.style.HTTP_INFO(f"\n{d.display_name}"))
            self.stdout.write(f"  ID:        {d.id}")
            self.stdout.write(f"  Slug:      {d.slug}")
            self.stdout.write(f"  Status:    {status}{exp}")
            self.stdout.write(f"  Icon:      {d.icon if d.icon else '-'}")
            self.stdout.write(f"  Color:     {d.color if d.color else '-'}")
            if d.description:
                desc = d.description[:80] + "..." if len(d.description) > 80 else d.description
                self.stdout.write(f"  Info:      {desc}")
        
        self.stdout.write("\n" + "="*90)
        active_count = domains.filter(is_active=True).count()
        inactive_count = domains.filter(is_active=False).count()
        
        self.stdout.write(
            f"Gesamt: {domains.count()} Domains "
            f"({active_count} aktiv, {inactive_count} inaktiv)"
        )
        self.stdout.write("="*90 + "\n")
