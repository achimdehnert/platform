"""Create search_chunks table with pgvector and FTS indexes.

Deployed in content_store DB (ADR-062).
Requires: PostgreSQL 16+ with pgvector extension.
"""

from django.db import migrations


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.RunSQL(
            sql="CREATE EXTENSION IF NOT EXISTS vector;",
            reverse_sql="DROP EXTENSION IF EXISTS vector;",
        ),
        migrations.RunSQL(
            sql="""
            CREATE TABLE IF NOT EXISTS search_chunks (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID NOT NULL,
                source_type VARCHAR(50) NOT NULL,
                source_id UUID NOT NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                embedding vector(1536),
                metadata JSONB DEFAULT '{}',
                embedding_model VARCHAR(100) NOT NULL
                    DEFAULT 'text-embedding-3-small',
                created_at TIMESTAMPTZ DEFAULT now(),
                updated_at TIMESTAMPTZ DEFAULT now(),
                search_vector tsvector GENERATED ALWAYS AS (
                    to_tsvector('german', content)
                ) STORED
            );
            """,
            reverse_sql="DROP TABLE IF EXISTS search_chunks;",
        ),
        migrations.RunSQL(
            sql="""
            CREATE INDEX IF NOT EXISTS idx_chunks_embedding
                ON search_chunks
                USING hnsw (embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 64);
            CREATE INDEX IF NOT EXISTS idx_chunks_fts
                ON search_chunks USING gin(search_vector);
            CREATE INDEX IF NOT EXISTS idx_chunks_tenant
                ON search_chunks (tenant_id);
            CREATE INDEX IF NOT EXISTS idx_chunks_source
                ON search_chunks (source_type, source_id);
            CREATE INDEX IF NOT EXISTS idx_chunks_model
                ON search_chunks (embedding_model);
            """,
            reverse_sql="""
            DROP INDEX IF EXISTS idx_chunks_embedding;
            DROP INDEX IF EXISTS idx_chunks_fts;
            DROP INDEX IF EXISTS idx_chunks_tenant;
            DROP INDEX IF EXISTS idx_chunks_source;
            DROP INDEX IF EXISTS idx_chunks_model;
            """,
        ),
    ]
