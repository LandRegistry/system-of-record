from application.models import SignedTitles
from Do_not_deploy import app
from Do_not_deploy import db
import logging
import json


@app.route("/")
def check_status():
    return "Tester is OK"


@app.route("/count")
def count_rows():
    the_count = db.session.query(SignedTitles).count()
    return str(the_count)


@app.route("/deletelastrecord")
#Raises SQLAlchemy UnmappedInstanceError if no row found
def delete_last_record():
    try:
        last_record = get_last_record()
        db.session.delete(last_record)
        db.session.commit()
        return 'deleted'
    except:
        return 'failed'

@app.route("/getlastrecord")
def get_last_signature():
    try:
        last_record = get_last_record()
        #convert the sor dictionary to a string
        sor_as_string = json.dumps(last_record.record)
        return sor_as_string
    except AttributeError:
        return "No row found", 404

@app.route("/deleteallrecords")
def delete_all_records():
    while True:
        if delete_last_record() != 'deleted':
            break
    db.engine.execute("ALTER SEQUENCE sor_id_seq RESTART WITH 1;")
    return 'deleted', 202


def get_last_record():
    #Returns an instance of SignedTitles, the last one in the table
    return db.session.query(SignedTitles).order_by(SignedTitles.id.desc()).first()


def query_nested_stuff_like_this():
    signed_titles_instance = db.session.query(SignedTitles).first()
    a_dict = signed_titles_instance.record
    my_element = a_dict['data']['title_number']
    return my_element


def query_by_an_id_like_this(the_id):
    athing = db.session.query(SignedTitles).get(the_id)
    return athing
