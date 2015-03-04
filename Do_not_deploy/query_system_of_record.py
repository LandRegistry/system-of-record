from application.models import SignedTitles
from application import app
from application import db
from flask import request
import json
from kombu import Connection, Exchange, Queue, Consumer, eventloop



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


@app.route("/getlastrecord")
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


@app.route("/getnextqueuemessage")
#Gets the next message from target queue.  Returns the signed JSON.
def get_last_incoming_queue_message():
    #: By default messages sent to exchanges are persistent (delivery_mode=2),
    #: and queues and exchanges are durable.
    exchange = Exchange()
    connection = Connection(app.config['RABBIT_ENDPOINT'])

    # Create/access a queue bound to the connection.
    queue = Queue(app.config['RABBIT_QUEUE'],
                  exchange,
                  routing_key=app.config['RABBIT_ROUTING_KEY'])(connection)
    queue.declare()

    message = queue.get()

    if message:
        signature = message.body
        message.ack() #acknowledges message, ensuring its removal.
        return signature

    else:
        return "no message"

