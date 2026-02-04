"""
Inception Tools
===============

Tool implementations for the Inception MCP Server.
Handles Business Case creation, refinement, and finalization.
"""

import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any

import httpx

from .db import execute_query, execute_one, execute_write, execute_insert_returning

logger = logging.getLogger("inception-mcp.tools")

# In-memory session storage (for MVP - use Redis in production)
SESSIONS: dict[str, dict[str, Any]] = {}

# Questions for BC inception (ordered)
INCEPTION_QUESTIONS = [
    {
        "field": "target_audience",
        "question": "Wer ist die Zielgruppe? Wer profitiert von dieser Lösung?",
        "question_en": "Who is the target audience? Who benefits from this solution?",
    },
    {
        "field": "expected_benefits",
        "question": "Welche konkreten Vorteile werden erwartet? (Bitte als Liste)",
        "question_en": "What specific benefits are expected? (Please list them)",
    },
    {
        "field": "scope",
        "question": "Was ist im Scope enthalten? Was soll konkret umgesetzt werden?",
        "question_en": "What's in scope? What specifically should be implemented?",
    },
    {
        "field": "out_of_scope",
        "question": "Was ist explizit NICHT im Scope? (Bitte als Liste)",
        "question_en": "What is explicitly OUT of scope? (Please list)",
    },
    {
        "field": "success_criteria",
        "question": "Wie messen wir den Erfolg? Welche messbaren Kriterien gelten?",
        "question_en": "How do we measure success? What measurable criteria apply?",
    },
    {
        "field": "risks",
        "question": "Welche Risiken siehst du? (Format: Risiko, Wahrscheinlichkeit, Auswirkung)",
        "question_en": "What risks do you see? (Format: risk, probability, impact)",
    },
    {
        "field": "requires_adr",
        "question": "Ist eine Architekturentscheidung (ADR) erforderlich? Wenn ja, warum?",
        "question_en": "Is an architecture decision (ADR) required? If yes, why?",
    },
]


def get_llm_gateway_url() -> str:
    """Get LLM Gateway URL from environment."""
    return os.environ.get("LLM_GATEWAY_URL", "http://localhost:8080/v1")


async def call_llm(prompt: str, system_prompt: str | None = None) -> str:
    """Call LLM via gateway for text extraction/generation."""
    url = f"{get_llm_gateway_url()}/chat/completions"
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                url,
                json={
                    "model": os.environ.get("LLM_MODEL", "claude-3-sonnet"),
                    "messages": messages,
                    "temperature": 0.3,
                    "max_tokens": 2000,
                },
                headers={"Authorization": f"Bearer {os.environ.get('LLM_API_KEY', '')}"},
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning(f"LLM call failed: {e}, using fallback")
            return ""


async def generate_bc_code() -> str:
    """Generate next Business Case code."""
    result = await execute_one("""
        SELECT COALESCE(MAX(CAST(SUBSTRING(code FROM 4) AS INTEGER)), 0) + 1 AS next_num
        FROM platform.dom_business_case
        WHERE code ~ '^BC-[0-9]+$'
    """)
    next_num = result["next_num"] if result else 1
    return f"BC-{next_num:03d}"


async def get_lookup_choice_id(domain_code: str, choice_code: str) -> int | None:
    """Get lookup choice ID by domain and choice code."""
    result = await execute_one("""
        SELECT c.id
        FROM platform.lkp_choice c
        JOIN platform.lkp_domain d ON c.domain_id = d.id
        WHERE d.code = %s AND c.code = %s AND c.is_active = true
    """, (domain_code, choice_code))
    return result["id"] if result else None


# =============================================================================
# TOOL IMPLEMENTATIONS
# =============================================================================

