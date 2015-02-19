from application.models import SignedTitles
from application import app
from application import db
from flask import request
import json



@app.route("/")
def check_status():
    return "Tester is OK"


@app.route("/count")
def count_rows():
    the_count = db.session.query(SignedTitles).count()
    return str(the_count)


@app.route("/deletelastrecord")
def delete_last_record():
    last_record = get_last_record()
    db.session.delete(last_record)
    db.session.commit()
    return 'deleted'


@app.route("/getlastsignature")
def get_last_signature():
    last_record = get_last_record()
    #convert the sor dictionary to a string
    sor_as_string = json.dumps(last_record.sor)
    return sor_as_string


def get_last_record():
    #Returns an instance of SignedTitles, the last one in the table
    return db.session.query(SignedTitles).order_by(SignedTitles.id.desc()).first()


def query_nested_stuff_like_this():
    signed_titles_instance = db.session.query(SignedTitles).first()
    a_dict = signed_titles_instance.sor
    my_element = a_dict['data']['titleno']
    return my_element


def query_by_an_id_like_this(the_id):
    athing = db.session.query(SignedTitles).get(the_id)
    return athing


