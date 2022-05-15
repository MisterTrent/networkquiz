from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import config
from .home import home_bp #TODO import inside app_context?

db = SQLAlchemy()

def create_app(config_type = None):
    '''Application factory can take several possible configuration
    parameters: 'test', 
    '''
    
    config_str = config_type.title() + 'Config' if config_type else 'Config'
    config_obj = getattr(config, config_str)

    app = Flask(__name__)
    app.config.from_object(config_obj)

    db.init_app(app)

    app.register_blueprint(home.home_bp)

    return app
