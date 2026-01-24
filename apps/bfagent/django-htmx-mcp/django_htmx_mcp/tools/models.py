"""
Model Generation Tools.

Tools zum Generieren von Django Models.
"""

from typing import Literal

from django_htmx_mcp.server import mcp, logger
from django_htmx_mcp.templating import snake_case, pluralize, model_to_verbose


@mcp.tool()
def generate_django_model(
    model_name: str,
    fields: list[dict],
    app_name: str = "app",
    with_timestamps: bool = True,
    with_uuid_pk: bool = False,
    with_soft_delete: bool = False,
    ordering: list[str] | None = None,
    verbose_name: str | None = None,
    docstring: str | None = None,
) -> str:
    """
    Generiert ein Django Model.
    
    Args:
        model_name: Name des Models (PascalCase, z.B. "BlogPost")
        fields: Liste von Field-Definitionen als Dicts:
            - name: Feldname (snake_case)
            - type: Django Field Type (CharField, ForeignKey, etc.)
            - max_length: Für CharField (optional)
            - blank: Erlaubt leeren Wert (default: False)
            - null: Erlaubt NULL in DB (default: False)
            - default: Default-Wert (optional)
            - unique: Unique Constraint (default: False)
            - choices: Liste von (value, label) Tupeln (optional)
            - to: Related Model für FK/M2M/O2O
            - on_delete: CASCADE, PROTECT, SET_NULL, etc.
            - related_name: Related name für Reverse-Lookup
            - help_text: Hilfetext (optional)
        app_name: Name der Django App
        with_timestamps: created_at/updated_at hinzufügen
        with_uuid_pk: UUID als Primary Key verwenden
        with_soft_delete: Soft Delete Pattern (is_deleted, deleted_at)
        ordering: Default ordering (z.B. ["-created_at"])
        verbose_name: Human-readable Name
        docstring: Model Docstring
        
    Returns:
        Python Code für das Model
        
    Example:
        generate_django_model(
            model_name="Task",
            fields=[
                {"name": "title", "type": "CharField", "max_length": 200},
                {"name": "description", "type": "TextField", "blank": True},
                {"name": "status", "type": "CharField", "max_length": 20, 
                 "choices": [("todo", "To Do"), ("done", "Done")]},
                {"name": "assignee", "type": "ForeignKey", "to": "User", 
                 "on_delete": "CASCADE", "null": True, "blank": True},
            ],
            with_timestamps=True
        )
    """
    logger.info(f"Generating model: {model_name}")
    
    # Imports sammeln
    imports = [
        "from django.db import models",
    ]
    
    if with_uuid_pk:
        imports.append("import uuid")
    
    if with_timestamps or with_soft_delete:
        imports.append("from django.utils import timezone")
    
    # Check for URL field -> reverse import
    has_get_absolute_url = True  # Immer generieren
    if has_get_absolute_url:
        imports.append("from django.urls import reverse")
    
    # Fields generieren
    field_lines = []
    
    # UUID PK
    if with_uuid_pk:
        field_lines.append(
            "id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)"
        )
    
    # User-defined fields
    for field in fields:
        field_line = _generate_field(field, imports)
        if field_line:
            field_lines.append(field_line)
    
    # Timestamp fields
    if with_timestamps:
        field_lines.append(
            "created_at = models.DateTimeField(auto_now_add=True)"
        )
        field_lines.append(
            "updated_at = models.DateTimeField(auto_now=True)"
        )
    
    # Soft delete fields
    if with_soft_delete:
        field_lines.append(
            "is_deleted = models.BooleanField(default=False)"
        )
        field_lines.append(
            "deleted_at = models.DateTimeField(null=True, blank=True)"
        )
    
    # Meta class
    meta_lines = []
    if ordering:
        meta_lines.append(f"ordering = {ordering}")
    if verbose_name:
        meta_lines.append(f'verbose_name = "{verbose_name}"')
        meta_lines.append(f'verbose_name_plural = "{pluralize(verbose_name)}"')
    else:
        vn = model_to_verbose(model_name)
        meta_lines.append(f'verbose_name = "{vn}"')
        meta_lines.append(f'verbose_name_plural = "{pluralize(vn)}"')
    
    # Build code
    code_parts = []
    
    # Imports
    code_parts.append("\n".join(sorted(set(imports))))
    code_parts.append("")
    code_parts.append("")
    
    # Class definition
    code_parts.append(f"class {model_name}(models.Model):")
    
    # Docstring
    if docstring:
        code_parts.append(f'    """{docstring}"""')
        code_parts.append("")
    
    # Fields
    for line in field_lines:
        code_parts.append(f"    {line}")
    
    code_parts.append("")
    
    # Meta class
    code_parts.append("    class Meta:")
    for line in meta_lines:
        code_parts.append(f"        {line}")
    
    code_parts.append("")
    
    # __str__ method
    str_field = _find_str_field(fields, model_name)
    code_parts.append("    def __str__(self):")
    code_parts.append(f'        return str(self.{str_field})')
    
    code_parts.append("")
    
    # get_absolute_url
    url_name = snake_case(model_name)
    code_parts.append("    def get_absolute_url(self):")
    code_parts.append(f'        return reverse("{app_name}:{url_name}_detail", kwargs={{"pk": self.pk}})')
    
    # Soft delete method
    if with_soft_delete:
        code_parts.append("")
        code_parts.append("    def soft_delete(self):")
        code_parts.append('        """Soft delete this instance."""')
        code_parts.append("        self.is_deleted = True")
        code_parts.append("        self.deleted_at = timezone.now()")
        code_parts.append("        self.save(update_fields=['is_deleted', 'deleted_at'])")
        code_parts.append("")
        code_parts.append("    def restore(self):")
        code_parts.append('        """Restore a soft-deleted instance."""')
        code_parts.append("        self.is_deleted = False")
        code_parts.append("        self.deleted_at = None")
        code_parts.append("        self.save(update_fields=['is_deleted', 'deleted_at'])")
    
    return "\n".join(code_parts)


