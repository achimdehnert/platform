"""
Pydantic Models für Tool-Eingaben und Validierung.
"""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


# === Enums ===

class FieldType(str, Enum):
    """Django Model Field Types."""
    CHAR = "CharField"
    TEXT = "TextField"
    INTEGER = "IntegerField"
    POSITIVE_INTEGER = "PositiveIntegerField"
    BIG_INTEGER = "BigIntegerField"
    SMALL_INTEGER = "SmallIntegerField"
    FLOAT = "FloatField"
    DECIMAL = "DecimalField"
    BOOLEAN = "BooleanField"
    NULL_BOOLEAN = "NullBooleanField"
    DATE = "DateField"
    DATETIME = "DateTimeField"
    TIME = "TimeField"
    DURATION = "DurationField"
    EMAIL = "EmailField"
    URL = "URLField"
    UUID = "UUIDField"
    SLUG = "SlugField"
    IP = "GenericIPAddressField"
    FILE = "FileField"
    IMAGE = "ImageField"
    JSON = "JSONField"
    FOREIGN_KEY = "ForeignKey"
    ONE_TO_ONE = "OneToOneField"
    MANY_TO_MANY = "ManyToManyField"


class ViewType(str, Enum):
    """Django Class-Based View Types."""
    LIST = "ListView"
    DETAIL = "DetailView"
    CREATE = "CreateView"
    UPDATE = "UpdateView"
    DELETE = "DeleteView"
    FORM = "FormView"
    TEMPLATE = "TemplateView"


class TemplateType(str, Enum):
    """Template Types für HTMX."""
    PAGE = "page"
    PARTIAL = "partial"
    COMPONENT = "component"
    MODAL = "modal"
    FORM = "form"
    TABLE = "table"
    LIST_ITEM = "list_item"


class SwapMethod(str, Enum):
    """HTMX Swap Methods."""
    INNER_HTML = "innerHTML"
    OUTER_HTML = "outerHTML"
    BEFORE_BEGIN = "beforebegin"
    AFTER_BEGIN = "afterbegin"
    BEFORE_END = "beforeend"
    AFTER_END = "afterend"
    DELETE = "delete"
    NONE = "none"


# === Model Field Definition ===

class FieldDefinition(BaseModel):
    """Definition eines Django Model Fields."""
    name: str = Field(..., description="Feldname (snake_case)")
    field_type: FieldType = Field(..., description="Django Field Type")
    
    # Common options
    max_length: int | None = Field(None, description="Für CharField/SlugField")
    blank: bool = Field(False, description="Erlaubt leeren Wert im Form")
    null: bool = Field(False, description="Erlaubt NULL in DB")
    default: str | None = Field(None, description="Default-Wert")
    unique: bool = Field(False, description="Unique Constraint")
    db_index: bool = Field(False, description="DB Index erstellen")
    help_text: str | None = Field(None, description="Hilfetext für Forms")
    verbose_name: str | None = Field(None, description="Human-readable Name")
    
    # Choices
    choices: list[tuple[str, str]] | None = Field(None, description="Choice-Tupel")
    
    # Relation options
    to: str | None = Field(None, description="Related Model (für FK/M2M/O2O)")
    on_delete: str | None = Field(None, description="on_delete für FK/O2O")
    related_name: str | None = Field(None, description="Related name")
    
    # Decimal options
    max_digits: int | None = Field(None, description="Für DecimalField")
    decimal_places: int | None = Field(None, description="Für DecimalField")
    
    # File options
    upload_to: str | None = Field(None, description="Upload-Pfad für File/Image")


# === Model Definition ===

class ModelMetaOptions(BaseModel):
    """Django Model Meta Options."""
    ordering: list[str] | None = Field(None, description="Default ordering")
    verbose_name: str | None = Field(None, description="Singular name")
    verbose_name_plural: str | None = Field(None, description="Plural name")
    db_table: str | None = Field(None, description="Custom table name")
    unique_together: list[list[str]] | None = Field(None, description="Unique constraints")
    indexes: list[dict] | None = Field(None, description="DB Indexes")
    constraints: list[dict] | None = Field(None, description="DB Constraints")
    abstract: bool = Field(False, description="Abstract base model")
    permissions: list[tuple[str, str]] | None = Field(None, description="Custom permissions")


