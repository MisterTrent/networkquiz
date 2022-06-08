import pytest
from app import create_app
from app.models import Base, Topic
from flask import template_rendered, session
from app.extensions import db

@pytest.fixture(scope='module')
def app():
    '''App instance with database for functional tests'''

    application = create_app(config_type='Test')

    with application.app_context():
        Base.metadata.drop_all(db.engine)
        Base.metadata.create_all(db.engine)

    yield application
    
    with application.app_context():
        db.session.remove()
        Base.metadata.drop_all(db.engine)

@pytest.fixture(scope='function')
def client(app):
    return app.test_client()

@pytest.fixture(scope='function')
def captured_templates(app):
    '''Taken verbatim from Flask's documentation on signals:
    flask.palletsprojects.com/en/2.1.x/signals/#subscribing-to-signals
    '''
    recorded = []
    def record(sender, template, context, **extra):
        recorded.append((template, context))
    template_rendered.connect(record, app)
    try:
        yield recorded
    finally:
        template_rendered.disconnect(record, app)

def test_config(app):
    '''Ensure proper configuration object used by app factory'''
     
    assert app.config.get('TESTING') is True

def test_home(app, client, captured_templates):
    
    with app.app_context():
        db.session.add(Topic(name='Topic1'))
        db.session.add(Topic(name='Topic2'))
        db.session.commit()

    response = client.get('/')
    
    assert response.status_code == 200
    assert len(captured_templates) == 1

    template, context = captured_templates[0]

    assert template.name == 'index.html'
    assert 'Topic1' in context['quiz_topics']
    assert 'Topic2' in context['quiz_topics']

    with app.app_context():
        db.session.query(Topic).delete()
        db.session.commit()

def test_quiz_setup(app, client):
    '''Tests that user quiz settings are saved to the session.'''
    
    with app.app_context():
        db.session.add(Topic(name='Topic1'))
        db.session.add(Topic(name='Topic2'))
        db.session.commit()
   
    goodform = {'Topic1': '', 'Topic2': ''}
    errorform = {'Topic3': ''}

    with client:
        response = client.post('/quiz', data=goodform)

        assert response.status_code == 200
        assert 'Topic1' in session['topics']
        assert 'Topic2' in session['topics']

    with client:
        response = client.post('/quiz', data=errorform)

        assert response.status_code == 400
        assert 'topics' not in session
    
    with client:
        response = client.post('/quiz', data={})

        assert response.status_code == 400

    with app.app_context():
        db.session.query(Topic).delete()
        db.session.commit()
