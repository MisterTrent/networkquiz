import pytest
from sqlalchemy.orm import with_polymorphic
from werkzeug.datastructures import ImmutableMultiDict
from app import create_app
from app.models import Base, Topic, Question, MultipleChoice
from app.extensions import db
from app.quiz import prep_multichoice, extract_answers

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

        answer_key, choices = prep_multichoice(questions) 
        
        for i, (key,data) in enumerate(answer_key.items()):
            assert q_ids[i] == data['id']

            possible_answers = choices[key]
            
            assert possible_answers[data['correct']] == questions[i].correct
            
            for idx in data['incorrect']:
                assert possible_answers[idx] in questions[i].incorrect

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
