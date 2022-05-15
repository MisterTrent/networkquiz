#3rd party imports
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

#local app imports
from app.models import Base, Question, MultipleChoice, Topic, question_topic_association

#TODO temp postgres db? Make choice of db a runtime option?
engine = create_engine("sqlite://", echo=True)
Session = sessionmaker()

@pytest.fixture(scope='module')
def connection():
    '''One connection per testing run'''
    
    connection = engine.connect()
    yield connection
    connection.close()

@pytest.fixture(scope='function')
def session(connection):
    
    transaction = connection.begin()
    Base.metadata.create_all(engine)
    session = Session(bind=connection)
    yield session
    session.close()
    transaction.rollback()

def test_multiple_choice_null_exception(session):
    '''Test creation of multiple choice question w/ omitted required fields.'''
    
    #missing fields required by base type
    with pytest.raises(SQLAlchemyError):
        
        question = MultipleChoice(
           correct = 'correct answer',
           incorrect = 'incorrect answer'
        )
        
        session.add(question)
        session.commit()
    
    #missing fields required by polymorphic subtype table
    with pytest.raises(SQLAlchemyError):

        question = MultipleChoice(
            text="test question text",
            qtype="multiple_choice"
        )
        
        session.add(question)
        session.commit()

def test_multiple_choice(session):
    '''Tests for correct insertion of MultipleChoice Question into db'''
    
    data = {
        'text' : 'test text',
        'qtype' : 'multiple_choice',
        'correct' : 'correct answer',
        'incorrect' : 'incorrect answer'
    }
    
    question = MultipleChoice(**data)

    session.add(question)
    session.commit()

    qresult = session.query(MultipleChoice).one()
    
    #TODO better model instance equivalence testing?
    assert qresult.text == data['text']
    assert qresult.qtype == data['qtype']
    assert qresult.correct == data['correct']
    assert qresult.incorrect == data['incorrect']

def test_topic_basic(session):
    '''Creation of a topic tag entry without any added relationships'''

    tag = Topic(name = "topic1")

    session.add(tag)
    session.commit()
    
    qresult = session.query(Topic).one()

    assert qresult.name == "topic1"

def test_question_topic_relationship(session):
   
    tag = Topic(name = "topic1")

    session.add(tag)
    session.commit()

    question_data = {
        'text' : 'test text',
        'qtype' : 'multiple_choice',
        'correct' : 'correct answer',
        'incorrect' : 'incorrect answer'
    }
    
    question = MultipleChoice(**question_data)
    question.topics.append(tag)

    session.add(question)
    session.commit()
    
    #TODO better/best way to query the m2m relationship? Maybe join or filter?
    qresult = session.query(question_topic_association).one()
    
    assert qresult.question_id == question.id
    assert qresult.topic_id == tag.id 
