"""
MCP Hub Models - Management für Model Context Protocol Server

Ermöglicht:
- Registrierung und Verwaltung von MCP-Servern
- Tool-Inventar und Konfiguration
- Health-Monitoring und Logs
"""

import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone


class MCPServerType(models.Model):
    """Kategorien von MCP-Servern"""
    
    TYPE_CHOICES = [
        ('builtin', 'Built-in (NPX)'),
        ('custom', 'Custom Python'),
        ('external', 'External Service'),
    ]
    
    name = models.CharField(max_length=50, unique=True)
    code = models.CharField(max_length=20, choices=TYPE_CHOICES, default='custom')
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, default='bi-box')
    
    class Meta:
        db_table = 'mcp_server_types'
        verbose_name = 'MCP Server Type'
    
    def __str__(self):
        return self.name


class MCPServer(models.Model):
    """
    Registrierter MCP-Server.
    Kann sowohl aus mcp_config.json importiert als auch manuell erstellt werden.
    """
    
    STATUS_CHOICES = [
        ('active', 'Aktiv'),
        ('disabled', 'Deaktiviert'),
        ('error', 'Fehler'),
        ('unknown', 'Unbekannt'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    name = models.CharField(max_length=100, unique=True, help_text="Eindeutiger Server-Name (z.B. 'bfagent')")
    display_name = models.CharField(max_length=200, help_text="Anzeigename (z.B. 'BF Agent MCP')")
    
    server_type = models.ForeignKey(
        MCPServerType, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='servers'
    )
    
    description = models.TextField(blank=True)
    
    # Ausführung
    command = models.CharField(max_length=50, default='wsl', help_text="z.B. 'wsl', 'npx', 'python'")
    args = models.JSONField(default=list, help_text="Kommandozeilen-Argumente als Liste")
    env = models.JSONField(default=dict, blank=True, help_text="Umgebungsvariablen")
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unknown')
    is_enabled = models.BooleanField(default=True)
    disabled_tools = models.JSONField(default=list, blank=True, help_text="Liste deaktivierter Tools")
    
    # Pfade
    source_path = models.CharField(max_length=500, blank=True, help_text="Pfad zum Quellcode (mcp-hub)")
    config_path = models.CharField(max_length=500, blank=True, help_text="Pfad zur Config-Datei")
    
    # Repository-Info
    repo_url = models.URLField(blank=True, help_text="GitHub/Git Repository URL")
    version = models.CharField(max_length=50, blank=True)
    
    # Metadaten
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_health_check = models.DateTimeField(null=True, blank=True)
    
    # Aus Config importiert?
    imported_from_config = models.BooleanField(default=False)
    config_key = models.CharField(max_length=100, blank=True, help_text="Key in mcp_config.json")
    
    class Meta:
        db_table = 'mcp_servers'
        ordering = ['name']
        verbose_name = 'MCP Server'
        verbose_name_plural = 'MCP Servers'
    
    def __str__(self):
        return f"{self.display_name} ({self.name})"
    
    @property
    def tool_count(self):
        return self.tools.count()
    
    @property
    def enabled_tool_count(self):
        return self.tools.filter(is_enabled=True).count()


class MCPTool(models.Model):
    """
    Ein Tool das von einem MCP-Server bereitgestellt wird.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    server = models.ForeignKey(MCPServer, on_delete=models.CASCADE, related_name='tools')
    
    name = models.CharField(max_length=200, help_text="Tool-Name (z.B. 'bfagent_resolve_bug')")
    display_name = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    
    # Schema
    input_schema = models.JSONField(default=dict, blank=True, help_text="JSON Schema für Parameter")
    
    # Status
    is_enabled = models.BooleanField(default=True)
    
    # Kategorisierung
    category = models.CharField(max_length=100, blank=True, help_text="z.B. 'search', 'file', 'database'")
    tags = models.JSONField(default=list, blank=True)
    
    # Nutzungsstatistik
    usage_count = models.IntegerField(default=0)
    last_used_at = models.DateTimeField(null=True, blank=True)
    
    # Metadaten
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'mcp_tools'
        unique_together = ['server', 'name']
        ordering = ['server', 'name']
        verbose_name = 'MCP Tool'
        verbose_name_plural = 'MCP Tools'
    
    def __str__(self):
        return f"{self.server.name}:{self.name}"
    
    def record_usage(self):
        """Zeichnet Tool-Nutzung auf"""
        self.usage_count += 1
        self.last_used_at = timezone.now()
        self.save(update_fields=['usage_count', 'last_used_at'])


class MCPServerLog(models.Model):
    """Logs für MCP-Server Aktivitäten"""
    
    LEVEL_CHOICES = [
        ('debug', 'Debug'),
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    server = models.ForeignKey(MCPServer, on_delete=models.CASCADE, related_name='logs')
    
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='info')
    message = models.TextField()
    details = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'mcp_server_logs'
        ordering = ['-created_at']
        verbose_name = 'MCP Server Log'
    
    def __str__(self):
        return f"[{self.level}] {self.server.name}: {self.message[:50]}"


class MCPConfigSync(models.Model):
    """
    Tracks sync status between mcp_config.json and database.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    config_path = models.CharField(max_length=500)
    config_hash = models.CharField(max_length=64, blank=True, help_text="SHA256 hash of config file")
    
    last_sync_at = models.DateTimeField(null=True, blank=True)
    sync_status = models.CharField(max_length=20, default='pending')
    sync_message = models.TextField(blank=True)
    
    servers_added = models.IntegerField(default=0)
    servers_updated = models.IntegerField(default=0)
    servers_removed = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'mcp_config_syncs'
        ordering = ['-created_at']
        verbose_name = 'MCP Config Sync'
    
    def __str__(self):
        return f"Sync {self.last_sync_at or 'pending'}"
