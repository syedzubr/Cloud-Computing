import os
from flask import Flask, jsonify, request,\
abort, Response,  redirect, url_for
from flask_pymongo import PyMongo
from pymongo import MongoClient
from datetime import datetime
from bson import Binary, Code
from bson.json_util import dumps, loads
import json
import hashlib
import requests
import datetime
import re


app = Flask(__name__)
app.config["MONGO_URI"] = 'mongodb://' + os.environ['MONGODB_USERNAME'] + ':' + os.environ['MONGODB_PASSWORD'] + '@' + os.environ['MONGODB_HOSTNAME'] + ':27017/' + os.environ['MONGODB_DATABASE']
mongo = PyMongo(app)
db = mongo.db


@app.route('/api/v1/rides/hello',methods=['GET'])
def test():
    return "hello_rides",200



def do_count(check):
    if(check == 1):
        rec = db.count.find({})
        rdata = list(rec) 
        ct = len(rdata) + 1
        db.count.insert_one({'data': {'count': ct}})
        return
        
    if(check == 2):
        rec = db.count.find({})
        rdata = list(rec) 
        ct = len(rdata) 
        return ct
        

#@app.route('/api/time', methods=['POST'])
def get_timestamp(timestamp):
    #req_data = request.get_json()
    #timestamp = req_data["timestamp"]
    date,time = timestamp.split(':')
    dd,mm,yy = date.split('-')
    ss,min,hh = time.split('-')

    isValidDate = True

    try:
        datetime.datetime(int(yy),int(mm),int(dd))
    except ValueError:
        isValidDate = False
    if(isValidDate):
        if(int(ss) > 59 or int(min) > 59 or int(hh) > 23):
            return "not-valid"
        else:
            return "valid"
    else:
        return "not-valid"


@app.route('/api/v1/rides', methods=['POST'])
def create_ride():
    do_count(1)
    req_data = request.get_json()
    name = req_data['created_by']

    #data = db.users.find({'username': name})
    #query = {'collection': 'users','data':{ 'username': name}}
    rec = requests.get(url='http://lb-591453474.us-east-1.elb.amazonaws.com/api/v1/users',
                            headers= {'Origin': '54.89.99.52'})        #LOOK here we use requests.get as it uses GET method ( list_users_api)
    rdata_old = loads(rec.text)
    rdata = []
    for val in rdata_old:
        if (name == val):
            rdata.append(val)

    rideId = 1
    max = 0

    if(len(rdata) > 0):
        timestamp = req_data['timestamp']
        # query = {'timestamp': timestamp}
        # rec = requests.post(url='http://assg3-lb-1719997549.us-east-1.elb.amazonaws.com/api/time',json=query)
        tm = get_timestamp(timestamp)
        if(tm != "valid"):
            return jsonify({}), 400


        #rides = list(db.rides.find())
        query = {'collection': 'rides','data':{}}
        rec = requests.post(url='http://34.198.254.117/api/v1/db/read',json=query)      
        rides = loads(rec.text)

        if(len(rides) <= 0):
            rideId = 1
        else:
            
            for i in range(0,len(rides)):
                
                if(rides[i]['rideId'] > max):
                    max = rides[i]['rideId']
                    rideId = max+1


        source = req_data['source']
        if(int(source) < 1 or int(source) > 198):
            return jsonify({}), 400

        dest = req_data['destination']
        if(int(dest) < 1 or int(dest) > 198):
            return jsonify({}), 400
        # db.rides.insert({
            # 'rideId': rideId,
            # 'created_by': name,
            # 'joinee': [],
            # 'timestamp' : timestamp,
            # 'source':source,
            # 'destination': dest
        # })
        query = {'collection': 'rides','work': 'insert', 'data': {'rideId': rideId,'created_by': name,'users': [],
            'timestamp' : timestamp,'source':source,'destination': dest}}
        a = requests.post(url='http://34.198.254.117/api/v1/db/write',json=query)
        return jsonify({}),201
    
    else:
        return jsonify({}),400
    


@app.route('/api/v1/db/clear', methods=['POST'])
def clear_db():
    requests.post(url='http://34.198.254.117/api/v1/db/clear')
    return jsonify({}), 200


