"""
URL Configuration for Book Reader
"""
from django.urls import path
from apps.bfagent.views.book_reader import (
    book_reader,
    chapter_view,
    chapter_api,
    export_docx,
    export_pdf,
    export_epub,
    chapter_edit,
    save_chapter,
    chapter_comments_reader,
    chapter_comment_add_reader,
)

app_name = 'book_reader'

urlpatterns = [
    # Book list
    path('', book_reader, name='book_list'),
    
    # Specific book chapters
    path('book/<int:project_id>/', book_reader, name='book_detail'),
    
    # Read specific chapter
    path('book/<int:project_id>/chapter/<int:chapter_number>/', 
         chapter_view, name='chapter_view'),
    
    # API endpoint for chapter content
    path('api/book/<int:project_id>/chapter/<int:chapter_number>/', 
         chapter_api, name='chapter_api'),
    
    # Export endpoints
    path('book/<int:project_id>/export/docx/', export_docx, name='export_docx'),
    path('book/<int:project_id>/export/pdf/', export_pdf, name='export_pdf'),
    path('book/<int:project_id>/export/epub/', export_epub, name='export_epub'),
    
    # Editor endpoints
    path('book/<int:project_id>/chapter/<int:chapter_number>/edit/', chapter_edit, name='chapter_edit'),
    path('book/<int:project_id>/chapter/<int:chapter_number>/save/', save_chapter, name='save_chapter'),
    
    # Chapter Comments (Reader-style URLs)
    path('book/<int:project_id>/chapter/<int:chapter_number>/comments/', 
         chapter_comments_reader, name='chapter_comments'),
    path('book/<int:project_id>/chapter/<int:chapter_number>/comment/add/', 
         chapter_comment_add_reader, name='chapter_comment_add'),
]
