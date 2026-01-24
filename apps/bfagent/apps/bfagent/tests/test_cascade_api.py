"""
Pytest Tests for Cascade Autonomous Work Session API

Tests the API endpoints for starting, monitoring, and stopping
autonomous Cascade work sessions.
"""

import pytest
import json
from django.urls import reverse
from django.contrib.auth import get_user_model

from apps.bfagent.models import TestRequirement
from apps.bfagent.models_cascade import CascadeWorkSession, CascadeWorkLog

User = get_user_model()


@pytest.fixture
def user(db):
    """Create a test user"""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def authenticated_client(client, user):
    """Return a logged-in client"""
    client.login(username='testuser', password='testpass123')
    return client


@pytest.fixture
def test_requirement(db, user):
    """Create a test requirement"""
    return TestRequirement.objects.create(
        name='Test Bug: Something is broken',
        description='This is a test bug description',
        category='bug_fix',
        priority='medium',
        domain='core',
        status='ready',
        created_by=user,
        acceptance_criteria=[
            {'id': 'ac_1', 'scenario': 'Test scenario', 'then': 'Expected result'}
        ]
    )


@pytest.fixture
def cascade_session(db, test_requirement, user):
    """Create a test cascade session"""
    return CascadeWorkSession.objects.create(
        requirement=test_requirement,
        domain='core',
        initial_context='Test context',
        max_iterations=10,
        created_by=user,
        status='running'
    )


# =============================================================================
# SESSION START TESTS
# =============================================================================

