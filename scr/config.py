import os
basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = 'xx98cbd764a4fb7bfdc5895e2ae43xrfc'
    SQLALCHEMY_DATABASE_URI = (os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'bbntwitter.db'))+'?check_same_thread=False'
    SQLALCHEMY_TRACK_MODIFICATIONS = False




