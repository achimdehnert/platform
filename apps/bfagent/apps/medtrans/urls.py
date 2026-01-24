from django.urls import path

from . import views

app_name = "medtrans"

urlpatterns = [
    # Main views
    path("", views.presentation_list, name="presentation-list"),
    path("upload/", views.presentation_upload, name="presentation-upload"),
    # Customer management
    path("customers/", views.customer_list, name="customer-list"),
    path("customers/create/", views.customer_create, name="customer-create"),
    # Translation pipeline
    path(
        "presentations/<int:presentation_id>/translate/",
        views.start_translation_pipeline,
        name="start-translation"
    ),
    # Presentation management
    path(
        "presentations/<int:presentation_id>/delete/",
        views.presentation_delete,
        name="presentation-delete"
    ),
    path(
        "presentations/<int:presentation_id>/reset/",
        views.presentation_reset,
        name="presentation-reset"
    ),
    path(
        "presentations/<int:presentation_id>/edit/",
        views.presentation_edit,
        name="presentation-edit"
    ),
    path(
        "presentations/<int:presentation_id>/update/",
        views.presentation_update_texts,
        name="presentation-update-texts"
    ),
    path(
        "presentations/<int:presentation_id>/regenerate/",
        views.presentation_regenerate,
        name="presentation-regenerate"
    ),
]
