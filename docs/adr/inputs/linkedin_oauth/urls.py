"""
linkedin_oauth/urls.py
"""
from django.urls import path
from . import views

app_name = "linkedin"

urlpatterns = [
    path("login/",      views.linkedin_login,        name="login"),
    path("callback/",   views.linkedin_callback,     name="callback"),
    path("disconnect/", views.linkedin_disconnect,   name="disconnect"),
    path("post/",       views.linkedin_post_share,   name="post_share"),
    path("status/",     views.linkedin_status,       name="status"),
]
