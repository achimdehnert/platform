# ============================================================================
# DOMAIN DEVELOPMENT LIFECYCLE - SPHINX EXTENSION
# Step 6: Custom Sphinx Extension for Database Documents
# ============================================================================
#
# Part of: Domain Development Lifecycle System
# Location: docs/_extensions/db_docs.py
#
# This extension provides directives to include Business Cases, Use Cases,
# and ADRs from the database directly in Sphinx documentation.
#
# Usage in RST:
#   .. db-business-case:: BC-001
#   .. db-use-case:: UC-001
#   .. db-adr:: ADR-001
#   .. db-business-case-list::
#      :status: approved
#      :category: neue_domain
#
# ============================================================================

"""
Sphinx Extension für Database Documents.

Ermöglicht das Einbinden von Business Cases, Use Cases und ADRs
direkt aus der PostgreSQL Datenbank in die Sphinx-Dokumentation.

Setup:
    1. Extension in conf.py registrieren:
       extensions = ['_extensions.db_docs']
    
    2. Datenbank-Verbindung konfigurieren:
       db_docs_database_url = 'postgresql://...'
       # oder via Environment Variable:
       # DATABASE_URL
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from docutils import nodes
from docutils.parsers.rst import Directive, directives
from docutils.statemachine import StringList
from sphinx.application import Sphinx
from sphinx.util.docutils import SphinxDirective


# ============================================================================
# DATABASE CONNECTION
# ============================================================================

_db_connection = None


def get_db_connection(app: Sphinx):
    """Get or create database connection."""
    global _db_connection
    
    if _db_connection is not None:
        return _db_connection
    
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
    except ImportError:
        raise ImportError(
            "psycopg2 is required for db_docs extension. "
            "Install with: pip install psycopg2-binary"
        )
    
    # Get database URL from config or environment
    db_url = getattr(app.config, 'db_docs_database_url', None)
    if not db_url:
        db_url = os.environ.get('DATABASE_URL')
    
    if not db_url:
        raise ValueError(
            "Database URL not configured. Set db_docs_database_url in conf.py "
            "or DATABASE_URL environment variable."
        )
    
    _db_connection = psycopg2.connect(db_url, cursor_factory=RealDictCursor)
    return _db_connection


def close_db_connection(app: Sphinx, exception: Optional[Exception]):
    """Close database connection on build finish."""
    global _db_connection
    if _db_connection is not None:
        _db_connection.close()
        _db_connection = None


# ============================================================================
# DATA ACCESS FUNCTIONS
# ============================================================================

def get_business_case(app: Sphinx, code: str) -> Optional[Dict]:
    """Fetch a Business Case from database."""
    conn = get_db_connection(app)
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 
                bc.code,
                bc.title,
                bc.problem_statement,
                bc.target_audience,
                bc.expected_benefits,
                bc.scope,
                bc.out_of_scope,
                bc.success_criteria,
                bc.assumptions,
                bc.constraints,
                bc.risks,
                bc.stakeholders,
                bc.architecture_basis,
                cat.name as category_name,
                cat.code as category_code,
                st.name as status_name,
                st.code as status_code,
                bc.created_at,
                bc.updated_at
            FROM platform.dom_business_case bc
            JOIN platform.lkp_choice cat ON bc.category_id = cat.id
            JOIN platform.lkp_choice st ON bc.status_id = st.id
            WHERE bc.code = %s AND bc.deleted_at IS NULL
        """, (code,))
        return cur.fetchone()


