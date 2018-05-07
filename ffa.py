import RPi.GPIO as GPIO                           #Import GPIO library
import time                                       #Import time library
from hw_pins import hw_pins
import RPi.GPIO as GPIO
from hw_pins import hw_pins
from rmq_params import rmq_params, rmq_routing_keys
import argparse
import pika
import pickle
parser = argparse.ArgumentParser()
parser.add_argument("-s", "--RABBIT_MQ_ADDR", help="This is the address of the rabbitMQ instance that is running", type=str)

# This gets the arguments from the user, access them through SERVER_PORT, etc
args = parser.parse_args()

username = rmq_params["username"]
pword = rmq_params["password"]
virtual_host= rmq_params["vhost"]

ip_addr_for_rmq = str(args.RABBIT_MQ_ADDR)

credentials = pika.PlainCredentials(username, pword)
parameters = pika.ConnectionParameters(host=ip_addr_for_rmq, virtual_host=virtual_host, port=5672, credentials=credentials,  socket_timeout=1000)
connection = pika.BlockingConnection(parameters)


# Need to make the channel for the queues to talk through
channel = connection.channel()

print("[Checkpoint] Setting up exchanges and queues...")
# The server's job is to create the queues that are needed
channel.exchange_declare(rmq_params["exchange"], exchange_type='direct')

# make all the queues for the service


# Need to make the channel for the queues to talk through
ch = connection.channel()
# Sets up the callback that is used
queue_name = rmq_params["ffa_queue"]


# setup the GPIO
GPIO.setmode(hw_pins['mode'])
GPIO.setup(hw_pins['pir'], GPIO.IN)                          #Set pin as GPIO in 

# setup the GPIO
GPIO.setup(hw_pins['red'], GPIO.OUT)
GPIO.setup(hw_pins['green'], GPIO.OUT)

GPIO.output(hw_pins['green'], False)
GPIO.output(hw_pins['red'], False)


print("Waiting for sensor to settle")
time.sleep(2)                                     #Waiting 2 seconds for the sensor to initiate

state = "no"
#setup the rmq device now
print("Detecting motion")
nos = 0
GPIO.output(hw_pins['green'], False)
GPIO.output(hw_pins['red'], True)

while True:
    if state == "no" and GPIO.input(hw_pins['pir']):                            #Check whether pir is HIGH
        state = "yes"    
        GPIO.output(hw_pins['green'], True)
        GPIO.output(hw_pins['red'], False)
        print("Motion Detected!")
        time.sleep(2)                               #D1- Delay to avoid multiple detection
    elif state == "yes" and GPIO.input(hw_pins['pir']) == 0:
        nos += 1
        if nos > 0:
            state = "no"
            nos = 0
            GPIO.output(hw_pins['green'], False)
            GPIO.output(hw_pins['red'], True)
    time.sleep(0.1)                                #While loop delay should be less than detection(hardware) delay
    print("sending: " + str(state))
    ch.basic_publish(exchange=rmq_params["exchange"], routing_key=rmq_routing_keys["ffa_queue"], body=state)





