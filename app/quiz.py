from flask import Blueprint
from app.extensions import db
from app.models import 

quiz_bp = Blueprint('quiz', __name__)

@quiz_bp.route('/submit', methods=['POST'])
def question_submit():
    pass

@quiz_bp.route('/get', methods=['GET'])
def get_questions():
    ''' Loads a round of questions based on user's current selected
    topics.
    '''
    pass

