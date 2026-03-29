"""URL patterns for doc_templates."""

from django.urls import path

from . import views

app_name = "doc_templates"

urlpatterns = [
    # Templates
    path("", views.template_list, name="template-list"),
    path("create/", views.template_create, name="template-create"),
    path("upload/", views.template_upload, name="template-upload"),
    path("<int:pk>/edit/", views.template_edit, name="template-edit"),
    path("<int:pk>/delete/", views.template_delete, name="template-delete"),
    # Instances
    path(
        "<int:template_pk>/instance/create/",
        views.instance_create,
        name="instance-create",
    ),
    path("instance/<int:pk>/edit/", views.instance_edit, name="instance-edit"),
    path("instance/<int:pk>/delete/", views.instance_delete, name="instance-delete"),
    path("instance/<int:pk>/prefill/", views.instance_llm_prefill, name="instance-prefill"),
    path("instance/<int:pk>/bulk-prefill/", views.instance_bulk_prefill, name="instance-bulk-prefill"),
    path("instance/<int:pk>/pdf/", views.instance_pdf_export, name="instance-pdf"),
]
