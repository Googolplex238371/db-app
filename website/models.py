from . import db
from flask_login import UserMixin
from sqlalchemy.sql import func
import secrets
class Data(db.Model):
    apikey = db.Column(db.String,primary_key=True)
    columns = db.Column(db.String)
    name = db.Column(db.String)
    primary_key = db.Column(db.Integer)
    last_change = db.Column(db.String, default=func.now())
    data = db.Column(db.String)
    requests = db.Column(db.String)
    types = db.Column(db.String(100))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))
    data = db.relationship('Data')
    otp = db.Column(db.String(16),unique=True)
    verified = db.Column(db.Boolean)
    queries = db.relationship('Query')
class Query(db.Model):
    id = db.Column(db.String, primary_key=True,default=secrets.token_urlsafe(16))
    criteria = db.Column(db.String)
    apikey = db.Column(db.String)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    name = db.Column(db.String)
    data = db.Column(db.String)