def _generate_field(field: dict, imports: list[str]) -> str:
    """Generiert eine einzelne Field-Definition."""
    name = field.get("name")
    ftype = field.get("type", "CharField")
    
    # Build field arguments
    args = []
    
    # Relation fields
    if ftype in ("ForeignKey", "OneToOneField", "ManyToManyField"):
        to = field.get("to", "self")
        if "." not in to and to != "self":
            to = f'"{to}"'  # Lazy reference
        args.append(to)
        
        if ftype in ("ForeignKey", "OneToOneField"):
            on_delete = field.get("on_delete", "CASCADE")
            args.append(f"on_delete=models.{on_delete}")
        
        if field.get("related_name"):
            args.append(f'related_name="{field["related_name"]}"')
    
    # CharField/SlugField max_length
    if ftype in ("CharField", "SlugField") and field.get("max_length"):
        args.append(f"max_length={field['max_length']}")
    
    # DecimalField
    if ftype == "DecimalField":
        args.append(f"max_digits={field.get('max_digits', 10)}")
        args.append(f"decimal_places={field.get('decimal_places', 2)}")
    
    # FileField/ImageField
    if ftype in ("FileField", "ImageField"):
        upload_to = field.get("upload_to", f"{snake_case(name)}s/")
        args.append(f'upload_to="{upload_to}"')
    
    # Choices
    if field.get("choices"):
        choices_name = f"{name.upper()}_CHOICES"
        # Note: Choices should be defined as class attribute
        choices_str = ", ".join(f'("{v}", "{l}")' for v, l in field["choices"])
        args.append(f"choices=[{choices_str}]")
    
    # Common options
    if field.get("blank"):
        args.append("blank=True")
    if field.get("null"):
        args.append("null=True")
    if field.get("default") is not None:
        default = field["default"]
        if isinstance(default, str) and not default.startswith(("models.", "timezone.")):
            args.append(f'default="{default}"')
        else:
            args.append(f"default={default}")
    if field.get("unique"):
        args.append("unique=True")
    if field.get("db_index"):
        args.append("db_index=True")
    if field.get("help_text"):
        args.append(f'help_text="{field["help_text"]}"')
    if field.get("verbose_name"):
        args.append(f'verbose_name="{field["verbose_name"]}"')
    
    args_str = ", ".join(args)
    return f"{name} = models.{ftype}({args_str})"


def _find_str_field(fields: list[dict], model_name: str) -> str:
    """Findet das beste Feld für __str__."""
    # Priorität: name, title, dann erstes CharField
    for fname in ["name", "title", "label", "subject"]:
        for f in fields:
            if f.get("name") == fname:
                return fname
    
    # Erstes CharField
    for f in fields:
        if f.get("type") == "CharField":
            return f["name"]
    
    # Fallback
    return "pk"


