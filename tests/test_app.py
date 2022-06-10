import pytest
from app import create_app
from app.models import Base, Topic, Question, MultipleChoice
from flask import template_rendered, session
from werkzeug.datastructures import ImmutableMultiDict
from app.extensions import db
from app.home import generate_id_list, process_form

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

@pytest.fixture(scope='module')
def db_questions(app):
    '''Populates database with three topics and two questions.
    Question 1 tagged w/ Topic 1, Question 2 w/ Topic 1 and 2. Topic 3 is
    an 'orphan' with no associated question relationship.
    '''
    
    #TODO scope='function' causes unique constraint error the second time
    #this fixture runs; possibly due to sqlite's autoincrement issue
    #docs.sqlalchemy.org/en/14/dialects/sqlite.html

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
        db.session.query(Topic).delete()
        db.session.query(Question).delete()
        db.session.commit()

def test_config(app):
    '''Ensure proper configuration object used by app factory'''
     
    assert app.config.get('TESTING') is True

def test_home_route(app, client, captured_templates):
    
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

def test_setup_form(app, db_questions):
    
    form1 = ImmutableMultiDict([('Topic1',''), ('Topic2','')])
    form2 = ImmutableMultiDict([('Topic3',''), ('Topic4','')])

    with app.app_context():
        output1 = process_form(form1)

    assert 'Topic1' in output1 and 'Topic2' in output1

    with app.app_context():
        output2 = process_form(form2)

    assert output2 == ['Topic3']

def test_question_list_generation(app, db_questions, client):
    
    with app.app_context():
        _id = db.session.query(Topic.id).filter(Topic.name=='Topic2').one()[0]
        idlist = generate_id_list(['Topic2'], randomize=False)

    assert len(idlist) == 1
    assert idlist[0] == _id

    with app.app_context():
        _ids = db.session.query(Topic.id)\
                .filter(Topic.name.in_(['Topic1','Topic2']))\
                .all()

        correct_ids = [v[0] for v in _ids]
        
        _id = db.session.query(Topic.id).filter(Topic.name == 'Topic3')
        incorrect_id = _id[0][0]

        idlist = generate_id_list(['Topic1','Topic2','Topic3'], randomize=True)

        assert len(idlist) == 2
        assert idlist[0] in correct_ids
        assert idlist[1] in correct_ids
        assert incorrect_id not in idlist

def test_quiz_setup_route(app, client):
    '''Tests that user quiz settings are saved to the session.'''
    
    goodform = {'Topic1': '', 'Topic2': ''}
    errorform = {'Topic4': ''}

    with client:
        response = client.post('/quiz', data=goodform)

        assert response.status_code == 200
        assert 1 in session['question_ids'] and 2 in session['question_ids']

    with client:
        response = client.post('/quiz', data=errorform)

        assert response.status_code == 400
        assert 'question_ids' not in session
    
    with client:
        response = client.post('/quiz', data={})

        assert response.status_code == 400