def get_business_case_use_cases(app: Sphinx, bc_code: str) -> List[Dict]:
    """Fetch Use Cases for a Business Case."""
    conn = get_db_connection(app)
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 
                uc.code,
                uc.title,
                uc.actor,
                st.name as status_name,
                pr.name as priority_name
            FROM platform.dom_use_case uc
            JOIN platform.dom_business_case bc ON uc.business_case_id = bc.id
            JOIN platform.lkp_choice st ON uc.status_id = st.id
            JOIN platform.lkp_choice pr ON uc.priority_id = pr.id
            WHERE bc.code = %s AND uc.deleted_at IS NULL
            ORDER BY uc.sort_order, uc.code
        """, (bc_code,))
        return cur.fetchall()


def get_use_case(app: Sphinx, code: str) -> Optional[Dict]:
    """Fetch a Use Case from database."""
    conn = get_db_connection(app)
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 
                uc.code,
                uc.title,
                uc.description,
                uc.actor,
                uc.preconditions,
                uc.postconditions,
                uc.business_rules,
                uc.main_flow,
                uc.alternative_flows,
                uc.exception_flows,
                uc.technical_notes,
                uc.api_endpoints,
                uc.estimated_hours,
                bc.code as business_case_code,
                bc.title as business_case_title,
                st.name as status_name,
                st.code as status_code,
                pr.name as priority_name,
                cx.name as complexity_name,
                cx.metadata->>'story_points' as story_points
            FROM platform.dom_use_case uc
            JOIN platform.dom_business_case bc ON uc.business_case_id = bc.id
            JOIN platform.lkp_choice st ON uc.status_id = st.id
            JOIN platform.lkp_choice pr ON uc.priority_id = pr.id
            LEFT JOIN platform.lkp_choice cx ON uc.complexity_id = cx.id
            WHERE uc.code = %s AND uc.deleted_at IS NULL
        """, (code,))
        return cur.fetchone()


