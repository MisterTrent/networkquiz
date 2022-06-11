from flask import Blueprint, session, render_template
from sqlalchemy.orm import with_polymorphic
from app.extensions import db
from app.models import Topic, Question, MultipleChoice

import pytest

quiz_bp = Blueprint('quiz', __name__)

@quiz_bp.route('/submit', methods=['POST'])
def question_submit():
    pass

@quiz_bp.route('/get', methods=['GET'])
def get_questions():
    '''Loads a round of questions based on user's current 
    selected topics.
    '''
    #TODO system controlling access only from form in quiz and one at a time
    #eg. csrf validation  
    try:
        idlist = session['question_ids']
    except:
        abort(400) 
    
    n = session['block_size']
    q_ids = idlist[-n:]
    
    #TODO using in_ vs a join; does it matter w/ sqla a/o our db of choice?
    polymap = with_polymorphic(Question, MultipleChoice)
    questions = db.session.query(polymap)\
                    .filter(Question.id.in_(q_ids))\
                    .all()
    
    #TODO end quiz if not enough available? Indicate end in jinja context to display?

    return render_template('quiz.html', questions = questions)
