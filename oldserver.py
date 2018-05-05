from pymongo import MongoClient
from functools import wraps
from flask import Flask, request, Response, jsonify
from zeroconf import Zeroconf
import socket
import pickle
import requests
from canvas_token import authentication

import requests

collection = None
client = None

r = Zeroconf()

# Setup for the canvas API stuff here
auth = authentication()
canvas_key = auth.getcanvas_key()
canvas_url = auth.getcanvas_url()
# Set up a session
session = requests.Session()
session.headers = {'Authorization': 'Bearer %s' % canvas_key}

def get_file_from_canvas(download_filename):
    params = (
        ('sort=name')
    )
    session.headers = {'Authorization': 'Bearer %s' % canvas_key}
    r = session.get(canvas_url+'?'+'only[]=names',params=params)
    r.raise_for_status()
    r = r.json()
    for x in r:
        if (x['filename']) == download_filename:
            file_id = (x['id'])
    r = session.get(canvas_url+'/'+str(file_id), stream=True)
    return r.content 
def push_file_to_canvas(upload_filename, file):
    # Step 1 - tell Canvas you want to upload a file
    payload = {}
    payload['name'] = upload_filename
    payload['parent_folder_path'] = '/'
    r = session.post(canvas_url, data=payload)
    r.raise_for_status()
    r = r.json()
    # Step 2 - upload file
    payload = list(r['upload_params'].items())  # Note this is now a list of tuples
    file_content = file.read()
    payload.append((u'file', file_content))  # Append file at the end of list of tuples
    r = requests.post(r['upload_url'], files=payload)
    r.raise_for_status()
    return r

def check_auth(username, password):
    """This function is called to check if a username /
    password combination is valid. and inside the mongodb database
    """
    result = collection.find_one({'username': username, 'password': password})
    if result:
        return True
    else:
        return False

def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(response='Could not verify your access level for that URL.\n'
    'You have to login with proper credentials\n',status=403)

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated


app = Flask(__name__)

data = {'red': 0.0, 'blue': 0.0, 'green': 0.0, 'rate': 0.0, 'state': 1}

@app.route('/led', methods=['GET', 'POST'])
@requires_auth
def index():
    if request.method == 'GET':
        info = None
        info = r.get_service_info("_http._tcp.local.", "My Service Name._http._tcp.local.")
        if info:
            return Response(status=200, response=str(data))
        else:
            return Response(response="LED resource is not ready\n",
                            status=503)
    elif request.method == "POST":
        data_sent = request.form # a dict
        if 'red' in data_sent:
            data['red'] = data_sent['red']
        if 'green' in data_sent:
            data['green'] = data_sent['green']
        if 'blue' in data_sent:
            data['blue'] = data_sent['blue']
        if 'rate' in data_sent:
            data['rate'] = data_sent['rate']
        if 'state' in data_sent:
            data['state'] = data_sent['state']
 
        # do the sending to the led here
        info = r.get_service_info("_http._tcp.local.", "My Service Name._http._tcp.local.")
        if info:
            TCP_IP = str(socket.inet_ntoa(info.address)) #'0.0.0.0'
            TCP_PORT = int(info.port)
            MESSAGE = data

            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((TCP_IP, TCP_PORT))
            s.send(pickle.dumps(MESSAGE))
            s.close()
            return Response(response="Success\n", status=200) 
        else:
            return Response(response="LED resource is not ready\n",
                            status=503)

@app.route('/canvas/download', methods=['GET'])
@requires_auth
def canvas_download():
    if request.method == 'GET':
        filename = request.args.get('filename')
        ret = get_file_from_canvas(filename)
        return Response(response=str(ret), status=200)
    else:
        return Response(status=400, response='Failed\n')

@app.route('/canvas', methods=['GET'])
@requires_auth
def canvas_list_files():
    if request.method == 'GET':
        params = (
            ('sort=name')
        )
        r = session.get(canvas_url+'?'+'only[]=names',params=params)
        r.raise_for_status()
        r = r.json()
        ret = {}
        count = 0
        for x in r:
            ret['filename'+str(count)] = x['filename']
            count += 1
        return jsonify(ret)

    else:
        return Response(status=400, response='Failed\n')

