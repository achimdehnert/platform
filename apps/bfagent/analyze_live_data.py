#!/usr/bin/env python
"""Analysiere Live-Daten in der Datenbank"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection

def analyze_live_data():
    """Analysiere welche Werte aktuell in der DB sind"""
    
    with connection.cursor() as cursor:
        results = {}
        
        # 1. Book Projects Status
        try:
            cursor.execute("SELECT DISTINCT status FROM book_projects WHERE status IS NOT NULL ORDER BY status")
            results['book_status'] = [row[0] for row in cursor.fetchall()]
        except:
            results['book_status'] = []
        
        # 2. Content Ratings
        try:
            cursor.execute("SELECT DISTINCT content_rating FROM book_projects WHERE content_rating IS NOT NULL ORDER BY content_rating")
            results['content_rating'] = [row[0] for row in cursor.fetchall()]
        except:
            results['content_rating'] = []
        
        # 3. Writing Stage
        try:
            cursor.execute("SELECT DISTINCT writing_stage FROM book_projects WHERE writing_stage IS NOT NULL ORDER BY writing_stage")
            results['writing_stage'] = [row[0] for row in cursor.fetchall()]
        except:
            results['writing_stage'] = []
        
        # 4. Genres (if exists as table)
        try:
            cursor.execute("SELECT name FROM genres WHERE is_active = 1 ORDER BY name")
            results['genres_table'] = [row[0] for row in cursor.fetchall()]
        except:
            results['genres_table'] = []
        
        # 5. Writing Status (if exists as table)
        try:
            cursor.execute("SELECT slug, name FROM writing_statuses WHERE is_active = 1 ORDER BY slug")
            results['writing_statuses_table'] = [(row[0], row[1]) for row in cursor.fetchall()]
        except:
            results['writing_statuses_table'] = []
        
        # 6. Handler Categories
        try:
            cursor.execute("SELECT DISTINCT category FROM handlers WHERE category IS NOT NULL ORDER BY category")
            results['handler_categories'] = [row[0] for row in cursor.fetchall()]
        except:
            results['handler_categories'] = []
        
        # 7. Review Status
        try:
            cursor.execute("SELECT DISTINCT status FROM review_sessions WHERE status IS NOT NULL ORDER BY status")
            results['review_status'] = [row[0] for row in cursor.fetchall()]
        except:
            results['review_status'] = []
        
        # 8. Test Case Categories
        try:
            cursor.execute("SELECT DISTINCT category FROM test_cases WHERE category IS NOT NULL ORDER BY category")
            results['test_categories'] = [row[0] for row in cursor.fetchall()]
        except:
            results['test_categories'] = []
    
    return results

if __name__ == "__main__":
    print("\n" + "="*80)
    print("LIVE DATA ANALYSIS - Welche Werte sind aktuell in der DB?")
    print("="*80 + "\n")
    
    data = analyze_live_data()
    
    for key, values in data.items():
        if values:
            print(f"\n📊 {key.upper().replace('_', ' ')}:")
            print("-" * 80)
            if isinstance(values[0], tuple):
                for slug, name in values:
                    print(f"  • {slug:20s} → {name}")
            else:
                for val in values:
                    print(f"  • {val}")
    
    print("\n" + "="*80)
    print("🎯 NÄCHSTER SCHRITT:")
    print("1. BACKUP machen!")
    print("2. Lookup-Tabellen erstellen")
    print("3. Live-Daten migrieren")
    print("="*80)