class ModelDefinition(BaseModel):
    """Vollständige Model Definition."""
    name: str = Field(..., description="Model Name (PascalCase)")
    app_name: str = Field(..., description="Django App Name")
    fields: list[FieldDefinition] = Field(..., description="Model Fields")
    meta: ModelMetaOptions | None = Field(None, description="Meta Options")
    with_timestamps: bool = Field(True, description="created_at/updated_at hinzufügen")
    with_uuid_pk: bool = Field(False, description="UUID als Primary Key")
    with_soft_delete: bool = Field(False, description="Soft Delete Pattern")
    docstring: str | None = Field(None, description="Model Docstring")


# === View Definition ===

class ViewDefinition(BaseModel):
    """Definition für Class-Based View."""
    name: str = Field(..., description="View Name (PascalCase, mit View-Suffix)")
    view_type: ViewType = Field(..., description="CBV Type")
    model: str = Field(..., description="Model Name")
    template_name: str | None = Field(None, description="Custom Template Name")
    
    # HTMX Options
    htmx_enabled: bool = Field(True, description="HTMX Support")
    htmx_partial_template: str | None = Field(None, description="Partial für HTMX Requests")
    htmx_trigger: str | None = Field(None, description="HX-Trigger Header")
    
    # Permissions
    login_required: bool = Field(False, description="LoginRequiredMixin")
    permissions: list[str] | None = Field(None, description="Permission classes")
    
    # ListView options
    paginate_by: int | None = Field(None, description="Pagination")
    ordering: list[str] | None = Field(None, description="Ordering")
    
    # Form options
    form_class: str | None = Field(None, description="Custom Form Class")
    fields: list[str] | None = Field(None, description="Model fields für Form")
    success_url: str | None = Field(None, description="Redirect nach Success")
    
    # Context
    extra_context: dict | None = Field(None, description="Extra context data")


# === Template Definition ===

class TemplateDefinition(BaseModel):
    """Definition für HTMX Template."""
    name: str = Field(..., description="Template Name (mit .html)")
    template_type: TemplateType = Field(..., description="Template Type")
    extends_base: str | None = Field("base.html", description="Base Template")
    
    # HTMX Options
    hx_get: str | None = Field(None, description="hx-get URL")
    hx_post: str | None = Field(None, description="hx-post URL")
    hx_target: str | None = Field(None, description="hx-target Selector")
    hx_swap: SwapMethod = Field(SwapMethod.INNER_HTML, description="hx-swap Method")
    hx_trigger: str | None = Field(None, description="hx-trigger Event")
    
    # Content
    model_context: str | None = Field(None, description="Context Variable (object/object_list)")
    include_loading_indicator: bool = Field(True, description="HTMX Loading Indicator")
    include_error_handling: bool = Field(True, description="Error Display")


# === Table Column Definition ===

class TableColumn(BaseModel):
    """Definition einer Tabellen-Spalte."""
    field: str = Field(..., description="Model Field Name")
    label: str | None = Field(None, description="Column Header")
    sortable: bool = Field(False, description="Sortierbar")
    searchable: bool = Field(False, description="In Suche einbeziehen")
    template: str | None = Field(None, description="Custom Cell Template")
    width: str | None = Field(None, description="CSS Width")


# === Form Field Definition ===

class FormFieldConfig(BaseModel):
    """Konfiguration für Form Field."""
    name: str = Field(..., description="Field Name")
    widget: str | None = Field(None, description="Custom Widget")
    label: str | None = Field(None, description="Custom Label")
    help_text: str | None = Field(None, description="Help Text")
    required: bool | None = Field(None, description="Override required")
    initial: str | None = Field(None, description="Initial Value")
