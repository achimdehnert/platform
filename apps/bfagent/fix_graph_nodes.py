#!/usr/bin/env python
"""Fix missing columns in graph_core_nodes table"""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.db import connection

cursor = connection.cursor()

# Add all missing columns based on GraphNode model
columns = [
    ('custom_color', 'VARCHAR(7) DEFAULT NULL'),
    ('custom_icon', 'VARCHAR(50) DEFAULT NULL'),
    ('custom_shape', 'VARCHAR(20) DEFAULT NULL'),
    ('is_locked', 'BOOLEAN DEFAULT FALSE'),
    ('is_hidden', 'BOOLEAN DEFAULT FALSE'),
    ('layer', 'INTEGER DEFAULT 0'),
]

for col_name, col_type in columns:
    try:
        cursor.execute(f'ALTER TABLE graph_core_nodes ADD COLUMN IF NOT EXISTS {col_name} {col_type}')
        print(f'Added {col_name} column')
    except Exception as e:
        print(f'Column {col_name}: {e}')

# Also fix graph_core_edges if needed
edge_columns = [
    ('custom_color', 'VARCHAR(7) DEFAULT NULL'),
    ('custom_style', 'VARCHAR(20) DEFAULT NULL'),
    ('weight', 'FLOAT DEFAULT 1.0'),
    ('is_hidden', 'BOOLEAN DEFAULT FALSE'),
]

for col_name, col_type in edge_columns:
    try:
        cursor.execute(f'ALTER TABLE graph_core_edges ADD COLUMN IF NOT EXISTS {col_name} {col_type}')
        print(f'Added {col_name} to edges')
    except Exception as e:
        print(f'Edge column {col_name}: {e}')

print('Done fixing graph tables')
