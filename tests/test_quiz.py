import pytest
from sqlalchemy.orm import with_polymorphic
from werkzeug.datastructures import ImmutableMultiDict
from flask import template_rendered, session
from app import create_app
from app.models import Base, Topic, Question, MultipleChoice
from app.extensions import db
from app.quiz import prep_multichoice, extract_answers, score_input

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

def test_prep_multichoice(app):
    
    with app.app_context():
        
        polymap = with_polymorphic(Question, MultipleChoice)
        questions = db.session.query(polymap).all()
         
        q_ids = [q.id for q in questions]

        answer_key = prep_multichoice(questions) 
        
        for i, (key,data) in enumerate(answer_key.items()):
            assert q_ids[i] == data['id']

            possible_answers = data['choices']
            correct_idx = data['correct_index']
            
            assert possible_answers[correct_idx] == questions[i].correct

def test_extract_answers():

    goodform = ImmutableMultiDict([('q1','0'), ('q2','3')])
    goodout = extract_answers(goodform)
    
    assert len(goodout.keys()) == 2
    assert goodout[1] == '0'
    assert goodout[2] == '3'

    badform = ImmutableMultiDict([('1','0'), 
                                    ('q22a', '22'), 
                                    ('q', '1'), 
                                    ('2q3', '1'),
                                    ('','3'),
                                    ('q2','3')])
    badout = extract_answers(badform)

    assert len(badout.keys()) == 1
    assert badout[2] == '3'

def test_score_input():
    
    user_answers = {
        0 : 4,
        1 : 3
    }

    answer_key = {0 : {'correct_index' : 4},
                  1 : {'correct_index' : 2}}

    score = score_input(user_answers, answer_key)

    assert score[0] == 'correct' and score[1] == 'incorrect'

def test_quiz_round(app, client, captured_templates):
    
    with app.app_context(): 
        
        qlist = db.session.query(Question)\
            .filter(Question.topics.any(Topic.name.in_(['Topic1','Topic2'])))\
            .all()
        
    with client.session_transaction() as session:
        session['question_ids'] = [q.id for q in qlist]
        session['block_size'] = len(qlist)

    response = client.get('/get')
    
    template, context = captured_templates[0]
    
    assert response.status_code == 200
    assert template.name == 'quiz.html'
    assert 'questions' in context
    assert len(qlist) == len(context['questions']) 
    
    #TODO doesn't seem to use aliased columns as suggested by documentation,
    #such as q.question_id, q.multiple_choice_id, etc....why?
    #docs.sqlalchemy.org/en/14/orm/inheritance_loading.html
    q_ids = [q.id for q in context['questions'].values()]
    
    for q in qlist:
        assert q.id in q_ids
