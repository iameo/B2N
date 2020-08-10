from datetime import datetime
from . import db

class NlPost(db.Model):
    __tablename__ = 'nl_posts'
    id = db.Column(db.Integer, primary_key=True)
    #unix
    location = db.Column(db.String(120), unique=False, nullable=True)
    tweet = db.Column(db.String(1000), unique=False, nullable=True)

    def __repr__(self):
        return '<TWEET: %s>' % self.tweet[:40]
