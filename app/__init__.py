from flask import Flask
import config
from .home import home_bp #TODO import inside app_context?
from .quiz import quiz_bp
from app.extensions import db, sess

def create_app(config_type = None):
    '''Application factory can take several possible configuration
    parameters: 'test', 
    '''
    
    config_str = config_type.title() + 'Config' if config_type else 'Config'
    config_obj = getattr(config, config_str)

    app = Flask(__name__)
    app.config.from_object(config_obj)

    db.init_app(app)
    sess.init_app(app)

    app.register_blueprint(home.home_bp)
    app.register_blueprint(quiz_bp)

    return app
