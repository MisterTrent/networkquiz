from flask import Blueprint, render_template, abort, session, request
from app.extensions import db
from app.models import Topic, Question
import json
import random

home_bp = Blueprint('home', __name__)

def get_topics():
    #TODO only return those associated with 1+ questions?
    results = db.session.query(Topic).all()
    return [r.name for r in results]

def process_form(form):
    ''' Extracts quiz setup info from form.'''

    #TODO add processing for question styles, special quizzes (e.g.
    #acronym test), etc. parsed from the form field 'name' attribute
    
    #TODO log any 'misses' as user probably manipulated form client side
    topics = get_topics() 
    selected = [k for k in form.keys() if k in topics]
    
    return selected

def generate_id_list(topiclist, randomize = False):
    '''Finds all questions matching user settings and creates randomized
    ordering for future queries by primary key in blocks of a predetermined
    size.
    '''
   
    #stackoverflow.com/questions/6474989
    result = db.session.query(Question.id)\
                .filter(Question.topics.any(Topic.name.in_(topiclist)))\
                .all()
    
    if len(result) < 1:
        return [] 
    
    _ids = [v[0] for v in result] 

    if randomize is True:
        random.shuffle(_ids)

    return _ids 

@home_bp.route('/quiz', methods=['POST'])
def quiz_setup():
    '''Receives form with user's quiz settings/preferences and stores in a 
    session for use between quiz 'rounds' (which are separate requests).
    '''
    
    session.clear() 
    
    try:
        form = request.form 
        topics = process_form(form)
    
        #TODO validation error or 400? blank submission should be OK client side
        if len(topics) == 0:
            abort(400)

    except:
        abort(400)

    session['question_ids'] = generate_id_list(topics)

    return render_template('quiz.html')

@home_bp.route('/')
def index():
    topics = get_topics()
    
    return render_template('index.html', quiz_topics = topics)
