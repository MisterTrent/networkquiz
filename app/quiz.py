from flask import Blueprint, session, render_template, abort, request
from sqlalchemy.orm import with_polymorphic
import re
import random
from app.extensions import db
from app.models import Topic, Question, MultipleChoice
import pytest

quiz_bp = Blueprint('quiz', __name__)

def prep_multichoice(qlist):
    '''Assigns a position for each correct answer in a list of multiple 
    choice questions.
    '''
    
    #keys for both are the question's index; index encoded in html attribute
    #for the form inputs and parsed upon submission to match w/ answer key
    answer_key = [None] * len(qlist)
   
    #random.shuffle's 'random' parameter deprecated, otherwise we could simply
    #shuffle all choices together AND rendering indices w/ the same seed param
    for q_idx, q in enumerate(qlist):

        orig_choices = q.incorrect.split(',')
        correct = q.correct
        orig_choices.append(correct)
        n_choices = len(orig_choices)
        
        idxs = list(range(n_choices))
        random.shuffle(idxs)
       
        answer_key[q_idx] = {'id' : q.id,
                            'text' : q.text,
                            'correct_index' : idxs[-1]}
        
        out_choices = [None]* (n_choices)
        for n,i in enumerate(idxs):
            out_choices[i] = orig_choices[n]
        
        answer_key[q_idx]['choices'] = out_choices

    return answer_key

def score_input(user_answers, answer_key):
    '''Compares input with the key created at time of quiz round's generation
    '''
    score = {}
    for q_idx, value in user_answers.items():
        correct_idx = answer_key[q_idx]['correct_index']
        
        #check for errors/user tampering with value attribute of input
        choice_idx = int(value) if value.isdigit() else None
        score[q_idx] = 'correct' if choice_idx == correct_idx else 'incorrect'

    return score

def extract_answers(form):
    '''Gets only the answer inputs from the user's quiz form which may have
    other fields (e.g. csrf). Question input "name" html attribute expected
    to have the form of "q##" where ## is the question's index in this round
    as stored in session.
    '''
   
    #very basic regex to discard unnecessary fields TODO detect user tampering
    rgx = r"(\d+)"    
    is_question = lambda k : len(k) == 3 and k[0] == 'q' \
                            and k[1].isdigit() and k[2] == ''
    
    answers = {}
    
    for k,v in form.items():
        split_key = re.split(rgx, k)
        if is_question(split_key):
           answers[int(split_key[1])] = v 

    return answers

@quiz_bp.route('/submit', methods=['POST'])
def question_submit():
    '''Processes a round of quiz questions to compare user input with
    questions' answers.
    '''
    try:
        form = request.form
    except:
        abort(400)
    
    user_answers = extract_answers(form)
    results = score_input(user_answers, session['answer_key'])

    return render_template('answerpage.html', results=results,
                                            questions=session['answer_key'])

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
    
    answer_key = prep_multichoice(questions)
    
    #remove already-asked questions
    session['question_ids'] = session['question_ids'][:-n or None]
    
    #store active questions for scoring user answers and displaying results
    session['answer_key'] = answer_key
    
    #TODO end quiz if not enough available? Indicate end in jinja context to display?

    return render_template('quiz.html', 
                                questions=answer_key)
