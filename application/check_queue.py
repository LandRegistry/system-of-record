"""
Example of simple consumer that waits for a single message, acknowledges it
and exits.

Run this to check that server.py has successully submitted to the queue,
"""
from kombu import Connection, Exchange, Queue, Consumer, eventloop
from pprint import pformat

#: By default messages sent to exchanges are persistent (delivery_mode=2),
#: and queues and exchanges are durable.
exchange = Exchange()
connection = Connection('amqp://guest:guest@localhost:5672//')

# Create (if necessary) a queue bound to the connection.
queue = Queue('system_of_record', exchange, routing_key='system_of_record')(connection)
queue.declare()


def pretty(obj):
    return pformat(obj, indent=4)

#: This is the callback applied when a message is received.
def handle_message(body, message):
    print('Received message: %r' % (body, ))
    print(' properties:\n%s' % (pretty(message.properties), ))
    print(' delivery_info:\n%s' % (pretty(message.delivery_info), ))
    message.ack()

message = queue.get()

if message:
    handle_message(message.body, message)