@pytest.mark.django_db
class TestSessionStart:
    """Tests for POST /api/cascade/session/start/"""
    
    def test_start_session_success(self, authenticated_client, test_requirement):
        """Should create a new session and return context"""
        url = reverse('control_center:cascade-session-start')
        data = {'requirement_id': str(test_requirement.id)}
        
        response = authenticated_client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result['success'] is True
        assert 'session_id' in result
        assert 'context' in result
        assert test_requirement.name in result['context']
        
        # Verify session was created
        session = CascadeWorkSession.objects.get(id=result['session_id'])
        assert session.requirement == test_requirement
        assert session.status == 'pending'
    
    def test_start_session_updates_requirement_status(self, authenticated_client, test_requirement):
        """Should update requirement status to in_progress"""
        url = reverse('control_center:cascade-session-start')
        data = {'requirement_id': str(test_requirement.id)}
        
        response = authenticated_client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        test_requirement.refresh_from_db()
        assert test_requirement.status == 'in_progress'
    
    def test_start_session_missing_requirement_id(self, authenticated_client):
        """Should return error if requirement_id is missing"""
        url = reverse('control_center:cascade-session-start')
        
        response = authenticated_client.post(
            url,
            data=json.dumps({}),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        result = response.json()
        assert result['success'] is False
        assert 'requirement_id' in result['error']
    
    def test_start_session_invalid_requirement(self, authenticated_client):
        """Should return error for non-existent requirement"""
        url = reverse('control_center:cascade-session-start')
        data = {'requirement_id': '00000000-0000-0000-0000-000000000000'}
        
        response = authenticated_client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # get_object_or_404 returns 404, but wrapped in try/except returns 500
        assert response.status_code in [404, 500]
    
    def test_start_session_already_active(self, authenticated_client, test_requirement):
        """Should return error if session already active"""
        url = reverse('control_center:cascade-session-start')
        data = {'requirement_id': str(test_requirement.id)}
        
        # Start first session
        response1 = authenticated_client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        assert response1.status_code == 200
        
        # Try to start second session
        response2 = authenticated_client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        assert response2.status_code == 409
        result = response2.json()
        assert result['success'] is False
        assert 'already exists' in result['error']
    
    def test_start_session_unauthenticated(self, client, test_requirement):
        """Should redirect unauthenticated users"""
        url = reverse('control_center:cascade-session-start')
        data = {'requirement_id': str(test_requirement.id)}
        
        response = client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Should redirect to login
        assert response.status_code == 302


# =============================================================================
# SESSION STATUS TESTS
# =============================================================================

@pytest.mark.django_db
class TestSessionStatus:
    """Tests for GET /api/cascade/session/{id}/"""
    
    def test_get_session_status(self, authenticated_client, cascade_session):
        """Should return session status"""
        url = reverse('control_center:cascade-session-status', kwargs={'session_id': cascade_session.id})
        
        response = authenticated_client.get(url)
        
        assert response.status_code == 200
        result = response.json()
        assert result['success'] is True
        assert result['session']['id'] == str(cascade_session.id)
        assert result['session']['status'] == 'running'
        assert result['session']['is_active'] is True
    
    def test_get_session_status_not_found(self, authenticated_client):
        """Should return 404 for non-existent session"""
        url = reverse('control_center:cascade-session-status', 
                      kwargs={'session_id': '00000000-0000-0000-0000-000000000000'})
        
        response = authenticated_client.get(url)
        
        assert response.status_code == 404


# =============================================================================
# SESSION STOP TESTS
# =============================================================================

@pytest.mark.django_db
class TestSessionStop:
    """Tests for POST /api/cascade/session/{id}/stop/"""
    
    def test_stop_session_success(self, authenticated_client, cascade_session):
        """Should stop an active session"""
        url = reverse('control_center:cascade-session-stop', kwargs={'session_id': cascade_session.id})
        
        response = authenticated_client.post(url)
        
        assert response.status_code == 200
        result = response.json()
        assert result['success'] is True
        
        cascade_session.refresh_from_db()
        assert cascade_session.status == 'stopped'
        assert cascade_session.completed_at is not None
    
    def test_stop_session_already_stopped(self, authenticated_client, cascade_session):
        """Should return error if session already stopped"""
        cascade_session.status = 'stopped'
        cascade_session.save()
        
        url = reverse('control_center:cascade-session-stop', kwargs={'session_id': cascade_session.id})
        
        response = authenticated_client.post(url)
        
        assert response.status_code == 400
        result = response.json()
        assert result['success'] is False


# =============================================================================
# SESSION ITERATE TESTS
# =============================================================================

@pytest.mark.django_db
class TestSessionIterate:
    """Tests for POST /api/cascade/session/{id}/iterate/"""
    
    def test_iterate_increments_counter(self, authenticated_client, cascade_session):
        """Should increment iteration counter"""
        url = reverse('control_center:cascade-session-iterate', kwargs={'session_id': cascade_session.id})
        
        response = authenticated_client.post(
            url,
            data=json.dumps({'success_check': False, 'summary': 'Fixed something'}),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result['success'] is True
        assert result['completed'] is False
        assert result['iteration'] == 1
        
        cascade_session.refresh_from_db()
        assert cascade_session.current_iteration == 1
    
    def test_iterate_with_success_check(self, authenticated_client, cascade_session, test_requirement):
        """Should mark session as success when success_check is True"""
        url = reverse('control_center:cascade-session-iterate', kwargs={'session_id': cascade_session.id})
        
        response = authenticated_client.post(
            url,
            data=json.dumps({'success_check': True, 'summary': 'Bug fixed!'}),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result['success'] is True
        assert result['completed'] is True
        assert result['status'] == 'success'
        
        cascade_session.refresh_from_db()
        assert cascade_session.status == 'success'
        
        test_requirement.refresh_from_db()
        assert test_requirement.status == 'done'
    
    def test_iterate_max_iterations_reached(self, authenticated_client, cascade_session):
        """Should stop when max iterations reached"""
        cascade_session.current_iteration = 9
        cascade_session.max_iterations = 10
        cascade_session.save()
        
        url = reverse('control_center:cascade-session-iterate', kwargs={'session_id': cascade_session.id})
        
        response = authenticated_client.post(
            url,
            data=json.dumps({'success_check': False}),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result['completed'] is True
        assert result['status'] == 'max_iterations'
        
        cascade_session.refresh_from_db()
        assert cascade_session.status == 'max_iterations'


# =============================================================================
# SESSION LOGS TESTS
# =============================================================================

@pytest.mark.django_db
class TestSessionLogs:
    """Tests for GET /api/cascade/session/{id}/logs/"""
    
    def test_get_logs(self, authenticated_client, cascade_session):
        """Should return session logs"""
        # Add some logs
        cascade_session.add_log('info', 'Test log 1')
        cascade_session.add_log('action', 'Test log 2')
        
        url = reverse('control_center:cascade-session-logs', kwargs={'session_id': cascade_session.id})
        
        response = authenticated_client.get(url)
        
        assert response.status_code == 200
        result = response.json()
        assert result['success'] is True
        assert len(result['logs']) == 2
        assert result['logs'][0]['message'] == 'Test log 1'
    
    def test_get_logs_with_limit(self, authenticated_client, cascade_session):
        """Should respect limit parameter"""
        # Add multiple logs
        for i in range(5):
            cascade_session.add_log('info', f'Log {i}')
        
        url = reverse('control_center:cascade-session-logs', kwargs={'session_id': cascade_session.id})
        
        response = authenticated_client.get(f"{url}?limit=3")
        
        assert response.status_code == 200
        result = response.json()
        assert len(result['logs']) == 3


# =============================================================================
# MODEL TESTS
# =============================================================================

@pytest.mark.django_db
class TestCascadeWorkSessionModel:
    """Tests for CascadeWorkSession model"""
    
    def test_progress_percentage(self, cascade_session):
        """Should calculate progress correctly"""
        cascade_session.current_iteration = 5
        cascade_session.max_iterations = 10
        
        assert cascade_session.progress_percentage == 50
    
    def test_is_active(self, cascade_session):
        """Should return True for active statuses"""
        cascade_session.status = 'running'
        assert cascade_session.is_active is True
        
        cascade_session.status = 'pending'
        assert cascade_session.is_active is True
        
        cascade_session.status = 'success'
        assert cascade_session.is_active is False
    
    def test_start(self, cascade_session):
        """Should set status and started_at"""
        cascade_session.status = 'pending'
        cascade_session.started_at = None
        cascade_session.start()
        
        assert cascade_session.status == 'running'
        assert cascade_session.started_at is not None
    
    def test_stop(self, cascade_session):
        """Should set status and completed_at"""
        cascade_session.stop('failed')
        
        assert cascade_session.status == 'failed'
        assert cascade_session.completed_at is not None
    
    def test_mark_success(self, cascade_session, test_requirement):
        """Should mark session and requirement as done"""
        cascade_session.mark_success('Bug fixed!')
        
        assert cascade_session.status == 'success'
        assert cascade_session.final_summary == 'Bug fixed!'
        
        test_requirement.refresh_from_db()
        assert test_requirement.status == 'done'
    
    def test_add_log(self, cascade_session):
        """Should create log entry"""
        log = cascade_session.add_log('info', 'Test message', {'key': 'value'})
        
        assert log.session == cascade_session
        assert log.log_type == 'info'
        assert log.message == 'Test message'
        assert log.details == {'key': 'value'}
        assert log.iteration == cascade_session.current_iteration
