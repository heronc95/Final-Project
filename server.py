from pymongo import MongoClient
import RPi.GPIO as GPIO
from hw_pins import hw_pins
import threading
import socket
import pika
import time
import pickle
from rmq_params import rmq_params, rmq_routing_keys
import pytz
from datetime import datetime




current_id = None
def get_current_time():
    tz = pytz.timezone('US/Eastern')
    current_time = datetime.now(tz)
    current_time = current_time.strftime("%m-%d-%H-%M")
    return current_time


def is_valid_time(start_time, end_time, given):
    """
    This parses the hours from the given range that was input
    :param start_time:
    :param end_time:
    :param given:
    :return:
    """

    # get starting times
    start_hour = int(start_time.split("-")[2])
    start_minute = int(start_time.split("-")[3])

    # get ending times
    end_hour = int(end_time.split("-")[2])
    end_minute = int(end_time.split("-")[3])

    # get the current time
    cur_hour = int(given.split("-")[2])
    cur_minute = int(given.split("-")[3])

    # now compare the values to see if it is time for them
    if cur_hour >= start_hour:
        # compare to see if it is within 15 mins of ending
        time_left = (end_hour - cur_hour) * 60 + (end_minute - cur_minute)
        if time_left <= 0:
            return "no" 
        print(time_left)
        if time_left < 15:
            print("Warn the user time is almost up.")
            return "almost"
        else:
            print("say the user is good now")
            return "good"
    else:
        print("say the user is not good.")
        return "no"





# setup the mongodb here
client = MongoClient('mongodb://localhost:27017/')

# Get the database to use for mongodb
db = client.hokie_id
collection = db.student_ids


def setup_rmq():

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
    print("[Checkpoint] Connected to vhost %s on RMQ server at %s as user %s" % (virtual_host, ip_to_run, username))
    return channel

def listen_for_times_to_enter(): 
    print("RUnning socket boi")
    TCP_IP = '0.0.0.0'
    TCP_PORT = 6969
    BUFFER_SIZE = 1024  # Normally 1024, but we want fast response

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((TCP_IP, TCP_PORT))
    s.listen(1)
    while 1:
        conn, addr = s.accept()
        print('Connection address:', addr)
        while 1:


            data = conn.recv(BUFFER_SIZE)

            if not data: 
                break
            data = data.decode('utf-8')
            print("received data:", data)

            data = data.split(",")
            id = data[0]
            start_time = data[1]
            end_time = data[2]
            to_insert = {"id": id, "start_time": start_time, "end_time": end_time}
            print("I'm inserting this: " + str(to_insert))
            # Remove all the others from the database here
            result = collection.delete_many({'id':id})

            # now insert my thing above
            collection.insert_one(to_insert)
            print("Just inserted it")

        conn.close()



count = 0
def motion_handler():
    # Need to make the channel for the queues to talk through
    channel = setup_rmq()

    # Now stop and listen on the id queue
    def motion_callback(ch, method, properties, body):
        # slow down the socket conneciton
        global count
        count += 1
        if count <= 10:
            return
        count = 0
        value = body.decode("utf-8")
        print("Received %s" % value)
        # Now send it to the server here
        TCP_IP = '0.0.0.0'
        TCP_PORT = 9696
        BUFFER_SIZE = 1024
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        MESSAGE = value
        print("sending: " + MESSAGE)

        s.connect((TCP_IP, TCP_PORT))
        s.send(MESSAGE.encode())
        s.close()
        print("Done") 
    # Sets up the callback that is used
    queue_name = rmq_params["ffa_queue"]
    channel.basic_consume(motion_callback, queue_name, no_ack=True)
    print("[Checkpoint] Consuming from RMQ queue: %s" % queue_name)

    # Start consuming the messages here
    channel.start_consuming()


def time_watcher():
    global current_id
    channel = setup_rmq()

    while 1:
        # sleep for a second
        time.sleep(1)
        print("Checking")
        # if nobody has claimed the spot yet, don't need to do anything
        if current_id == None:
            continue
        result = collection.find_one({'id': current_id})
        if result:
            print("Id is not updated")
            cur = get_current_time()
            start = result['start_time']
            end = result['end_time']
            response = is_valid_time(start, end, cur)

        else:
            # make the current time slot available
            response = "no"
        # make the response a no
        if response == "no":
            current_id = None
        # Signal we have sent the order to the server
        channel.basic_publish(exchange=rmq_params["exchange"], routing_key=rmq_routing_keys["valid_queue"], body=response)

def reserver_thread():
    # Need to make the channel for the queues to talk through
    channel = setup_rmq()
    # Now stop and listen on the id queue
    def callback(ch, method, properties, body):
        global current_id
        value = body.decode("utf-8")
        print("Received %s" % value)
        # Checks the mongodatabase
        # This should send it through a rabbitMQ message queue
        result = collection.find_one({'id': value})
        # makes sure the right person is accessing, and that the current person still has it reserved
        #if result and not current_id:
        if result:
            current_id = value
            cur = get_current_time()
            start = result['start_time']
            end = result['end_time']
            response = is_valid_time(start, end, cur)
        else:
            #current_id = None
            response = "no"
        # Signal we have sent the order to the server
        ch.basic_publish(exchange=rmq_params["exchange"], routing_key=rmq_routing_keys["valid_queue"], body=response)



    # Sets up the callback that is used
    queue_name = rmq_params["id_queue"]
    channel.basic_consume(callback, queue_name, no_ack=True)
    print("[Checkpoint] Consuming from RMQ queue: %s" % queue_name)




    # Start consuming the messages here
    channel.start_consuming()







# now start two threads and pass the channel onto them so they can start listening on them

rt = threading.Thread(name='reserve', target=reserver_thread)
rt.start()

mt = threading.Thread(name='motion', target=motion_handler)
mt.start()

sockme = threading.Thread(name='mongo_enterer', target= listen_for_times_to_enter)
sockme.start()
#timer = threading.Thread(name='timer', target=time_watcher)
#timer.start()
