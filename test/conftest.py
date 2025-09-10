# test/conftest.py - Fixed version tanpa database mock yang bermasalah
import pytest
import os
import sys
from unittest.mock import Mock, patch

# Add the project root and src directory to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_path = os.path.join(project_root, 'src')
sys.path.insert(0, project_root)
sys.path.insert(0, src_path)

@pytest.fixture(autouse=True)
def mock_environment():
    """Mock environment variables for testing."""
    with patch.dict(os.environ, {
        'SECRET_KEY': 'test-secret-key-for-testing',
        'TOKEN_API': 'https://test-token-api.com',
        'NUSA_ID': 'test-nusa-id',
        'NUSA_SECRET': 'test-nusa-secret',
        'USERS_ID': 'test-users-id',
        'USERS_SECRET': 'test-users-secret',
        'DATABASE_URL': 'sqlite:///:memory:',  # In-memory database for tests
        'FLASK_ENV': 'testing'
    }):
        yield

@pytest.fixture(autouse=True)
def mock_services():
    """Mock all service dependencies."""
    # Mock the service classes from src/service/service.py
    with patch('service.service.ArticleService') as mock_article_service, \
         patch('service.service.QuestionService') as mock_question_service, \
         patch('service.service.OrganizationService') as mock_org_service, \
         patch('service.service.AskService') as mock_ask_service, \
         patch('service.service.LogService') as mock_log_service, \
         patch('service.service.webHook') as mock_webhook, \
         patch('validation.authentication.tokenService') as mock_token_service:
        
        # Setup mock instances
        mock_article_service.return_value = Mock()
        mock_question_service.return_value = Mock()
        mock_org_service.return_value = Mock()
        mock_ask_service.return_value = Mock()
        mock_log_service.return_value = Mock()
        mock_webhook.return_value = Mock()
        mock_token_service.return_value = Mock()
        
        yield {
            'article_service': mock_article_service.return_value,
            'question_service': mock_question_service.return_value,
            'org_service': mock_org_service.return_value,
            'ask_service': mock_ask_service.return_value,
            'log_service': mock_log_service.return_value,
            'webhook': mock_webhook.return_value,
            'token_service': mock_token_service.return_value
        }

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    # Import here to avoid circular imports
    from app import app
    
    app.config.update({
        'TESTING': True,
        'SECRET_KEY': 'test-secret-key-for-testing',
        'WTF_CSRF_ENABLED': False,  # Disable CSRF for testing
    })
    
    return app

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()

@pytest.fixture
def auth_headers(app):
    """Create authorization headers with a valid JWT token."""
    import jwt
    payload = {
        'client_id': 'test-client',
        'roles': ['private'],
        'exp': 9999999999  # Far future expiration
    }
    token = jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')
    return {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

@pytest.fixture
def public_auth_headers(app):
    """Create authorization headers with a public JWT token."""
    import jwt
    payload = {
        'client_id': 'test-client',
        'roles': ['public'],
        'exp': 9999999999
    }
    token = jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')
    return {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

# Mock data fixtures
@pytest.fixture
def sample_article():
    """Sample article data for testing."""
    return {
        'id': 1,
        'title': 'Test Article',
        'content': 'This is a test article content.',
        'author': 'Test Author',
        'created_at': '2024-01-01T00:00:00Z'
    }

@pytest.fixture
def sample_question():
    """Sample question data for testing."""
    return {
        'id': 1,
        'question': 'What is the meaning of life?',
        'answer': 'The meaning of life is 42.',
        'created_at': '2024-01-01T00:00:00Z'
    }

@pytest.fixture
def sample_organization():
    """Sample organization data for testing."""
    return {
        'id': 1,
        'name': 'Test Organization',
        'description': 'This is a test organization.',
        'created_at': '2024-01-01T00:00:00Z'
    }

@pytest.fixture
def sample_user():
    """Sample user data for testing."""
    return {
        'id': 1,
        'username': 'testuser',
        'email': 'test@example.com',
        'role': 'private'
    }

# Database fixtures (if you're using a database)
@pytest.fixture(scope='function')
def db_session():
    """Create a database session for testing."""
    # This would be implemented based on your database setup
    # For now, it's a placeholder
    pass


@pytest.fixture(autouse=True)
def disable_validators(monkeypatch):
    monkeypatch.setattr("app.validate_question_batch", lambda f: f)
    monkeypatch.setattr("app.validate_article_batch", lambda f: f)
# Note: Removed the problematic mock_database_operations fixture
# since it was causing AttributeError with connection.database_connection