@mcp.tool()
def generate_choices_class(
    name: str,
    choices: list[tuple[str, str]],
    use_text_choices: bool = True,
) -> str:
    """
    Generiert eine Django TextChoices/IntegerChoices Klasse.
    
    Args:
        name: Name der Choices-Klasse (z.B. "TaskStatus")
        choices: Liste von (value, label) Tupeln
        use_text_choices: True für TextChoices, False für IntegerChoices
        
    Returns:
        Python Code für die Choices-Klasse
        
    Example:
        generate_choices_class(
            name="TaskStatus",
            choices=[("PENDING", "Pending"), ("IN_PROGRESS", "In Progress"), ("DONE", "Done")]
        )
    """
    base_class = "models.TextChoices" if use_text_choices else "models.IntegerChoices"
    
    lines = [
        "from django.db import models",
        "",
        "",
        f"class {name}({base_class}):",
    ]
    
    for i, (value, label) in enumerate(choices):
        if use_text_choices:
            lines.append(f'    {value.upper()} = "{value.lower()}", "{label}"')
        else:
            lines.append(f'    {value.upper()} = {i + 1}, "{label}"')
    
    return "\n".join(lines)


@mcp.tool()
def generate_model_manager(
    model_name: str,
    with_soft_delete: bool = True,
    custom_methods: list[dict] | None = None,
) -> str:
    """
    Generiert einen Custom Model Manager.
    
    Args:
        model_name: Name des Models
        with_soft_delete: Soft Delete QuerySet-Methoden
        custom_methods: Liste von Custom Methods:
            - name: Method name
            - filter: Filter dict (z.B. {"status": "active"})
            - description: Docstring
            
    Returns:
        Python Code für Manager und QuerySet
        
    Example:
        generate_model_manager(
            model_name="Task",
            with_soft_delete=True,
            custom_methods=[
                {"name": "pending", "filter": {"status": "pending"}, "description": "Get pending tasks"},
                {"name": "overdue", "filter": {"due_date__lt": "timezone.now()"}, "description": "Get overdue tasks"},
            ]
        )
    """
    lines = [
        "from django.db import models",
    ]
    
    if custom_methods:
        for m in custom_methods:
            if "timezone" in str(m.get("filter", {})):
                lines.append("from django.utils import timezone")
                break
    
    lines.extend(["", ""])
    
    # QuerySet
    lines.append(f"class {model_name}QuerySet(models.QuerySet):")
    
    if with_soft_delete:
        lines.append('    """Custom QuerySet with soft delete support."""')
        lines.append("")
        lines.append("    def active(self):")
        lines.append('        """Return non-deleted objects."""')
        lines.append("        return self.filter(is_deleted=False)")
        lines.append("")
        lines.append("    def deleted(self):")
        lines.append('        """Return soft-deleted objects."""')
        lines.append("        return self.filter(is_deleted=True)")
    
    if custom_methods:
        for method in custom_methods:
            lines.append("")
            lines.append(f"    def {method['name']}(self):")
            if method.get("description"):
                lines.append(f'        """{method["description"]}"""')
            
            filter_str = ", ".join(f"{k}={v}" for k, v in method["filter"].items())
            lines.append(f"        return self.filter({filter_str})")
    
    lines.extend(["", ""])
    
    # Manager
    lines.append(f"class {model_name}Manager(models.Manager):")
    lines.append('    """Custom Manager using {model_name}QuerySet."""')
    lines.append("")
    lines.append("    def get_queryset(self):")
    lines.append(f"        return {model_name}QuerySet(self.model, using=self._db)")
    
    if with_soft_delete:
        lines.append("")
        lines.append("    def active(self):")
        lines.append("        return self.get_queryset().active()")
        lines.append("")
        lines.append("    def deleted(self):")
        lines.append("        return self.get_queryset().deleted()")
    
    if custom_methods:
        for method in custom_methods:
            lines.append("")
            lines.append(f"    def {method['name']}(self):")
            lines.append(f"        return self.get_queryset().{method['name']}()")
    
    lines.extend(["", ""])
    
    # Usage hint
    lines.append(f"# Add to {model_name} model:")
    lines.append(f"# objects = {model_name}Manager()")
    
    return "\n".join(lines)