@app.route('/api/v1/rides', methods=['GET'])
def upcoming_rides():
    do_count(1)
    if('source' in request.args):
        source = request.args['source']
    else:
        return jsonify({}), 400

    if('destination' in request.args):
        destination = request.args['destination']
    else:
        return jsonify({}), 400

    

    if(int(source) < 1 or int(source) > 198):
        return jsonify({}), 400

    if(int(destination) < 1 or int(destination) > 198):
        return jsonify({}), 400

    #data = list(db.rides.find({'source':source , 'destination':destination}))
    query = {'collection': 'rides','data':{'source':source , 'destination':destination}}
    rec = requests.post(url='http://34.198.254.117/api/v1/db/read',json=query)
    rdata = loads(rec.text) 
    #print(rdata)

    rides_list = []
    if(len(rdata) > 0):
        j=len(rdata)
        for i in range(0,j):
            rides_list.append(  {"rideId" : rdata[i]['rideId'],
            "username" : rdata[i]['created_by'] ,
            "timestamp" : rdata[i]['timestamp']
            })

        return json.dumps(rides_list),200
    else:
        return json.dumps(rides_list),204


@app.route('/api/v1/rides/<int:rideId>', methods=['GET'])
def ride_detail(rideId):
    do_count(1)
    #data = db.rides.find({'rideId': rideId})
    query = {'collection': 'rides','data':{'rideId': rideId}}
    rec = requests.post(url='http://34.198.254.117/api/v1/db/read',json=query)
    rdata = loads(rec.text)
    
    if(len(rdata) > 0):
        #print('==========',rdata[0])
        dic = dict()
        dic = rdata[0]
        dic.pop("_id")
        return json.dumps(dic),200
    else:
        return jsonify({}), 204



@app.route('/api/v1/rides/<int:rideId>', methods=['POST'])   
def join_ride(rideId):
    do_count(1)
    req_data = request.get_json()
    name = req_data['username']
    #dbname = db.users.find({'username': name})
    #query = {'collection': 'users','data':{ 'username': name}}
    rec = requests.get(url='http://lb-591453474.us-east-1.elb.amazonaws.com/api/v1/users',
                            headers= {'Origin': '54.89.99.52'})
    rdata_old = loads(rec.text)
    rdata = []
    for val in rdata_old:
        if(name == val):
            rdata.append(val) 
    #print(rdata)

    if(len(rdata) > 0):   
        #dbid = db.rides.find({'rideId': rideId})
        
        query = {'collection': 'rides','data':{ 'rideId': rideId}}
        rec = requests.post(url='http://34.198.254.117/api/v1/db/read',json=query)
        rdata = loads(rec.text) 
        #print(rdata, rdata[0]['rideId'])

        if(len(rdata) > 0):
        #if(dbid.count() > 0):
            #db.rides.update({'rideId': rideId}, {'$push': {'joinee': name}} )
            query = {'collection': 'rides','work': 'update', 'data': ({'rideId': rideId},{'$push': {'users': name}} )}
            a = requests.post(url='http://34.198.254.117/api/v1/db/write',json=query)
            #return a.text

            return jsonify({}), 201
        else:
            return jsonify({}), 400
    else:
        return jsonify({}), 400



@app.route('/api/v1/rides/<int:rideId>', methods=['DELETE'])   
def delete_ride(rideId):
    do_count(1)
    query = {'collection': 'rides','data':{ 'rideId': rideId}}
    rec = requests.post(url='http://34.198.254.117/api/v1/db/read',json=query)
    rdata = loads(rec.text) 

    if(len(rdata) > 0):
        query = {'collection': 'rides','work': 'delete', 'data':{ 'rideId': rideId}}
        rec = requests.post(url='http://34.198.254.117/api/v1/db/write',json=query)
        return jsonify({}), 200
    else:
        return jsonify({}), 400



@app.route('/api/v1/rides/count', methods=['GET'])
def rides_count():
    do_count(1)
    query = {'collection': 'rides','data':{}}
    rec = requests.post(url='http://34.198.254.117/api/v1/db/read',json=query)
    rides = loads(rec.text)
    
    rides_count = []
    rides_count.append(len(rides))
    return json.dumps(rides_count),200
    

@app.route('/api/v1/_count', methods=['GET'])
def count_req():
    county = do_count(2)
    list_count = []
    list_count.append(county)
    return json.dumps(list_count),200
    
 
@app.route('/api/v1/_count', methods=['DELETE'])
def count_zero():
    db.count.delete_many({})
    return jsonify({}),200


@app.errorhandler(405)
def method_not_allowed(e):
    do_count(1)
    return jsonify({"MyError" : "method not allowed"}),405

@app.errorhandler(404)
def page_not_found(e):
    return jsonify({"MyError" : "Page not found"}),404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"MyError" : "Server Error"}),500

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
   