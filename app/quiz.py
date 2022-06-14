from flask import Blueprint, session, render_template
from sqlalchemy.orm import with_polymorphic
import re
from app.extensions import db
from app.models import Topic, Question, MultipleChoice

quiz_bp = Blueprint('quiz', __name__)

def prep_multichoice(qlist):
    '''Assigns a position for each correct answer in a list of multiple 
    choice questions.
    '''
    
    #keys for both are the question's index; index encoded in html attribute
    #for the form inputs and parsed upon submission to match w/ answer key
    answer_key = {}
    choices = {}
   
    #random.shuffle's 'random' parameter deprecated, otherwise we could simply
    #shuffle all choices together AND rendering indices w/ the same seed param
    for qnum, q in enumerate(qlist):

        incorrect = q.incorrect.split(',')
        correct = q.correct
        both = incorrect.append(correct)
        
        n_choices = len(both)
        idxs = random.shuffle(list(range(n_choices)))
        
        answer_key[qnum] = {'id' : q.id,
                            'correct_index' : idxs[-1],
                            'incorrect_indices' : idxs[:-1]}
        
        choices[qnum] = [None]* (n_choices)
         
        for n,i in enumerate(idxs):
            choices[qnum][i] = both[n]
    
    return answer_key, choices

def score_input(user_answers, answer_key):
    '''Compares input with the key created at time of quiz round's generation
    '''
    answer_key = session['answer_key']
    score = {}

    for _id, choice in user_answers.items():
        correct_index = answer_key[_id]['correct_index']
        score[_id] = 'correct' if choice == correct_index else 'incorrect'

    return score

def extract_answers(form):
    '''Gets only the answer inputs from the user's quiz form which may have
    other fields (e.g. csrf). Question input "name" html attribute expected
    to have the form of "q##" where ## is the question's index in this round
    as stored in session.
    '''
   
    #very basic regex to discard unnecessary fields TODO detect user tampering
    rgx = '(\d+)'    
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
    
    idlist = session['active_questions']
    polymap = with_polymorphic(Question, MultipleChoice)
    questions = db.session.query(polymap)\
                    .filter(Question.id.in_(q_ids))\
                    .all()
    
    answers = extract_answers(form)
    results = score_input(answers, questions) 
    
    return render_template('answerpage.html', results = results)

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

    answer_key, questions = prep_multichoice(questions)

    session['active_questions'] = q_ids
    session['question_ids'] = session['question_ids'][:-n or None]
    session['answer_key'] = answer_key
    
    #TODO end quiz if not enough available? Indicate end in jinja context to display?

    return render_template('quiz.html', 
                                questions=questions, 
                                answer_key=answer_key)
