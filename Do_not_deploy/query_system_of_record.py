from application.models import SignedTitles
from application import app
from application import db
from flask import request


@app.route("/")
def check_status():
    return "Tester is OK"


# @app.route("/insert", methods=["POST"])
# def insert():
#     signed_title_json = request.get_json()
#     signed_title_json_object = SignedTitles(signed_title_json)
#     db.session.add(signed_title_json_object)
#     db.session.commit()
#     return "row inserted"

#Add a route to return the json for a title so that the tests can confirm.gco master