async def start_business_case(
    initial_description: str,
    category: str | None = None,
) -> dict[str, Any]:
    """
    Start a new Business Case from free-text description.
    
    1. Analyze description with LLM to extract initial data
    2. Create BC draft in database
    3. Create inception session
    4. Return first question
    """
    session_id = str(uuid.uuid4())
    
    # Get category ID (default to 'feature')
    category_code = category or "feature"
    category_id = await get_lookup_choice_id("bc_category", category_code)
    if not category_id:
        category_id = await get_lookup_choice_id("bc_category", "feature")
    
    # Get draft status ID
    status_id = await get_lookup_choice_id("bc_status", "draft")
    
    # Generate BC code
    bc_code = await generate_bc_code()
    
    # Extract title from description using LLM (or simple fallback)
    title = initial_description[:100].split(".")[0].strip()
    if len(title) > 80:
        title = title[:77] + "..."
    
    # Create BC draft
    result = await execute_insert_returning("""
        INSERT INTO platform.dom_business_case 
        (code, title, category_id, status_id, problem_statement, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
        RETURNING id, code
    """, (bc_code, title, category_id, status_id, initial_description))
    
    bc_id = result["id"]
    
    # Create conversation record
    conv_status_id = await get_lookup_choice_id("conversation_status", "active")
    await execute_insert_returning("""
        INSERT INTO platform.dom_conversation
        (session_id, business_case_id, status_id, started_at, created_at, updated_at)
        VALUES (%s, %s, %s, NOW(), NOW(), NOW())
        RETURNING id
    """, (session_id, bc_id, conv_status_id))
    
    # Initialize session state
    SESSIONS[session_id] = {
        "bc_id": bc_id,
        "bc_code": bc_code,
        "current_question_index": 0,
        "answers": {},
        "started_at": datetime.utcnow().isoformat(),
    }
    
    # Return first question
    first_q = INCEPTION_QUESTIONS[0]
    
    return {
        "session_id": session_id,
        "bc_code": bc_code,
        "question": first_q["question"],
        "question_en": first_q["question_en"],
        "field": first_q["field"],
        "questions_remaining": len(INCEPTION_QUESTIONS),
        "message": f"Business Case {bc_code} erstellt. Bitte beantworte die folgenden Fragen.",
    }


async def answer_question(
    session_id: str,
    answer: str,
) -> dict[str, Any]:
    """
    Process answer to current question and return next question or summary.
    """
    if session_id not in SESSIONS:
        return {"error": f"Session {session_id} not found"}
    
    session = SESSIONS[session_id]
    current_idx = session["current_question_index"]
    
    if current_idx >= len(INCEPTION_QUESTIONS):
        return {"error": "Session already completed", "ready_for_finalization": True}
    
    current_q = INCEPTION_QUESTIONS[current_idx]
    field = current_q["field"]
    
    # Process answer based on field type
    processed_value = answer
    
    # For list fields, try to parse as JSON array or split by newlines
    if field in ["expected_benefits", "out_of_scope", "success_criteria"]:
        try:
            processed_value = json.loads(answer)
        except:
            # Split by newlines or commas
            lines = [l.strip() for l in answer.replace(",", "\n").split("\n") if l.strip()]
            processed_value = json.dumps(lines)
    elif field == "risks":
        # Parse risks into structured format
        try:
            processed_value = json.loads(answer)
        except:
            risks = []
            for line in answer.split("\n"):
                if line.strip():
                    risks.append({"description": line.strip(), "probability": "medium", "impact": "medium"})
            processed_value = json.dumps(risks)
    elif field == "requires_adr":
        # Boolean with optional reason
        lower_answer = answer.lower()
        requires = "ja" in lower_answer or "yes" in lower_answer or "true" in lower_answer
        session["adr_reason"] = answer if requires else ""
        processed_value = requires
    
    # Store answer
    session["answers"][field] = processed_value
    
    # Update BC in database
    bc_id = session["bc_id"]
    
    if field == "requires_adr":
        await execute_write(f"""
            UPDATE platform.dom_business_case
            SET requires_adr = %s, adr_reason = %s, updated_at = NOW()
            WHERE id = %s
        """, (processed_value, session.get("adr_reason", ""), bc_id))
    elif field in ["expected_benefits", "out_of_scope", "success_criteria", "risks"]:
        await execute_write(f"""
            UPDATE platform.dom_business_case
            SET {field} = %s::jsonb, updated_at = NOW()
            WHERE id = %s
        """, (processed_value, bc_id))
    else:
        await execute_write(f"""
            UPDATE platform.dom_business_case
            SET {field} = %s, updated_at = NOW()
            WHERE id = %s
        """, (processed_value, bc_id))
    
    # Move to next question
    session["current_question_index"] = current_idx + 1
    
    # Check if more questions
    if current_idx + 1 < len(INCEPTION_QUESTIONS):
        next_q = INCEPTION_QUESTIONS[current_idx + 1]
        return {
            "session_id": session_id,
            "question": next_q["question"],
            "question_en": next_q["question_en"],
            "field": next_q["field"],
            "questions_remaining": len(INCEPTION_QUESTIONS) - current_idx - 1,
        }
    
    # All questions answered - return summary
    bc = await execute_one("""
        SELECT bc.*, 
               cat.name as category_name,
               st.name as status_name
        FROM platform.dom_business_case bc
        JOIN platform.lkp_choice cat ON bc.category_id = cat.id
        JOIN platform.lkp_choice st ON bc.status_id = st.id
        WHERE bc.id = %s
    """, (bc_id,))
    
    return {
        "session_id": session_id,
        "ready_for_finalization": True,
        "summary": {
            "code": bc["code"],
            "title": bc["title"],
            "category": bc["category_name"],
            "problem_statement": bc["problem_statement"],
            "target_audience": bc["target_audience"],
            "scope": bc["scope"],
            "requires_adr": bc["requires_adr"],
        },
        "message": "Alle Fragen beantwortet. Bitte finalize_business_case aufrufen um abzuschließen.",
    }


