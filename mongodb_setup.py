"""
Write code below to setup a MongoDB server to store usernames and passwords for HTTP Basic Authentication.

This MongoDB server should be accessed via localhost on default port with default credentials.

This script will be run before validating you system separately from your server code. It will not actually be used by your system.

This script is important for validation. It will ensure usernames and passwords are stored in the MongoDB server
in a way that your server code expects.

Make sure there are at least 3 usernames and passwords.

Make sure an additional username and password is stored where...
	username = admin
	password = pass
"""

from pymongo import MongoClient

# open the pymongo client to use
client = MongoClient('mongodb://localhost:27017/')

# Get the database to use
db = client.hokie_id
collection = db.student_ids

# Clear out old entries from the database here

set = {"id": "905870688", "start_time":"05-05-16-40", "end_time":"05-05-17-15"}



# insert the first default user name and password
collection.insert_one(set)
result = collection.delete_many({'id':'905870688'})

result = collection.find_one({'id': '905870688'})
if result:
    print("In there")
else:
    print("Not in there")