def get_adr(app: Sphinx, code: str) -> Optional[Dict]:
    """Fetch an ADR from database."""
    conn = get_db_connection(app)
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 
                adr.code,
                adr.title,
                adr.context,
                adr.decision,
                adr.consequences,
                adr.alternatives,
                adr.decision_drivers,
                adr.affected_components,
                adr.implementation_notes,
                adr.decision_date,
                bc.code as business_case_code,
                bc.title as business_case_title,
                st.name as status_name,
                st.code as status_code,
                st.metadata->>'badge' as status_badge,
                sup.code as supersedes_code
            FROM platform.dom_adr adr
            JOIN platform.lkp_choice st ON adr.status_id = st.id
            LEFT JOIN platform.dom_business_case bc ON adr.business_case_id = bc.id
            LEFT JOIN platform.dom_adr sup ON adr.supersedes_id = sup.id
            WHERE adr.code = %s AND adr.deleted_at IS NULL
        """, (code,))
        return cur.fetchone()


def list_business_cases(
    app: Sphinx,
    status: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50
) -> List[Dict]:
    """List Business Cases with optional filters."""
    conn = get_db_connection(app)
    with conn.cursor() as cur:
        query = """
            SELECT 
                bc.code,
                bc.title,
                cat.name as category_name,
                st.name as status_name,
                bc.created_at
            FROM platform.dom_business_case bc
            JOIN platform.lkp_choice cat ON bc.category_id = cat.id
            JOIN platform.lkp_choice st ON bc.status_id = st.id
            WHERE bc.deleted_at IS NULL
        """
        params = []
        
        if status:
            query += " AND st.code = %s"
            params.append(status)
        
        if category:
            query += " AND cat.code = %s"
            params.append(category)
        
        query += " ORDER BY bc.created_at DESC LIMIT %s"
        params.append(limit)
        
        cur.execute(query, params)
        return cur.fetchall()


# ============================================================================
# RST GENERATORS
# ============================================================================

def generate_business_case_rst(bc: Dict, use_cases: List[Dict]) -> str:
    """Generate RST content for a Business Case."""
    lines = []
    
    # Title
    title = f"{bc['code']}: {bc['title']}"
    lines.append(title)
    lines.append("=" * len(title))
    lines.append("")
    
    # Metadata
    lines.append(f":Status: {bc['status_name']}")
    lines.append(f":Kategorie: {bc['category_name']}")
    lines.append(f":Erstellt: {bc['created_at'].strftime('%d.%m.%Y')}")
    lines.append("")
    
    # Problem
    lines.append("Problem")
    lines.append("-" * 7)
    lines.append("")
    lines.append(bc['problem_statement'])
    lines.append("")
    
    # Target Audience
    if bc['target_audience']:
        lines.append("Zielgruppe")
        lines.append("-" * 10)
        lines.append("")
        lines.append(bc['target_audience'])
        lines.append("")
    
    # Expected Benefits
    if bc['expected_benefits']:
        lines.append("Erwarteter Nutzen")
        lines.append("-" * 17)
        lines.append("")
        lines.append(bc['expected_benefits'])
        lines.append("")
    
    # Success Criteria
    if bc['success_criteria']:
        lines.append("Erfolgskriterien")
        lines.append("-" * 16)
        lines.append("")
        for criterion in bc['success_criteria']:
            lines.append(f"* {criterion}")
        lines.append("")
    
    # Scope
    if bc['scope']:
        lines.append("Scope")
        lines.append("-" * 5)
        lines.append("")
        lines.append(bc['scope'])
        lines.append("")
    
    # Out of Scope
    if bc['out_of_scope']:
        lines.append("Out of Scope")
        lines.append("-" * 12)
        lines.append("")
        lines.append(bc['out_of_scope'])
        lines.append("")
    
    # Assumptions
    if bc['assumptions']:
        lines.append("Annahmen")
        lines.append("-" * 8)
        lines.append("")
        for assumption in bc['assumptions']:
            lines.append(f"* {assumption}")
        lines.append("")
    
    # Risks
    if bc['risks']:
        lines.append("Risiken")
        lines.append("-" * 7)
        lines.append("")
        for risk in bc['risks']:
            if isinstance(risk, dict):
                lines.append(f"* **{risk.get('risk', 'N/A')}**: {risk.get('mitigation', '')}")
            else:
                lines.append(f"* {risk}")
        lines.append("")
    
    # Architecture Basis
    if bc['architecture_basis']:
        lines.append("Architektur")
        lines.append("-" * 11)
        lines.append("")
        for key, value in bc['architecture_basis'].items():
            lines.append(f"* **{key}**: {value}")
        lines.append("")
    
    # Use Cases
    if use_cases:
        lines.append("Use Cases")
        lines.append("-" * 9)
        lines.append("")
        lines.append(".. list-table::")
        lines.append("   :header-rows: 1")
        lines.append("   :widths: 15 50 15 20")
        lines.append("")
        lines.append("   * - Code")
        lines.append("     - Titel")
        lines.append("     - Akteur")
        lines.append("     - Status")
        for uc in use_cases:
            lines.append(f"   * - :doc:`../use_cases/{uc['code']}`")
            lines.append(f"     - {uc['title']}")
            lines.append(f"     - {uc['actor'] or '-'}")
            lines.append(f"     - {uc['status_name']}")
        lines.append("")
    
    return "\n".join(lines)


def generate_use_case_rst(uc: Dict) -> str:
    """Generate RST content for a Use Case."""
    lines = []
    
    # Title
    title = f"{uc['code']}: {uc['title']}"
    lines.append(title)
    lines.append("=" * len(title))
    lines.append("")
    
    # Metadata
    lines.append(f":Business Case: :doc:`../business_cases/{uc['business_case_code']}`")
    lines.append(f":Status: {uc['status_name']}")
    lines.append(f":Priorität: {uc['priority_name']}")
    if uc['complexity_name']:
        lines.append(f":Komplexität: {uc['complexity_name']} ({uc['story_points']} SP)")
    if uc['actor']:
        lines.append(f":Akteur: {uc['actor']}")
    lines.append("")
    
    # Description
    if uc['description']:
        lines.append("Beschreibung")
        lines.append("-" * 12)
        lines.append("")
        lines.append(uc['description'])
        lines.append("")
    
    # Preconditions
    if uc['preconditions']:
        lines.append("Vorbedingungen")
        lines.append("-" * 14)
        lines.append("")
        for pre in uc['preconditions']:
            lines.append(f"* {pre}")
        lines.append("")
    
    # Main Flow
    if uc['main_flow']:
        lines.append("Hauptablauf")
        lines.append("-" * 11)
        lines.append("")
        for step in uc['main_flow']:
            step_num = step.get('step', '?')
            step_type = step.get('type', 'action')
            desc = step.get('description', '')
            
            type_icons = {
                'user_action': '👤',
                'system_action': '⚙️',
                'validation': '✅',
                'decision': '❓',
                'external_call': '🌐',
                'data_operation': '💾',
                'notification': '🔔',
            }
            icon = type_icons.get(step_type, '•')
            
            lines.append(f"{step_num}. {icon} {desc}")
        lines.append("")
    
    # Alternative Flows
    if uc['alternative_flows']:
        lines.append("Alternative Abläufe")
        lines.append("-" * 19)
        lines.append("")
        for alt in uc['alternative_flows']:
            lines.append(f"**{alt.get('name', 'Alternative')}**")
            lines.append("")
            lines.append(f"*Bedingung:* {alt.get('condition', '')}")
            lines.append("")
            if alt.get('steps'):
                for step in alt['steps']:
                    lines.append(f"   {step.get('step', '?')}. {step.get('description', '')}")
            lines.append("")
    
    # Exception Flows
    if uc['exception_flows']:
        lines.append("Ausnahme-Abläufe")
        lines.append("-" * 16)
        lines.append("")
        for exc in uc['exception_flows']:
            lines.append(f"**{exc.get('name', 'Exception')}**")
            lines.append("")
            lines.append(f"*Auslöser:* {exc.get('trigger', '')}")
            lines.append("")
    
    # Postconditions
    if uc['postconditions']:
        lines.append("Nachbedingungen")
        lines.append("-" * 15)
        lines.append("")
        for post in uc['postconditions']:
            lines.append(f"* {post}")
        lines.append("")
    
    # Business Rules
    if uc['business_rules']:
        lines.append("Geschäftsregeln")
        lines.append("-" * 15)
        lines.append("")
        for rule in uc['business_rules']:
            lines.append(f"* {rule}")
        lines.append("")
    
    # Technical Notes
    if uc['technical_notes']:
        lines.append("Technische Hinweise")
        lines.append("-" * 19)
        lines.append("")
        lines.append(uc['technical_notes'])
        lines.append("")
    
    # API Endpoints
    if uc['api_endpoints']:
        lines.append("API Endpoints")
        lines.append("-" * 13)
        lines.append("")
        lines.append(".. code-block::")
        lines.append("")
        for endpoint in uc['api_endpoints']:
            lines.append(f"   {endpoint}")
        lines.append("")
    
    return "\n".join(lines)


def generate_adr_rst(adr: Dict) -> str:
    """Generate RST content for an ADR."""
    lines = []
    
    # Title with badge
    badge = adr['status_badge'] or adr['status_code'].upper()
    title = f"{adr['code']}: {adr['title']}"
    lines.append(title)
    lines.append("=" * len(title))
    lines.append("")
    
    # Status badge
    lines.append(f".. admonition:: Status: {badge}")
    lines.append("   :class: note")
    lines.append("")
    lines.append(f"   {adr['status_name']}")
    if adr['decision_date']:
        lines.append(f"   (Entschieden am {adr['decision_date'].strftime('%d.%m.%Y')})")
    lines.append("")
    
    # Supersedes
    if adr['supersedes_code']:
        lines.append(f".. note:: Dieser ADR ersetzt :doc:`{adr['supersedes_code']}`")
        lines.append("")
    
    # Business Case link
    if adr['business_case_code']:
        lines.append(f":Business Case: :doc:`../business_cases/{adr['business_case_code']}`")
        lines.append("")
    
    # Context
    lines.append("Kontext")
    lines.append("-" * 7)
    lines.append("")
    lines.append(adr['context'])
    lines.append("")
    
    # Decision
    lines.append("Entscheidung")
    lines.append("-" * 12)
    lines.append("")
    lines.append(adr['decision'])
    lines.append("")
    
    # Decision Drivers
    if adr['decision_drivers']:
        lines.append("Entscheidungstreiber")
        lines.append("-" * 20)
        lines.append("")
        for driver in adr['decision_drivers']:
            lines.append(f"* {driver}")
        lines.append("")
    
    # Alternatives
    if adr['alternatives']:
        lines.append("Betrachtete Alternativen")
        lines.append("-" * 24)
        lines.append("")
        for alt in adr['alternatives']:
            lines.append(f"**{alt.get('name', 'Alternative')}**")
            if alt.get('description'):
                lines.append("")
                lines.append(alt['description'])
            lines.append("")
            if alt.get('pros'):
                lines.append("*Pro:*")
                for pro in alt['pros']:
                    lines.append(f"  * {pro}")
            if alt.get('cons'):
                lines.append("*Contra:*")
                for con in alt['cons']:
                    lines.append(f"  * {con}")
            if alt.get('score') is not None:
                lines.append(f"*Score:* {alt['score']}/10")
            lines.append("")
    
    # Consequences
    if adr['consequences']:
        lines.append("Konsequenzen")
        lines.append("-" * 12)
        lines.append("")
        lines.append(adr['consequences'])
        lines.append("")
    
    # Affected Components
    if adr['affected_components']:
        lines.append("Betroffene Komponenten")
        lines.append("-" * 21)
        lines.append("")
        for comp in adr['affected_components']:
            lines.append(f"* ``{comp}``")
        lines.append("")
    
    # Implementation Notes
    if adr['implementation_notes']:
        lines.append("Implementierungshinweise")
        lines.append("-" * 24)
        lines.append("")
        lines.append(adr['implementation_notes'])
        lines.append("")
    
    return "\n".join(lines)


# ============================================================================
# SPHINX DIRECTIVES
# ============================================================================

class DBBusinessCaseDirective(SphinxDirective):
    """
    Directive to include a Business Case from database.
    
    Usage:
        .. db-business-case:: BC-001
    """
    
    required_arguments = 1  # BC code
    optional_arguments = 0
    has_content = False
    
    def run(self) -> List[nodes.Node]:
        code = self.arguments[0]
        
        try:
            bc = get_business_case(self.env.app, code)
            if not bc:
                error = self.state_machine.reporter.error(
                    f"Business Case '{code}' not found in database.",
                    nodes.literal_block(self.block_text, self.block_text),
                    line=self.lineno
                )
                return [error]
            
            use_cases = get_business_case_use_cases(self.env.app, code)
            rst_content = generate_business_case_rst(bc, use_cases)
            
            # Parse RST and return nodes
            return self._parse_rst(rst_content)
            
        except Exception as e:
            error = self.state_machine.reporter.error(
                f"Error loading Business Case '{code}': {e}",
                nodes.literal_block(self.block_text, self.block_text),
                line=self.lineno
            )
            return [error]
    
    def _parse_rst(self, rst_content: str) -> List[nodes.Node]:
        """Parse RST content and return document nodes."""
        rst_lines = StringList(rst_content.split('\n'))
        node = nodes.section()
        node.document = self.state.document
        
        nested_parse_with_titles = self.state.nested_parse
        nested_parse_with_titles(rst_lines, self.content_offset, node)
        
        return node.children


class DBUseCaseDirective(SphinxDirective):
    """
    Directive to include a Use Case from database.
    
    Usage:
        .. db-use-case:: UC-001
    """
    
    required_arguments = 1
    optional_arguments = 0
    has_content = False
    
    def run(self) -> List[nodes.Node]:
        code = self.arguments[0]
        
        try:
            uc = get_use_case(self.env.app, code)
            if not uc:
                error = self.state_machine.reporter.error(
                    f"Use Case '{code}' not found in database.",
                    nodes.literal_block(self.block_text, self.block_text),
                    line=self.lineno
                )
                return [error]
            
            rst_content = generate_use_case_rst(uc)
            return self._parse_rst(rst_content)
            
        except Exception as e:
            error = self.state_machine.reporter.error(
                f"Error loading Use Case '{code}': {e}",
                nodes.literal_block(self.block_text, self.block_text),
                line=self.lineno
            )
            return [error]
    
    def _parse_rst(self, rst_content: str) -> List[nodes.Node]:
        rst_lines = StringList(rst_content.split('\n'))
        node = nodes.section()
        node.document = self.state.document
        self.state.nested_parse(rst_lines, self.content_offset, node)
        return node.children


class DBADRDirective(SphinxDirective):
    """
    Directive to include an ADR from database.
    
    Usage:
        .. db-adr:: ADR-001
    """
    
    required_arguments = 1
    optional_arguments = 0
    has_content = False
    
    def run(self) -> List[nodes.Node]:
        code = self.arguments[0]
        
        try:
            adr = get_adr(self.env.app, code)
            if not adr:
                error = self.state_machine.reporter.error(
                    f"ADR '{code}' not found in database.",
                    nodes.literal_block(self.block_text, self.block_text),
                    line=self.lineno
                )
                return [error]
            
            rst_content = generate_adr_rst(adr)
            return self._parse_rst(rst_content)
            
        except Exception as e:
            error = self.state_machine.reporter.error(
                f"Error loading ADR '{code}': {e}",
                nodes.literal_block(self.block_text, self.block_text),
                line=self.lineno
            )
            return [error]
    
    def _parse_rst(self, rst_content: str) -> List[nodes.Node]:
        rst_lines = StringList(rst_content.split('\n'))
        node = nodes.section()
        node.document = self.state.document
        self.state.nested_parse(rst_lines, self.content_offset, node)
        return node.children


class DBBusinessCaseListDirective(SphinxDirective):
    """
    Directive to list Business Cases from database.
    
    Usage:
        .. db-business-case-list::
           :status: approved
           :category: neue_domain
           :limit: 20
    """
    
    required_arguments = 0
    optional_arguments = 0
    has_content = False
    option_spec = {
        'status': directives.unchanged,
        'category': directives.unchanged,
        'limit': directives.positive_int,
    }
    
    def run(self) -> List[nodes.Node]:
        status = self.options.get('status')
        category = self.options.get('category')
        limit = self.options.get('limit', 50)
        
        try:
            business_cases = list_business_cases(
                self.env.app,
                status=status,
                category=category,
                limit=limit
            )
            
            if not business_cases:
                para = nodes.paragraph(text="Keine Business Cases gefunden.")
                return [para]
            
            # Create table
            table = nodes.table()
            tgroup = nodes.tgroup(cols=4)
            table += tgroup
            
            for width in [15, 50, 20, 15]:
                tgroup += nodes.colspec(colwidth=width)
            
            # Header
            thead = nodes.thead()
            tgroup += thead
            header_row = nodes.row()
            thead += header_row
            for header in ['Code', 'Titel', 'Kategorie', 'Status']:
                entry = nodes.entry()
                entry += nodes.paragraph(text=header)
                header_row += entry
            
            # Body
            tbody = nodes.tbody()
            tgroup += tbody
            
            for bc in business_cases:
                row = nodes.row()
                tbody += row
                
                # Code with link
                code_entry = nodes.entry()
                code_para = nodes.paragraph()
                ref = nodes.reference(
                    text=bc['code'],
                    refuri=f"../business_cases/{bc['code']}.html"
                )
                code_para += ref
                code_entry += code_para
                row += code_entry
                
                # Title
                title_entry = nodes.entry()
                title_entry += nodes.paragraph(text=bc['title'])
                row += title_entry
                
                # Category
                cat_entry = nodes.entry()
                cat_entry += nodes.paragraph(text=bc['category_name'])
                row += cat_entry
                
                # Status
                status_entry = nodes.entry()
                status_entry += nodes.paragraph(text=bc['status_name'])
                row += status_entry
            
            return [table]
            
        except Exception as e:
            error = self.state_machine.reporter.error(
                f"Error listing Business Cases: {e}",
                nodes.literal_block(self.block_text, self.block_text),
                line=self.lineno
            )
            return [error]


# ============================================================================
# SPHINX SETUP
# ============================================================================

def setup(app: Sphinx) -> Dict[str, Any]:
    """Setup the Sphinx extension."""
    
    # Configuration
    app.add_config_value('db_docs_database_url', None, 'env')
    
    # Register directives
    app.add_directive('db-business-case', DBBusinessCaseDirective)
    app.add_directive('db-use-case', DBUseCaseDirective)
    app.add_directive('db-adr', DBADRDirective)
    app.add_directive('db-business-case-list', DBBusinessCaseListDirective)
    
    # Connect events
    app.connect('build-finished', close_db_connection)
    
    return {
        'version': '1.0.0',
        'parallel_read_safe': False,  # Database connection not thread-safe
        'parallel_write_safe': True,
    }
