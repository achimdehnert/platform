"""
Database Router for Governance App
===================================

Routes all governance models to the 'platform' PostgreSQL database.
"""


class GovernanceRouter:
    """Route governance app models to the platform database."""
    
    app_label = "governance"
    db_name = "platform"
    
    def db_for_read(self, model, **hints):
        """Read from platform DB for governance models."""
        if model._meta.app_label == self.app_label:
            return self.db_name
        return None
    
    def db_for_write(self, model, **hints):
        """Write to platform DB for governance models."""
        if model._meta.app_label == self.app_label:
            return self.db_name
        return None
    
    def allow_relation(self, obj1, obj2, **hints):
        """Allow relations within governance app."""
        if (
            obj1._meta.app_label == self.app_label or
            obj2._meta.app_label == self.app_label
        ):
            return True
        return None
    
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Migrate governance models only to platform DB."""
        if app_label == self.app_label:
            return db == self.db_name
        # Don't migrate non-governance apps to platform DB
        if db == self.db_name:
            return False
        return None
