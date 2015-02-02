from flask import Flask, request
import os
from flask.ext.sqlalchemy import SQLAlchemy
import json

app = Flask(__name__)
app.config.from_object(os.environ.get('SETTINGS'))
db = SQLAlchemy(app)

@app.route("/")
def check_status():
    return "Everything is OK"



