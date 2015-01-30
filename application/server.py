from flask import Flask, request
import os
import json
from flask.ext.pymongo import PyMongo

app = Flask(__name__)
mongo = PyMongo(app)

@app.route("/")
def check_status():
    return "Everything is OK"



