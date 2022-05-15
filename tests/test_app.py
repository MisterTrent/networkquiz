import pytest
from app import create_app

@pytest.fixture(scope='module')
def app():
    app = create_app(config_type='Test')
    yield app

@pytest.fixture(scope='function')
def client(app):
    return app.test_client()

def test_config(app):
    '''Ensure proper configuration object used by app factory'''
    
    assert app.config.get('TESTING') is True

def test_home(client):

    response = client.get('/')
    assert response.status_code == 200