async def finalize_business_case(
    session_id: str,
    adjustments: dict[str, Any] | None = None,
    derive_use_cases: bool = True,
) -> dict[str, Any]:
    """
    Finalize a Business Case and optionally derive Use Cases.
    """
    if session_id not in SESSIONS:
        return {"error": f"Session {session_id} not found"}
    
    session = SESSIONS[session_id]
    bc_id = session["bc_id"]
    bc_code = session["bc_code"]
    
    # Apply any adjustments
    if adjustments:
        for field, value in adjustments.items():
            if field in ["title", "problem_statement", "target_audience", "scope"]:
                await execute_write(f"""
                    UPDATE platform.dom_business_case
                    SET {field} = %s, updated_at = NOW()
                    WHERE id = %s
                """, (value, bc_id))
    
    # Update status to 'submitted'
    submitted_status_id = await get_lookup_choice_id("bc_status", "submitted")
    old_status_id = await execute_one("""
        SELECT status_id FROM platform.dom_business_case WHERE id = %s
    """, (bc_id,))
    
    await execute_write("""
        UPDATE platform.dom_business_case
        SET status_id = %s, updated_at = NOW()
        WHERE id = %s
    """, (submitted_status_id, bc_id))
    
    # Record status change
    entity_type_id = await get_lookup_choice_id("review_entity_type", "business_case")
    if entity_type_id and old_status_id:
        await execute_insert_returning("""
            INSERT INTO platform.dom_status_history
            (entity_type_id, entity_id, old_status_id, new_status_id, reason, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
            RETURNING id
        """, (entity_type_id, bc_id, old_status_id["status_id"], submitted_status_id, "Finalized via inception"))
    
    # Update conversation status
    conv_completed_id = await get_lookup_choice_id("conversation_status", "completed")
    await execute_write("""
        UPDATE platform.dom_conversation
        SET status_id = %s, completed_at = NOW(), updated_at = NOW()
        WHERE session_id = %s
    """, (conv_completed_id, session_id))
    
    derived_use_cases = []
    
    # Derive Use Cases if requested
    if derive_use_cases:
        bc = await execute_one("""
            SELECT * FROM platform.dom_business_case WHERE id = %s
        """, (bc_id,))
        
        # Simple derivation: create one UC from scope
        if bc and bc.get("scope"):
            uc_draft_status = await get_lookup_choice_id("uc_status", "draft")
            
            # Generate UC code
            uc_result = await execute_one("""
                SELECT COALESCE(MAX(CAST(SUBSTRING(code FROM 4) AS INTEGER)), 0) + 1 AS next_num
                FROM platform.dom_use_case
                WHERE code ~ '^UC-[0-9]+$'
            """)
            uc_num = uc_result["next_num"] if uc_result else 1
            uc_code = f"UC-{uc_num:03d}"
            
            await execute_insert_returning("""
                INSERT INTO platform.dom_use_case
                (code, title, business_case_id, status_id, actor, main_flow, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s::jsonb, NOW(), NOW())
                RETURNING id, code
            """, (
                uc_code,
                f"Hauptanwendungsfall für {bc['title']}",
                bc_id,
                uc_draft_status,
                "Registrierter Benutzer",
                json.dumps(["1. Benutzer öffnet die Anwendung", "2. [Details aus Scope ableiten]"]),
            ))
            
            derived_use_cases.append({"code": uc_code, "title": f"Hauptanwendungsfall für {bc['title']}"})
    
    # Cleanup session
    del SESSIONS[session_id]
    
    return {
        "success": True,
        "bc_code": bc_code,
        "status": "submitted",
        "derived_use_cases": derived_use_cases,
        "next_steps": [
            f"Business Case {bc_code} wurde eingereicht",
            "Ein Reviewer wird benachrichtigt",
            "Use Cases können im Web-UI detailliert werden" if derived_use_cases else "Use Cases manuell erstellen",
        ],
    }


