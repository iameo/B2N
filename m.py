from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, String
from flask_migrate import Migrate
from .config import Config



engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
# db = SQLAlchemy()

def create_app():
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object('config.Config')
    db.init_app(app)
    migrate = Migrate(app)

    with app.app_context():

        # db.create_all()
        return app

