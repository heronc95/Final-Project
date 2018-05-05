from evdev import InputDevice, categorize, ecodes, KeyEvent
from pymongo import MongoClient
import RPi.GPIO as GPIO
from hw_pins import hw_pins


device = InputDevice("/dev/input/event0") # my keyboard


# setup the mongodb here
client = MongoClient('mongodb://localhost:27017/')

# Get the database to use
db = client.hokie_id
collection = db.student_ids

# setup the GPIO
GPIO.setmode(hw_pins['mode'])
GPIO.setup(hw_pins['red'], GPIO.OUT)
GPIO.setup(hw_pins['powerstrip'], GPIO.OUT)
GPIO.setup(hw_pins['green'], GPIO.OUT)


GPIO.output(hw_pins['green'], False)
GPIO.output(hw_pins['red'], False)
GPIO.output(hw_pins['powerstrip'], False)




# The global variable that holds the number to read from
number = ""
for event in device.read_loop():
    # Event is an inputEvent, which is not iterable
    if event.type == ecodes.EV_KEY:
        category_string = str(categorize(event))
        # parse the raw input data to get the information we want from the device
        elem = category_string.strip(" ").split(",")
        # loop through the list finding the numbers that I want 

        # pull the last number from the value to see if it is a number
        s = elem[1]
        key_val = s[s.find("(")+1:s.find(")")]
        t = key_val[-1]

        #print("Here: " + str(elem))
        if t.isdigit() and  "down" not in elem[2]:
            # then we know it is a hokie p number
            number += str(t)
            #print("THe number I got was: " + number)
        elif key_val == "KEY_EQUAL":
            # Leave the loop if this happens
            break
print(number)
#number = "96501243"

# This should send it through a rabbitMQ message queue
result = collection.find_one({'id': number})
if result:
    GPIO.output(hw_pins['green'], True)
    GPIO.output(hw_pins['powerstrip'], True)

    GPIO.output(hw_pins['red'], False)
    # turn on led and the power strip here
    print("Access allowed")
    
else:
    GPIO.output(hw_pins['green'], False)
    GPIO.output(hw_pins['red'], True)
    # turn on the LEDS here
    print("Wasnt in there")