async def list_business_cases(
    status: str | None = None,
    category: str | None = None,
    search: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """List Business Cases with filters."""
    conditions = ["1=1"]
    params = []
    
    if status:
        conditions.append("st.code = %s")
        params.append(status)
    
    if category:
        conditions.append("cat.code = %s")
        params.append(category)
    
    if search:
        conditions.append("(bc.title ILIKE %s OR bc.problem_statement ILIKE %s)")
        params.extend([f"%{search}%", f"%{search}%"])
    
    params.append(limit)
    
    results = await execute_query(f"""
        SELECT bc.code, bc.title, bc.created_at, bc.updated_at,
               st.code as status_code, st.name as status_name, st.color as status_color,
               cat.code as category_code, cat.name as category_name, cat.color as category_color,
               pri.code as priority_code, pri.name as priority_name
        FROM platform.dom_business_case bc
        JOIN platform.lkp_choice st ON bc.status_id = st.id
        JOIN platform.lkp_choice cat ON bc.category_id = cat.id
        LEFT JOIN platform.lkp_choice pri ON bc.priority_id = pri.id
        WHERE {' AND '.join(conditions)}
        ORDER BY bc.created_at DESC
        LIMIT %s
    """, tuple(params))
    
    return {
        "count": len(results),
        "business_cases": [
            {
                "code": r["code"],
                "title": r["title"],
                "status": {"code": r["status_code"], "name": r["status_name"], "color": r["status_color"]},
                "category": {"code": r["category_code"], "name": r["category_name"], "color": r["category_color"]},
                "priority": {"code": r["priority_code"], "name": r["priority_name"]} if r["priority_code"] else None,
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            }
            for r in results
        ],
    }


async def get_business_case(code: str) -> dict[str, Any]:
    """Get full Business Case details."""
    bc = await execute_one("""
        SELECT bc.*,
               st.code as status_code, st.name as status_name, st.color as status_color,
               cat.code as category_code, cat.name as category_name,
               pri.code as priority_code, pri.name as priority_name
        FROM platform.dom_business_case bc
        JOIN platform.lkp_choice st ON bc.status_id = st.id
        JOIN platform.lkp_choice cat ON bc.category_id = cat.id
        LEFT JOIN platform.lkp_choice pri ON bc.priority_id = pri.id
        WHERE bc.code = %s
    """, (code,))
    
    if not bc:
        return {"error": f"Business Case {code} not found"}
    
    # Get related Use Cases
    use_cases = await execute_query("""
        SELECT uc.code, uc.title, st.name as status
        FROM platform.dom_use_case uc
        JOIN platform.lkp_choice st ON uc.status_id = st.id
        WHERE uc.business_case_id = %s
        ORDER BY uc.code
    """, (bc["id"],))
    
    return {
        "code": bc["code"],
        "title": bc["title"],
        "status": {"code": bc["status_code"], "name": bc["status_name"], "color": bc["status_color"]},
        "category": {"code": bc["category_code"], "name": bc["category_name"]},
        "priority": {"code": bc["priority_code"], "name": bc["priority_name"]} if bc["priority_code"] else None,
        "problem_statement": bc["problem_statement"],
        "target_audience": bc["target_audience"],
        "expected_benefits": bc["expected_benefits"],
        "scope": bc["scope"],
        "out_of_scope": bc["out_of_scope"],
        "success_criteria": bc["success_criteria"],
        "assumptions": bc["assumptions"],
        "risks": bc["risks"],
        "requires_adr": bc["requires_adr"],
        "adr_reason": bc["adr_reason"],
        "use_cases": [{"code": uc["code"], "title": uc["title"], "status": uc["status"]} for uc in use_cases],
        "created_at": bc["created_at"].isoformat() if bc["created_at"] else None,
        "updated_at": bc["updated_at"].isoformat() if bc["updated_at"] else None,
    }


async def get_categories() -> dict[str, Any]:
    """Get all Business Case categories."""
    results = await execute_query("""
        SELECT c.code, c.name, c.name_de, c.color, c.icon
        FROM platform.lkp_choice c
        JOIN platform.lkp_domain d ON c.domain_id = d.id
        WHERE d.code = 'bc_category' AND c.is_active = true
        ORDER BY c.sort_order
    """)
    
    return {
        "categories": [
            {
                "code": r["code"],
                "name": r["name"],
                "name_de": r["name_de"],
                "color": r["color"],
                "icon": r["icon"],
            }
            for r in results
        ],
    }


async def submit_for_review(code: str) -> dict[str, Any]:
    """Submit a Business Case for review."""
    bc = await execute_one("""
        SELECT bc.id, bc.status_id, st.code as status_code
        FROM platform.dom_business_case bc
        JOIN platform.lkp_choice st ON bc.status_id = st.id
        WHERE bc.code = %s
    """, (code,))
    
    if not bc:
        return {"error": f"Business Case {code} not found"}
    
    if bc["status_code"] != "draft":
        return {"error": f"Business Case {code} is not in draft status (current: {bc['status_code']})"}
    
    # Update to submitted
    submitted_id = await get_lookup_choice_id("bc_status", "submitted")
    await execute_write("""
        UPDATE platform.dom_business_case
        SET status_id = %s, updated_at = NOW()
        WHERE id = %s
    """, (submitted_id, bc["id"]))
    
    # Record status change
    entity_type_id = await get_lookup_choice_id("review_entity_type", "business_case")
    if entity_type_id:
        await execute_insert_returning("""
            INSERT INTO platform.dom_status_history
            (entity_type_id, entity_id, old_status_id, new_status_id, reason, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
            RETURNING id
        """, (entity_type_id, bc["id"], bc["status_id"], submitted_id, "Submitted for review"))
    
    return {
        "success": True,
        "code": code,
        "new_status": "submitted",
        "message": f"Business Case {code} wurde zur Review eingereicht",
    }


async def get_session_status(session_id: str) -> dict[str, Any]:
    """Get current status of an inception session."""
    if session_id not in SESSIONS:
        # Check database for completed session
        conv = await execute_one("""
            SELECT c.*, st.code as status_code, bc.code as bc_code
            FROM platform.dom_conversation c
            JOIN platform.lkp_choice st ON c.status_id = st.id
            LEFT JOIN platform.dom_business_case bc ON c.business_case_id = bc.id
            WHERE c.session_id = %s
        """, (session_id,))
        
        if conv:
            return {
                "session_id": session_id,
                "status": conv["status_code"],
                "bc_code": conv["bc_code"],
                "completed_at": conv["completed_at"].isoformat() if conv["completed_at"] else None,
            }
        
        return {"error": f"Session {session_id} not found"}
    
    session = SESSIONS[session_id]
    current_idx = session["current_question_index"]
    
    current_question = None
    if current_idx < len(INCEPTION_QUESTIONS):
        q = INCEPTION_QUESTIONS[current_idx]
        current_question = {
            "field": q["field"],
            "question": q["question"],
            "question_en": q["question_en"],
        }
    
    return {
        "session_id": session_id,
        "status": "active",
        "bc_code": session["bc_code"],
        "questions_answered": current_idx,
        "questions_total": len(INCEPTION_QUESTIONS),
        "current_question": current_question,
        "ready_for_finalization": current_idx >= len(INCEPTION_QUESTIONS),
    }
