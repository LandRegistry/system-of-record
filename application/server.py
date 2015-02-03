from application.models import SignedTitles
from application import app
from application import db
import json

@app.route("/")
def check_status():
    return "Everything is OK"

@app.route("/insert")
def check_insert():
    json_data = {"key1": "value1", "key2": "value2"}
    test_row = SignedTitles(json_data)
    db.session.add(test_row)
    db.session.commit()
    return "Test row inserted"



