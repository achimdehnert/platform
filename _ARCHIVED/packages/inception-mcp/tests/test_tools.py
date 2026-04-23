"""
Tests for Inception MCP Tools
=============================

Run with: pytest tests/test_tools.py -v
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch

from inception_mcp.tools import (
    start_business_case,
    answer_question,
    finalize_business_case,
    list_business_cases,
    get_business_case,
    get_categories,
    submit_for_review,
    get_session_status,
    SESSIONS,
    INCEPTION_QUESTIONS,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(autouse=True)
def clear_sessions():
    """Clear sessions before each test."""
    SESSIONS.clear()
    yield
    SESSIONS.clear()


@pytest.fixture
def mock_db():
    """Mock database functions."""
    with patch("inception_mcp.tools.execute_query") as mock_query, \
         patch("inception_mcp.tools.execute_one") as mock_one, \
         patch("inception_mcp.tools.execute_write") as mock_write, \
         patch("inception_mcp.tools.execute_insert_returning") as mock_insert:
        
        # Default returns
        mock_query.return_value = []
        mock_one.return_value = None
        mock_write.return_value = 1
        mock_insert.return_value = {"id": 1, "code": "BC-001"}
        
        yield {
            "query": mock_query,
            "one": mock_one,
            "write": mock_write,
            "insert": mock_insert,
        }


# =============================================================================
# TESTS: start_business_case
# =============================================================================

@pytest.mark.asyncio
async def test_start_business_case_returns_session(mock_db):
    """Test that start_business_case creates a session."""
    # Setup mocks - order must match actual call order in start_business_case:
    # 1. get_lookup_choice_id("bc_category", "feature")
    # 2. get_lookup_choice_id("bc_status", "draft")
    # 3. generate_bc_code() -> execute_one
    # 4. get_lookup_choice_id("conversation_status", "active")
    mock_db["one"].side_effect = [
        {"id": 1},        # category lookup
        {"id": 2},        # status lookup
        {"next_num": 1},  # BC code generation
        {"id": 3},        # conversation status lookup
    ]
    mock_db["insert"].side_effect = [
        {"id": 1, "code": "BC-001"},  # BC insert
        {"id": 1},                      # Conversation insert
    ]
    
    result = await start_business_case(
        initial_description="Wir brauchen eine bessere Suchfunktion"
    )
    
    assert "session_id" in result
    assert result["bc_code"] == "BC-001"
    assert "question" in result
    assert result["questions_remaining"] == len(INCEPTION_QUESTIONS)


@pytest.mark.asyncio
async def test_start_business_case_with_category(mock_db):
    """Test starting BC with specific category."""
    # Order: category lookup, status lookup, BC code gen, conv status lookup
    mock_db["one"].side_effect = [
        {"id": 5},        # enhancement category lookup
        {"id": 2},        # status lookup
        {"next_num": 42}, # BC code generation
        {"id": 3},        # conversation status lookup
    ]
    mock_db["insert"].side_effect = [
        {"id": 42, "code": "BC-042"},
        {"id": 1},
    ]
    
    result = await start_business_case(
        initial_description="Performance verbessern",
        category="enhancement"
    )
    
    assert result["bc_code"] == "BC-042"


# =============================================================================
# TESTS: answer_question
# =============================================================================

@pytest.mark.asyncio
async def test_answer_question_progresses(mock_db):
    """Test that answer_question progresses through questions."""
    # Setup session
    session_id = "test-session-123"
    SESSIONS[session_id] = {
        "bc_id": 1,
        "bc_code": "BC-001",
        "current_question_index": 0,
        "answers": {},
        "started_at": "2024-01-01T00:00:00",
    }
    
    result = await answer_question(
        session_id=session_id,
        answer="Alle registrierten Benutzer"
    )
    
    assert "question" in result
    assert result["questions_remaining"] == len(INCEPTION_QUESTIONS) - 1
    assert SESSIONS[session_id]["current_question_index"] == 1


@pytest.mark.asyncio
async def test_answer_question_invalid_session():
    """Test error for invalid session."""
    result = await answer_question(
        session_id="invalid-session",
        answer="Some answer"
    )
    
    assert "error" in result


@pytest.mark.asyncio
async def test_answer_question_last_returns_summary(mock_db):
    """Test that last question returns summary."""
    session_id = "test-session-456"
    SESSIONS[session_id] = {
        "bc_id": 1,
        "bc_code": "BC-001",
        "current_question_index": len(INCEPTION_QUESTIONS) - 1,
        "answers": {},
        "started_at": "2024-01-01T00:00:00",
    }
    
    mock_db["one"].return_value = {
        "code": "BC-001",
        "title": "Test BC",
        "category_name": "Feature",
        "status_name": "Draft",
        "problem_statement": "Problem",
        "target_audience": "Users",
        "scope": "Scope",
        "requires_adr": False,
    }
    
    result = await answer_question(
        session_id=session_id,
        answer="Nein, kein ADR nötig"
    )
    
    assert result["ready_for_finalization"] is True
    assert "summary" in result


# =============================================================================
# TESTS: finalize_business_case
# =============================================================================

@pytest.mark.asyncio
async def test_finalize_business_case(mock_db):
    """Test finalizing a business case."""
    session_id = "test-session-789"
    SESSIONS[session_id] = {
        "bc_id": 1,
        "bc_code": "BC-001",
        "current_question_index": len(INCEPTION_QUESTIONS),
        "answers": {"target_audience": "Users"},
        "started_at": "2024-01-01T00:00:00",
    }
    
    # Order of execute_one calls in finalize_business_case:
    # 1. get_lookup_choice_id("bc_status", "submitted")
    # 2. execute_one for old status
    # 3. get_lookup_choice_id("review_entity_type", "business_case")
    # 4. get_lookup_choice_id("conversation_status", "completed")
    # 5. execute_one for BC details (derive_use_cases=True)
    # 6. get_lookup_choice_id("uc_status", "draft")
    # 7. execute_one for UC code generation
    mock_db["one"].side_effect = [
        {"id": 10},       # submitted status lookup
        {"status_id": 1}, # old status from BC
        {"id": 20},       # entity type lookup
        {"id": 30},       # conversation status lookup
        {"id": 1, "code": "BC-001", "title": "Test", "scope": "Test scope"},  # BC details
        {"id": 40},       # uc_status draft lookup
        {"next_num": 1},  # UC code generation
    ]
    mock_db["insert"].return_value = {"id": 1, "code": "UC-001"}
    
    result = await finalize_business_case(
        session_id=session_id,
        derive_use_cases=True
    )
    
    assert result["success"] is True
    assert result["bc_code"] == "BC-001"
    assert result["status"] == "submitted"
    assert session_id not in SESSIONS  # Session cleaned up


# =============================================================================
# TESTS: list_business_cases
# =============================================================================

@pytest.mark.asyncio
async def test_list_business_cases_empty(mock_db):
    """Test listing with no results."""
    mock_db["query"].return_value = []
    
    result = await list_business_cases()
    
    assert result["count"] == 0
    assert result["business_cases"] == []


@pytest.mark.asyncio
async def test_list_business_cases_with_filters(mock_db):
    """Test listing with filters."""
    mock_db["query"].return_value = [
        {
            "code": "BC-001",
            "title": "Test BC",
            "status_code": "draft",
            "status_name": "Draft",
            "status_color": "#gray",
            "category_code": "feature",
            "category_name": "Feature",
            "category_color": "#blue",
            "priority_code": None,
            "priority_name": None,
            "created_at": None,
        }
    ]
    
    result = await list_business_cases(
        status="draft",
        category="feature",
        search="Test",
        limit=10
    )
    
    assert result["count"] == 1
    assert result["business_cases"][0]["code"] == "BC-001"


# =============================================================================
# TESTS: get_categories
# =============================================================================

@pytest.mark.asyncio
async def test_get_categories(mock_db):
    """Test getting categories."""
    mock_db["query"].return_value = [
        {"code": "feature", "name": "Feature", "name_de": "Funktion", "color": "#blue", "icon": "bi-plus"},
        {"code": "bugfix", "name": "Bug Fix", "name_de": "Fehler", "color": "#red", "icon": "bi-bug"},
    ]
    
    result = await get_categories()
    
    assert len(result["categories"]) == 2
    assert result["categories"][0]["code"] == "feature"


# =============================================================================
# TESTS: get_session_status
# =============================================================================

@pytest.mark.asyncio
async def test_get_session_status_active():
    """Test status for active session."""
    session_id = "active-session"
    SESSIONS[session_id] = {
        "bc_id": 1,
        "bc_code": "BC-001",
        "current_question_index": 3,
        "answers": {},
        "started_at": "2024-01-01T00:00:00",
    }
    
    result = await get_session_status(session_id)
    
    assert result["status"] == "active"
    assert result["bc_code"] == "BC-001"
    assert result["questions_answered"] == 3
    assert result["current_question"] is not None


@pytest.mark.asyncio
async def test_get_session_status_completed(mock_db):
    """Test status for completed session."""
    mock_db["one"].return_value = {
        "status_code": "completed",
        "bc_code": "BC-001",
        "completed_at": None,
    }
    
    result = await get_session_status("completed-session")
    
    assert result["status"] == "completed"
    assert result["bc_code"] == "BC-001"
