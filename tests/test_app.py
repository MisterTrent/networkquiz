from werkzeug.datastructures import ImmutableMultiDict
from flask import session

from app.extensions import db
from app.models import Topic, Question, MultipleChoice
from app.home import generate_id_list, process_form

def test_config(app):
    '''Ensure proper configuration object used by app factory'''
     
    assert app.config.get('TESTING') is True

def test_home_route(app, client, db_questions, captured_templates):
    
    response = client.get('/')
    
    assert response.status_code == 200
    assert len(captured_templates) == 1

    template, context = captured_templates[0]

    assert template.name == 'index.html'
    assert 'Topic1' in context['quiz_topics']
    assert 'Topic2' in context['quiz_topics']

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

def test_quiz_setup_route(app, client, db_questions):
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

