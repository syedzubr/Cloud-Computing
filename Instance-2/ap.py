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


@app.route('/api/v1/users/hello',methods=['GET'])
def test():
    return "hello",200


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


@app.route('/api/v1/users',methods=['PUT'])
def add_user():
    do_count(1)
    req_data = request.get_json()
    
    name = req_data['username']
    passw = req_data['password']
    
    if(name == "" or passw == ""):
        return jsonify({}), 400

    hash_pass = hashlib.sha1(passw.encode())
    #print(hash_pass.hexdigest(),'-----------' ,hash_pass)
    
    query = {'collection': 'users','data':{ 'username': name}}
    rec = requests.post(url='http://34.198.254.117/api/v1/db/read',json=query)
    rdata = loads(rec.text) 
    #print(rdata)

    if(len(rdata) > 0):
        #return "Take diff username"
        return jsonify({}),400

    query = {'collection': 'users','work': 'insert', 'data': {'username': name, 'password': hash_pass.hexdigest()}}
    a = requests.post(url='http://34.198.254.117/api/v1/db/write',json=query)
    #print(a.status_code, a.reason,a.text)
    return jsonify({}),201



@app.route('/api/v1/users/<string:user>', methods=['DELETE'])
def delete_user(user):
    do_count(1)
    query = {'collection': 'users','data':{ 'username': user}}
    rec = requests.post(url='http://34.198.254.117/api/v1/db/read',json=query)
    rdata = loads(rec.text) 
    #print(rdata)

    if(len(rdata) > 0):
        query = {'collection': 'rides','data':{ 'created_by': user}}
        rec = requests.post(url='http://34.198.254.117/api/v1/db/read',json=query)
        rdata = loads(rec.text)
        
        if(len(rdata) > 0):
            query = {'collection': 'rides','work': 'delete', 'data':{ 'created_by': user}}
            rec = requests.post(url='http://34.198.254.117/api/v1/db/write',json=query)

        #data = db.users.find({"username": user})
        query = {'collection': 'users','work': 'delete','data':{ 'username': user}}
        a = requests.post(url='http://34.198.254.117/api/v1/db/write',json=query)
        return jsonify({}),200

    else:
        return jsonify({}),400



@app.route('/api/v1/users', methods=['GET'])
def list_all_users():
    do_count(1)
    query = {'collection': 'users','data':'distinct','value': 'username'}
    rec = requests.post(url='http://34.198.254.117/api/v1/db/read',json=query)
    rdata = loads(rec.text)
    if(len(rdata) > 0):
        return json.dumps(rdata), 200
    else:
        return json.dumps(rdata), 204


@app.route('/api/v1/db/clear', methods=['POST'])
def clear_db():
    requests.post(url='http://34.198.254.117/api/v1/db/clear')
    '''
    db.users.remove({})
    db.rides.remove({})
    '''
    return jsonify({}), 200



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
   