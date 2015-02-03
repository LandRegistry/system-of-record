from application.models import SignedTitles
from application import app
from application import db
import json
from flask import request

@app.route("/")
def check_status():
    return "Everything is OK"


@app.route("/insert", methods=["POST"])
def insert():
    signed_title_json = request.get_json()
    signed_title_json_object = SignedTitles(signed_title_json)
    db.session.add(signed_title_json_object)
    db.session.commit()
    return "Test row inserted"





