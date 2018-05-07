#!/usr/bin/env python
from flask import Flask,render_template, request
import socket
import threading

Available = ""

def ReadTable():
    global Available
    TCP_IP = '0.0.0.0'
    TCP_PORT = 9696
    BUFFER_SIZE = 20
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((TCP_IP, TCP_PORT))
    s.listen(1)
    while 1:
        conn, addr = s.accept()
        while 1:
            data = conn.recv(BUFFER_SIZE)
            if not data:
                break
            Available=data.decode('utf-8').strip()
            #print(Available)
            #print("received data:", data.decode('utf-8'))
            conn.send(data)
        conn.close()

application = Flask(__name__)
@application.route('/MakeRes')
def StartFile():
    return render_template('LibraryFile.html')
@application.route('/ViewTables')
def Tables():
    if Available == "no":
        Test = 10
    elif Available == "yes":
        Test =5
    else:
        Test = 10
    return render_template('OpenTables.html', value=Test)

@application.route('/data',methods =['POST'])
def ViewData():
    PID_NUMBER = request.form['PID_NUMBER']
    TIME = request.form['TIME']
    if TIME == "1":
        TIME ="05-07-00-00,05-07-01-00"
    elif TIME == "2":
        TIME ="05-07-01-00,05-07-02-00"
    elif TIME == "3":
        TIME ="05-07-02-00,05-07-03-00"
    elif TIME == "4":
        TIME ="05-07-03-00,05-07-04-00"
    elif TIME == "5":
        TIME ="05-07-04-00,05-07-05-00"
    elif TIME == "6":
        TIME ="05-07-05-00,05-07-06-00"
    elif TIME == "7":
        TIME ="05-07-06-00,05-07-07-00"
    elif TIME == "8":
        TIME ="05-07-07-00,05-07-08-00"
    elif TIME == "9":
        TIME ="05-07-08-00,05-07-09-00"
    elif TIME == "10":
        TIME ="05-07-09-00,05-07-10-00"
    elif TIME == "11":
        TIME ="05-07-10-00,05-07-11-00"
    elif TIME == "12":
        TIME ="05-07-11-00,05-07-12-00"
    elif TIME == "13":
        TIME ="05-07-12-00,05-07-13-00"
    elif TIME == "14":
        TIME ="05-07-13-00,05-07-14-00"
    elif TIME == "15":
        TIME ="05-07-14-00,05-07-15-00"
    elif TIME == "16":
        TIME ="05-07-15-00,05-07-16-00"
    elif TIME == "17":
        TIME ="05-07-16-00,05-07-17-00"
    elif TIME == "18":
        TIME ="05-07-17-00,05-07-18-00"
    elif TIME == "19":
        TIME ="05-07-18-00,05-07-19-00"
    elif TIME == "20":
        TIME ="05-07-19-00,05-07-20-00"
    elif TIME == "21":
        TIME ="05-07-20-00,05-07-21-00"
    elif TIME == "22":
        TIME ="05-07-21-00,05-07-22-00"
    elif TIME == "23":
        TIME ="05-07-22-00,05-07-23-00"
    elif TIME == "24":
        TIME ="05-07-23-00,05-07-00-00"
    else:
        TIME = "NOT A VALID RESERVATION"
    TCP_IP = '172.29.127.136'
    TCP_PORT = 6969
    BUFFER_SIZE = 1024
    MESSAGE=PID_NUMBER+','+TIME
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((TCP_IP, TCP_PORT))
    s.send(str(MESSAGE).encode())
    data = s.recv(BUFFER_SIZE)
    s.close()
    return 'Reservation made'

if __name__ == "__main__":
    t = threading.Thread(name='t1', target=ReadTable)
    t.start()
    application.run(host='0.0.0.0')