from kombu import Connection, Exchange, Queue
from flask import Flask
import os

app = Flask(__name__)
app.config.from_object(os.environ.get('SETTINGS'))


# env_endpoint = app.config['REPUBLISH_EVERYTHING_ENDPOINT']
# env_queue = app.config['REPUBLISH_EVERYTHING_QUEUE']

env_endpoint = app.config['RABBIT_ENDPOINT']
env_queue = app.config['RABBIT_QUEUE']

#: By default messages sent to exchanges are persistent (delivery_mode=2),
#: and queues and exchanges are durable.
exchange = Exchange()
connection = Connection(env_endpoint)

# Create/access a queue bound to the connection.
queue = Queue(env_queue, exchange, routing_key=env_queue)(connection)
queue.declare()


@app.route("/getnextqueuemessage")
#Gets the next message from target queue.  Returns the signed JSON.
def get_last_queue_message():
    message = queue.get()

    if message:
        signature = message.body
        message.ack() #acknowledges message, ensuring its removal.
        return signature
    else:
        return "no message", 404



@app.route("/removeallmessages")
#Gets the next message from target queue.  Returns the signed JSON.
def remove_all_messages():
    while True:
        message = queue.get()
        if message:
            message.ack() #acknowledges message, ensuring its removal.
        else:
            break
    return "done", 202


@app.route("/")
def check_status():
    return "Everything is OK"

