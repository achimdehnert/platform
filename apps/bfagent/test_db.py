#!/usr/bin/env python
import psycopg2

conn = psycopg2.connect(
    host='localhost',
    database='bfagent_dev',
    user='bfagent_user',
    password='bfagent_secure_2024'
)
cur = conn.cursor()
cur.execute('SELECT id, name, provider FROM llms WHERE is_active = true LIMIT 5')
for row in cur.fetchall():
    print(row)
conn.close()
