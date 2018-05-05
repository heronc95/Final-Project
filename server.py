from pymongo import MongoClient
import RPi.GPIO as GPIO
from hw_pins import hw_pins
import pika
import time
import pickle
from rmq_params import rmq_params, rmq_routing_keys




# setup the mongodb here
client = MongoClient('mongodb://localhost:27017/')

# Get the database to use for mongodb
db = client.hokie_id
collection = db.student_ids


# setup the rabbitMQ queues here

# The queue name that is appended with a number
order_base_queue_name = "order"
order_queue_num = 1

username = rmq_params["username"]
pword = rmq_params["password"]
ip_to_run = '0.0.0.0'
virtual_host = rmq_params["vhost"]
credentials = pika.PlainCredentials(username, pword)
parameters = pika.ConnectionParameters(host=ip_to_run, virtual_host=virtual_host, port=5672, credentials=credentials,
                                       socket_timeout=1000)
connection = pika.BlockingConnection(parameters)

print("[Checkpoint] Connected to vhost %s on RMQ server at %s as user %s" % (virtual_host, ip_to_run, username))

# Need to make the channel for the queues to talk through
channel = connection.channel()

print("[Checkpoint] Setting up exchanges and queues...")
# The server's job is to create the queues that are needed
channel.exchange_declare(rmq_params["exchange"], exchange_type='direct')

# make all the queues for the service
channel.queue_declare(rmq_params["valid_queue"],auto_delete=False)
channel.queue_declare(rmq_params["id_queue"], auto_delete=False)
channel.queue_declare(rmq_params["ffa_queue"], auto_delete=False)


channel.queue_bind(exchange=rmq_params["exchange"], queue=rmq_params["ffa_queue"], routing_key=rmq_routing_keys["ffa_queue"])
channel.queue_bind(exchange=rmq_params["exchange"], queue=rmq_params["id_queue"], routing_key=rmq_routing_keys["id_queue"])
channel.queue_bind(exchange=rmq_params["exchange"], queue=rmq_params["valid_queue"], routing_key=rmq_routing_keys["valid_queue"])


# Test the writing out here
channel.basic_publish(exchange=rmq_params["exchange"], routing_key=rmq_routing_keys["ffa_queue"], body="ffa queue!")
# Signal we have sent the order to the server
#channel.basic_publish(exchange=rmq_params["exchange"], routing_key=rmq_routing_keys["id_queue"], body='id queue!')



# Now stop and listen on the id queue
def callback(ch, method, properties, body):
    value = body.decode("utf-8")
    print("Received %s" % value)
    # Checks the mongodatabase
    # This should send it through a rabbitMQ message queue
    result = collection.find_one({'id': value})
    if result:
        reply = "valid"
    else:
        reply = "invalid"
    # Signal we have sent the order to the server
    ch.basic_publish(exchange=rmq_params["exchange"], routing_key=rmq_routing_keys["valid_queue"], body=reply)

# Need to make the channel for the queues to talk through
channel = connection.channel()
# Sets up the callback that is used
queue_name = rmq_params["id_queue"]
channel.basic_consume(callback, queue_name, no_ack=True)
print("[Checkpoint] Consuming from RMQ queue: %s" % queue_name)


# Start consuming the messages here
channel.start_consuming()
