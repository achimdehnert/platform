"""
Migrate core_prompt_templates from SQLite to prompt_templates in Postgres
Uses subprocess to execute SQL via docker exec
"""
import json
import sqlite3
import subprocess
import sys

# Mappings from SQLite INTEGER to Postgres VARCHAR
CATEGORY_MAP = {
    1: "character",
    2: "chapter", 
    3: "world",
    4: "plot",
    5: "dialogue",
    6: "description",
    7: "analysis",
    8: "dialogue",
    9: "plot",
}

LANGUAGE_MAP = {1: "en", 2: "de", 3: "es", 4: "fr"}
OUTPUT_FORMAT_MAP = {1: "text", 2: "json", 3: "markdown", 4: "structured"}
AB_TEST_GROUP_MAP = {0: "", 1: "A", 2: "B", 3: "C"}


def parse_json_field(value):
    """Parse JSON field, handling double-encoded strings"""
    if value is None:
        return []
    if isinstance(value, (list, dict)):
        return value
    try:
        parsed = json.loads(value)
        if isinstance(parsed, str):
            try:
                return json.loads(parsed)
            except:
                return parsed
        return parsed
    except:
        return value if value else []


def run_psql(sql):
    """Run SQL via docker exec"""
    cmd = ['docker', 'exec', '-i', 'bfagent_db', 'psql', '-U', 'bfagent', '-d', 'bfagent_dev', '-c', sql]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
    if result.returncode != 0:
        print(f"SQL Error: {result.stderr}")
    return result.stdout, result.returncode


def escape_sql(value):
    """Escape string for SQL"""
    if value is None:
        return 'NULL'
    s = str(value).replace("'", "''").replace("\\", "\\\\")
    return f"'{s}'"


def migrate():
    sqlite_path = r"c:\Users\achim\github\bfagent\bfagent_20251206.db"
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()
    
    # Read from SQLite
    sqlite_cur.execute("SELECT * FROM core_prompt_templates ORDER BY id")
    rows = sqlite_cur.fetchall()
    print(f"Found {len(rows)} records to migrate")
    
    # Check existing count
    out, _ = run_psql("SELECT COUNT(*) FROM prompt_templates;")
    print(f"Postgres output: {out.strip()}")
    
    # Clear existing
    print("Clearing existing prompt_templates...")
    run_psql("DELETE FROM prompt_template_tests; DELETE FROM prompt_executions;")
    run_psql("DELETE FROM prompt_templates;")
    
    migrated = 0
    for row in rows:
        try:
            category = CATEGORY_MAP.get(row['category'], 'character')
            language = LANGUAGE_MAP.get(row['language'], 'en')
            output_format = OUTPUT_FORMAT_MAP.get(row['output_format'], 'text')
            ab_test_group = AB_TEST_GROUP_MAP.get(row['ab_test_group'], '')
            
            required_vars = json.dumps(parse_json_field(row['required_variables']))
            optional_vars = json.dumps(parse_json_field(row['optional_variables']))
            var_defaults = json.dumps(parse_json_field(row['variable_defaults']))
            output_schema = json.dumps(parse_json_field(row['output_schema']))
            tags = json.dumps(parse_json_field(row['tags']))
            
            sql = f"""INSERT INTO prompt_templates (
                id, name, template_key, category, system_prompt, user_prompt_template,
                required_variables, optional_variables, variable_defaults,
                output_format, output_schema, max_tokens, temperature, top_p,
                frequency_penalty, presence_penalty, version, is_active, is_default,
                ab_test_group, ab_test_weight, language, usage_count, success_count,
                failure_count, avg_confidence, avg_execution_time, avg_tokens_used,
                avg_cost, description, tags, created_at, updated_at,
                created_by_id, fallback_template_id, parent_template_id, preferred_llm_id
            ) VALUES (
                {row['id']},
                {escape_sql(row['name'])},
                {escape_sql(row['template_key'])},
                {escape_sql(category)},
                {escape_sql(row['system_prompt'])},
                {escape_sql(row['user_prompt_template'])},
                {escape_sql(required_vars)}::jsonb,
                {escape_sql(optional_vars)}::jsonb,
                {escape_sql(var_defaults)}::jsonb,
                {escape_sql(output_format)},
                {escape_sql(output_schema)}::jsonb,
                {row['max_tokens']},
                {row['temperature']},
                {row['top_p']},
                {row['frequency_penalty']},
                {row['presence_penalty']},
                {escape_sql(row['version'])},
                {str(bool(row['is_active'])).lower()},
                {str(bool(row['is_default'])).lower()},
                {escape_sql(ab_test_group)},
                {row['ab_test_weight']},
                {escape_sql(language)},
                {row['usage_count']},
                {row['success_count']},
                {row['failure_count']},
                {row['avg_quality_score'] or 0.0},
                {row['avg_execution_time']},
                {row['avg_tokens_used']},
                {float(row['avg_cost'] or 0)},
                {escape_sql(row['description'] or '')},
                {escape_sql(tags)}::jsonb,
                {escape_sql(row['created_at'])},
                {escape_sql(row['updated_at'])},
                NULL, NULL, NULL, NULL
            );"""
            
            _, rc = run_psql(sql)
            if rc == 0:
                migrated += 1
                print(f"  ✓ {row['name']}")
            else:
                print(f"  ✗ {row['name']}")
                
        except Exception as e:
            print(f"  ✗ Error: {row['name']}: {e}")
    
    # Reset sequence
    run_psql("SELECT setval('prompt_templates_id_seq', (SELECT COALESCE(MAX(id), 1) FROM prompt_templates));")
    
    print(f"\n✅ Migrated {migrated}/{len(rows)} records")
    
    # Verify
    out, _ = run_psql("SELECT COUNT(*) FROM prompt_templates;")
    print(f"Final count: {out.strip()}")
    
    sqlite_conn.close()


if __name__ == "__main__":
    migrate()
