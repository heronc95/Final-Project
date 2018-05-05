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


# This is the function that listens to swipes and then sends them to the main user
def swipe_listener(ch):

    device = InputDevice("/dev/input/event0") # my keyboard
    # The global variable that holds the number to read from
    while 1:
        number = ""
        done = False
        enter_count = 0
        print("Here")
        
        for event in device.read_loop():
            print("Here 2")
            # Event is an inputEvent, which is not iterable
            if  event.type == ecodes.EV_KEY:
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
                    #print("THe number I got was: " + number)
                elif key_val == "KEY_EQUAL":
                    # Leave the loop if this happens
                    done = True
                elif key_val == "KEY_ENTER":
                    enter_count += 1
                    if enter_count == 2:
                        break
        print(number)
        # Write the number to the server here
        ch.basic_publish(exchange=rmq_params["exchange"], routing_key=rmq_routing_keys["id_queue"], body=str(number))




# This is the callback for the valid queue. Writes to the hardware devices
def callback(ch, method, properties, body):
    value = body.decode("utf-8")
    print("Received %s" % value)
    if value == "valid":
        GPIO.output(hw_pins['green'], True)
        GPIO.output(hw_pins['powerstrip'], True)
        GPIO.output(hw_pins['red'], False)
        # turn on led and the power strip here
        print("Access allowed")

    else:
        GPIO.output(hw_pins['green'], False)
        GPIO.output(hw_pins['powerstrip'], False)
        GPIO.output(hw_pins['red'], True)
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
# Sets up the callback that is used
queue_name = rmq_params["valid_queue"]
channel.basic_consume(callback, queue_name, no_ack=True)

print("[Checkpoint] Consuming from RMQ queue: %s" % queue_name)
t = threading.Thread(name='my_listener', target=swipe_listener, args=(channel,))
t.start()

try:
    # Start consuming the messages here
    channel.start_consuming()
except KeyboardInterrupt:
    GPIO.output(hw_pins['green'], False)
    GPIO.output(hw_pins['powerstrip'], False)
    GPIO.output(hw_pins['red'], False)
    t.join()
