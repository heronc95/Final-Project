from evdev import InputDevice, categorize, ecodes, KeyEvent
from pymongo import MongoClient
import RPi.GPIO as GPIO
from hw_pins import hw_pins
import pika
import time
import pickle
import threading
import argparse
from rmq_params import rmq_params, rmq_routing_keys



parser = argparse.ArgumentParser()
parser.add_argument("-s", "--RABBIT_MQ_ADDR", help="This is the address of the rabbitMQ instance that is running", type=str)

# This gets the arguments from the user, access them through SERVER_PORT, etc
args = parser.parse_args()




# setup the GPIO
GPIO.setmode(hw_pins['mode'])
GPIO.setup(hw_pins['red'], GPIO.OUT)
GPIO.setup(hw_pins['powerstrip'], GPIO.OUT)
GPIO.setup(hw_pins['green'], GPIO.OUT)
GPIO.setup(hw_pins['yellow'], GPIO.OUT)
GPIO.output(hw_pins['green'], False)
GPIO.output(hw_pins['red'], True)
GPIO.output(hw_pins['powerstrip'], False)

number = ""
# This is the function that listens to swipes and then sends them to the main user
def swipe_listener():
    global number
    device = InputDevice("/dev/input/event0") # my keyboard
    # The global variable that holds the number to read from
    while 1:
        done = False
        enter_count = 0
        print("Here")
        updating = False
        for event in device.read_loop():
            print("Here 2")
            if not updating:
                number = ""
            # Event is an inputEvent, which is not iterable
            if event.type == ecodes.EV_KEY:
                category_string = str(categorize(event))
                print(category_string)
                # parse the raw input data to get the information we want from the device
                elem = category_string.strip(" ").split(",")
                # loop through the list finding the numbers that I want

                # pull the last number from the value to see if it is a number
                s = elem[1]
                key_val = s[s.find("(")+1:s.find(")")]
                t = key_val[-1]

                if done == False and t.isdigit() and  "down" not in elem[2]:
                    # then we know it is a hokie p number
                    number += str(t)
                    updating = True
                elif key_val == "KEY_EQUAL":
                    # Leave the loop if this happens
                    done = True
                elif key_val == "KEY_ENTER":
                    enter_count += 1
                    if enter_count == 2:
                        break
        print(number)
        updating = False


def echo_current_number(addr):
    global number
    username = rmq_params["username"]
    pword = rmq_params["password"]
    virtual_host= rmq_params["vhost"]

    ip_addr_for_rmq = addr

    credentials = pika.PlainCredentials(username, pword)
    parameters = pika.ConnectionParameters(host=ip_addr_for_rmq, virtual_host=virtual_host, port=5672, credentials=credentials, socket_timeout=1000)
    connection = pika.BlockingConnection(parameters)

    ch = connection.channel()
    # setup RMQ stuff here 
    while 1:
        print("Sending the number now " + str(number))
        # Write the number to the server here
        ch.basic_publish(exchange=rmq_params["exchange"], routing_key=rmq_routing_keys["id_queue"], body=str(number))
        time.sleep(.1)





# This is the callback for the valid queue. Writes to the hardware devices
def callback(ch, method, properties, body):
    good = False
    if all(v is not None for v in [ch, method, properties, body]):
        good = True
    if not good:
        print("Something weird happened here")
        while 1:
            x = 0
        return 

    value = body.decode("utf-8")
    print("Received %s" % value)
    if value == "good":
        GPIO.output(hw_pins['green'], True)
        GPIO.output(hw_pins['powerstrip'], True)
        GPIO.output(hw_pins['red'], False)
        GPIO.output(hw_pins['yellow'], False)
        # turn on led and the power strip here
        print("Access allowed")

    elif value == "almost":
        GPIO.output(hw_pins['green'], False)
        GPIO.output(hw_pins['powerstrip'], True)
        GPIO.output(hw_pins['red'], False)
        GPIO.output(hw_pins['yellow'], True)
    elif value == "no":
        GPIO.output(hw_pins['green'], False)
        GPIO.output(hw_pins['powerstrip'], False)
        GPIO.output(hw_pins['red'], True)
        GPIO.output(hw_pins['yellow'], False)
        # turn on the LEDS here 
        print("Wasnt in there")



username = rmq_params["username"]
pword = rmq_params["password"]
virtual_host= rmq_params["vhost"]

ip_addr_for_rmq = str(args.RABBIT_MQ_ADDR)

credentials = pika.PlainCredentials(username, pword)
parameters = pika.ConnectionParameters(host=ip_addr_for_rmq, virtual_host=virtual_host, port=5672, credentials=credentials,  socket_timeout=1000)
connection = pika.BlockingConnection(parameters)





# Need to make the channel for the queues to talk through
channel = connection.channel()
channel.queue_declare(rmq_params["id_queue"], auto_delete=False)



# Sets up the callback that is used
queue_name = rmq_params["valid_queue"]
channel.basic_consume(callback, queue_name, no_ack=True)

print("[Checkpoint] Consuming from RMQ queue: %s" % queue_name)
t = threading.Thread(name='my_listener', target=swipe_listener)
t.start()

echoer = threading.Thread(name='number_shouter', target=echo_current_number, args=(str(args.RABBIT_MQ_ADDR),))
echoer.start()
try:
    # Start consuming the messages here
    channel.start_consuming()
except KeyboardInterrupt:
    GPIO.output(hw_pins['green'], False)
    GPIO.output(hw_pins['powerstrip'], False)
    GPIO.output(hw_pins['red'], False)
    GPIO.output(hw_pins['yellow'], False)
    t.join()
    echoer.join()


