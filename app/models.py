from sqlalchemy import Table, Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

#Note: no cascade delete on either question or topic b/c they exist independent
#of one another. See: docs.sqlalchemy.org/en/14/orm/cascades.html#delete 
question_topic_association = Table(
            'question_topics', 
            Base.metadata,
            Column('question_id', ForeignKey('questions.id'), primary_key=True),
            Column('topic_id', ForeignKey('topics.id'), primary_key=True)
)

class Question(Base):
    '''"Supertype" table for all questions regardless of type. Necessary as
    each question type will have different styles of representing answers and
    prompts, but we want a single table for things such as question-topic 
    association.
    '''

    __tablename__ = 'questions'
    
    id = Column(Integer, primary_key=True)
    text = Column(String, nullable=False)
    qtype = Column(String, nullable=False)
    topics = relationship("Topic", 
                        secondary="question_topics",
                        back_populates="questions")

    __mapper_args__ = {
        'polymorphic_identity' : 'question',
        'polymorphic_on' : qtype
    }

class MultipleChoice(Question):
    '''Contains the specifics of a question with a multiple choice answer.

    "correct" and "incorrect" columns contain comma-separated lists of possible
    choices to prompt user with. Nothing in data structure enforces a min or 
    max number of correct answers.
    '''
    
    __tablename__ = 'multiple_choice'

    id = Column(Integer, ForeignKey('questions.id'), primary_key=True)
    
    correct = Column(String, nullable=False)
    incorrect = Column(String, nullable=False)

    __mapper_args__ = {
        'polymorphic_identity' : 'multiple_choice',
    }

class Topic(Base):
    '''Categories or topics a question may be tagged with.'''

    #TODO add "top level tag" attribute? E.g. broad topics vs specific ones

    __tablename__ = 'topics'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    questions = relationship("Question", 
                            secondary="question_topics",
                            back_populates="topics")
