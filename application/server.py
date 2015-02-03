from application.models import SignedTitles
from application import app
from application import db
import json
from flask import request

@app.route("/")
def check_status():
    return "Everything is OK"

@app.route("/testinsert")
def test_insert():
    json_data = {"key1": "value1", "key2": "value2"}
    test_row = SignedTitles(json_data)
    db.session.add(test_row)
    db.session.commit()
    return "Test row inserted"

@app.route("/insert", methods=["POST"])
def insert():
    signed_title_json = request.get_json()
    signed_title_json_object = SignedTitles(signed_title_json)
    db.session.add(signed_title_json_object)
    db.session.commit()
    return "Test row inserted"


#curl -X POST -d '{"titleno" : "DN1"}' -H "Content-Type: application/json" http://0.0.0.0:5000/insert


