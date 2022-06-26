from sqlalchemy.orm import with_polymorphic
from werkzeug.datastructures import ImmutableMultiDict

from app.models import Topic, Question, MultipleChoice
from app.quiz import prep_multichoice, extract_answers, score_input
from app.extensions import db

def test_prep_multichoice(app, db_questions):
    
    with app.app_context():
        
        polymap = with_polymorphic(Question, MultipleChoice)
        questions = db.session.query(polymap).all()
        q_ids = [q.id for q in questions]
        
        answer_key = prep_multichoice(questions) 
        
        for i,data in enumerate(answer_key):
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
        0 : '4',
        1 : '3'
    }

    answer_key = [{'correct_index' : 4},
                  {'correct_index' : 2}]

    score = score_input(user_answers, answer_key)

    assert score[0] == 'correct' and score[1] == 'incorrect'

def test_quiz_get(app, client, captured_templates, db_questions):
    
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
    q_ids = [q['id'] for q in context['questions']]
    
    for q in qlist:
        assert q.id in q_ids

def test_quiz_submit(app, client, captured_templates, db_questions):
    
    with app.app_context(): 
        qlist = db.session.query(Question)\
            .filter(Question.topics.any(Topic.name.in_(['Topic1','Topic2'])))\
            .all()
         
    form = {'q0' : '0' , 'q1': '3'}
    ans_key = [None] * len(qlist)
    
    #dummy data for choices since for this route, it only matters for display
    for n, q in enumerate(qlist):
        ans_key[n] = {'id' : q.id,
                      'text' : q.text,
                      'correct_index' : n,
                      'choices' : ['choice0', 'choice1', 'choice2']}
    
    with client.session_transaction() as session:
        session['question_ids'] = [q.id for q in qlist]
        session['block_size'] = len(qlist)
        session['answer_key'] = ans_key
    
    response = client.post('/submit', data=form)
    template, context = captured_templates[0]

    assert response.status_code == 200
    assert template.name == 'answerpage.html'
    assert 'results' in context and 'questions' in context

    assert context['questions'] == ans_key

    #for test, correct index was made equal to display index instead of random
    assert context['results'][0] == 'correct'
    assert context['results'][1] == 'incorrect'
