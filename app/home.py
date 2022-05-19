from flask import Blueprint, render_template
from app.extensions import db
from app.models import Topic

home_bp = Blueprint('home', __name__)

def get_topics():
    #TODO only return those associated with 1+ questions?
    results = db.session.query(Topic).all()
    return [r.name for r in results]

@home_bp.route('/')
def index():
    topics = get_topics()
    return render_template('index.html', quiz_topics = topics)
