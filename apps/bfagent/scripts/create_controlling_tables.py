#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Erstellt die Controlling-Tabellen direkt in der Datenbank."""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection

def create_tables():
    """Erstellt die Controlling-Tabellen."""
    cursor = connection.cursor()
    
    # Create LLMUsageLog table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS bfagent_llmusagelog (
        id SERIAL PRIMARY KEY,
        timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        agent VARCHAR(50) NOT NULL,
        task VARCHAR(100) NOT NULL,
        model VARCHAR(50) NOT NULL,
        provider VARCHAR(30) DEFAULT 'unknown',
        tokens_in INTEGER DEFAULT 0,
        tokens_out INTEGER DEFAULT 0,
        cost_usd DECIMAL(10,6) DEFAULT 0.000000,
        latency_ms FLOAT DEFAULT 0.0,
        cached BOOLEAN DEFAULT FALSE,
        fallback_used BOOLEAN DEFAULT FALSE,
        success BOOLEAN DEFAULT TRUE,
        error_message TEXT,
        request_hash VARCHAR(64)
    )
    ''')
    print('✅ LLMUsageLog table created')

    # Create AgentValidationLog table  
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS bfagent_agentvalidationlog (
        id SERIAL PRIMARY KEY,
        timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        agent VARCHAR(50) NOT NULL,
        action VARCHAR(50) NOT NULL,
        passed BOOLEAN NOT NULL,
        errors_count INTEGER DEFAULT 0,
        warnings_count INTEGER DEFAULT 0,
        errors_prevented JSONB DEFAULT '[]',
        file_path VARCHAR(500),
        cascade_session_id VARCHAR(100)
    )
    ''')
    print('✅ AgentValidationLog table created')

    # Create ControllingBaseline table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS bfagent_controllingbaseline (
        id SERIAL PRIMARY KEY,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        metric_type VARCHAR(50) NOT NULL,
        period_days INTEGER DEFAULT 30,
        data JSONB NOT NULL,
        description TEXT
    )
    ''')
    print('✅ ControllingBaseline table created')

    # Create ControllingAlert table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS bfagent_controllingalert (
        id SERIAL PRIMARY KEY,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        alert_type VARCHAR(30) NOT NULL,
        severity VARCHAR(20) DEFAULT 'warning',
        message TEXT NOT NULL,
        threshold_value FLOAT,
        actual_value FLOAT,
        acknowledged BOOLEAN DEFAULT FALSE,
        acknowledged_at TIMESTAMP WITH TIME ZONE,
        acknowledged_by VARCHAR(100)
    )
    ''')
    print('✅ ControllingAlert table created')

    # Create indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_llmusagelog_timestamp ON bfagent_llmusagelog(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_llmusagelog_agent ON bfagent_llmusagelog(agent)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_llmusagelog_model ON bfagent_llmusagelog(model)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_agentvalidationlog_timestamp ON bfagent_agentvalidationlog(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_agentvalidationlog_agent ON bfagent_agentvalidationlog(agent)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_controllingbaseline_metric ON bfagent_controllingbaseline(metric_type)')
    print('✅ Indexes created')
    
    print()
    print('=' * 50)
    print('All Controlling tables created successfully!')
    print('=' * 50)

if __name__ == '__main__':
    create_tables()