@app.route('/canvas/upload', methods=['POST'])
@requires_auth
def canvas_upload():
    if request.method == 'POST':
        r = request
        # check if the post request has the file part
        #if 'file' not in request.files:
        filename = r.args['filename']
        file = r.files[filename]

        push_file_to_canvas(filename, file)
        return Response(response="Success\n", status=200)

    else:
        return Response(status=400)


# implementation of the custom API
@app.route('/custom/times', methods=['GET', 'POST'])
@requires_auth
def custom_api():
    print(request.headers)
    if request.method == 'GET':
        # Check if the resource is available now, this was for the custom service example
        info = r.get_service_info("_http._tcp.local.", "My Service Name2._http._tcp.local.")
        if info:
            #make a request for the current time info.address
            to_send = "http://"
            to_send += str(socket.inet_ntoa(info.address))
            to_send += ":5000/custom/times"
            new_request = requests.get(to_send)
            return Response(response=new_request.text, status=200)
        else:
            return Response(response="Custom resource is not ready", status=503) 
    elif request.method == 'POST':
        info = r.get_service_info("_http._tcp.local.", "My Service Name2._http._tcp.local.")
        if info:
            # make a request for the current time info.address
            to_send = "http://"
            to_send += str(socket.inet_ntoa(info.address))
            to_send += ":5000/custom/times"
            new_request = requests.post(to_send, data=request.form)
            return Response(response=new_request.text, status=200)
        else:
            return  Response(response="Custom resource is not ready\n", status=503)
    else:
        return Response(status=400) 


@app.route('/custom/times/<int:time_id>', methods=['GET', 'POST'])
@requires_auth
def custom_api_time(time_id):
    print(request.headers)
    if request.method == 'GET':
        # Check if the resource is available now, this was for the custom service example
        info = r.get_service_info("_http._tcp.local.", "My Service Name2._http._tcp.local.")
        if info:
            #make a request for the current time
            to_send = "http://"
            to_send += str(socket.inet_ntoa(info.address))
            to_send += ":5000/custom/times/"
            to_send += str(time_id)
            new_request = requests.get(to_send)
            return Response(response=new_request.text, status=200)
        else:
            return  Response(response="Custom resource is not ready.", status=503)
    elif request.method == 'POST':
        # Check if the resource is available now, this was for the custom service$
        info = r.get_service_info("_http._tcp.local.", "My Service Name2._http._tcp.local.")
        if info:
            #make a request for the current time
            to_send = "http://"
            to_send += str(socket.inet_ntoa(info.address))
            to_send += ":5000/custom/times/" + str(time_id)
            new_request = requests.post(to_send, data=request.form)
            return Response(response=new_request.text, status=200)
        else:
            return  Response(response="Custom resource is not ready.", status=503)
    else:
        return Response(status=400)


@app.route('/custom/times/currentTime', methods=['GET'])
@requires_auth
def custom_api_current_time():
    print(request.headers)
    if request.method == 'GET':
        # Check if the resource is available now, this was for the custom service example
        info = r.get_service_info("_http._tcp.local.", "My Service Name2._http._tcp.local.")
        if info:
            #make a request for the current time
            to_send = "http://"
            to_send += str(socket.inet_ntoa(info.address))
            to_send += ":5000/custom/times/currentTime"
            new_request = requests.get(to_send)
            return Response(response=new_request.text, status=200)
        else:
            return  Response(response="Custom resource is not ready.\n", status=503)
    else:
        return Response(status=400)

if __name__ == '__main__':

    # before running the server, setup the values
    # open the pymongo client to use
    client = MongoClient('mongodb://localhost:27017/')

    # Get the database to use
    db = client.http_auth_database
    collection = db.auth_collection

    # run the server now
    app.run(host='0.0.0.0', port=5000, debug=True)





