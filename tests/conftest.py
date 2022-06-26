import pytest
from flask import template_rendered

from app import create_app
from app.extensions import db
from app.models import Base, Topic, Question, MultipleChoice

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

@pytest.fixture(scope='function')
def db_questions(app):
    '''Populates database with three topics and two questions.
    Question 1 tagged w/ Topic 1, Question 2 w/ Topic 1 and 2. Topic 3 is
    an 'orphan' with no associated question relationship.
    '''
    
    t1 = Topic(name='Topic1')
    t2 = Topic(name='Topic2')
    t3 = Topic(name='Topic3')
    
    q1_data = {
        'text' : 'test text',
        'qtype' : 'multiple_choice',
        'correct' : 'correct1',
        'incorrect' : 'choice1, choice2, choice3'
    }
    
    q2_data = {
        'text' : 'test text',
        'qtype' : 'multiple_choice',
        'correct' : 'correct2',
        'incorrect' : 'choice1, choice2, choice3'
    }

    q1 = MultipleChoice(**q1_data)
    q2 = MultipleChoice(**q2_data)

    q1.topics.append(t1)
    q2.topics.extend((t1,t2))

    with app.app_context():
        db.session.add(q1)
        db.session.add(q2)
        db.session.add(t3)
        db.session.commit()
        
    yield

    with app.app_context():
        topics = db.session.query(Topic).all()
        qlist = db.session.query(Question).all()
        
        for q in qlist:
            db.session.delete(q)

        for t in topics:
            db.session.delete(t)

        db.session.commit()
