#!/usr/bin/env python
import pika
from flask import Flask, jsonify, request,\
abort, Response,  redirect, url_for
from bson.json_util import dumps, loads
from flask_pymongo import PyMongo
from pymongo import MongoClient    
import json
import sys
import copy
import docker
import os 
import math
import time
import threading
#from zoo_watch import ZooWatch
from kazoo.client import KazooClient
import logging


connection = pika.BlockingConnection(
        pika.ConnectionParameters(host='rmq',heartbeat=600))
channel = connection.channel()
app = Flask(__name__)
app.config["MONGO_URI"] = 'mongodb://' + os.environ['MONGODB_USR'] + ':' + os.environ['MONGODB_PASS'] + '@' + os.environ['MONGODB_NAME'] + ':27017/' + os.environ['MONGODB_DB']  
print("master mongodb connected")
mongo = PyMongo(app)    
db = mongo.db   
client = docker.from_env()


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
        

def create_slave(n):
    #if n>0 : n slaves required  && if n<0 : n slaves need to remove(more slaves are runningthan required)
    if n > 0:
        for i in range(0,n):  
            run_mongodb(str(i+2))
            run_slave(str(i+2))
    else:
        for i in range(n,0):
            remove_container()


def run_mongodb(i):
    try:
       client.containers.run("mongo:4.0",detach=True, name = "mongodb"+i, network="flaskapp_default",\
       environment={"MONGO_INITDB_ROOT_USERNAME": "admin","MONGO_INITDB_ROOT_PASSWORD": "password","MONGO_INITDB_DATABASE": "mymongodb"},\
       restart_policy={"Name": "on-failure"}, volumes={'/home/ubuntu/flaskapp/mongo-init.js': {'bind': '/docker-entrypoint-initdb.d/mongo-init.js', 'mode': 'ro'}})
       print("created mongodb" + i)
   
    except docker.errors.APIError:
        for container in client.containers.list():
            if ("mongodb"+i) in container.name:
                container.stop()
                client.containers.prune()
                run_mongodb(i)


def run_slave(i):   
    try:
       img=client.images.build(path=".",dockerfile="Dockerfile")
       print(img[0].id)
       container = client.containers.run(img[0].id,command=["sh","-c","sleep 5 && python slv.py"],detach=True,name="slv"+i,restart_policy={"Name": "on-failure"},network="flaskapp_default",environment={"type":"slave",\
       "MONGODB_DATABASE":"mymongodb","MONGODB_USERNAME":"admin","MONGODB_PASSWORD": "password","MONGODB_HOSTNAME":"mongodb"+i,"NODE_NAME":"slv_node_"+i,"type":"slave"},links={"rmq":"slv"+i,"mongodb"+i:"slv"+i,"zoo": "slv"+i })
       print("created slave" + i)
    
    except docker.errors.APIError:
        for container in client.containers.list():
            if ("slv"+i) in container.name:
                container.stop()
                client.containers.prune()
                run_slave(i)



prune_cont = None
def remove_container():
    pid_slv = dict()
    pid_mongo = dict()
    for container in client.containers.list():
        if "slv" in container.name and container.name != "slv":
            opp = container.top()
            pid_slv.update(  {container.name : int(opp["Processes"][0][1])}   )
        
        if "mongodb" in container.name and "mongodb_mst" != container.name and "mongodb1" != container.name:
            opp = container.top()
            pid_mongo.update(  {container.name : int(opp["Processes"][0][1])}   )
            
    max = 0
    cp = 0
    print(pid_slv)
    print(pid_mongo)
    for key,value in pid_slv.items():     
        if(max < value):
            max = value
            container_name1 = key
            print("containers to prune",container_name1)
            cp = cp + 1
    
    max = 0
    for key,value in pid_mongo.items():     
        if(max < value):
            max = value
            container_name2 = key
            print("containers to prune",container_name2)
            cp = cp + 1
            
    for container in client.containers.list():
        if(cp > 1):
            if (container_name1 == container.name or container_name2 == container.name):        
                global prune_cont
                prune_cont = container
                #prune_list.append(container_name1)
                container.stop()
                client.containers.prune()



@app.route('/api/v1/worker/list', methods=['GET'])
def worker_list():
    pid_list = []
    for container in client.containers.list():
        if "slv" in container.name or "mongodb" in container.name :
            #pid_list.append(container.id)
            opp = container.top()
            pid_list.append(int(opp["Processes"][0][1]))
    return dumps(sorted(pid_list)),200
    
    
    
#create_slave(1)
def count_zero():
    db.count.delete_many({})
    
    
def worker_list2():
    pid_list = []
    for container in client.containers.list():
        if "slv" in container.name:
            #pid_list.append(container.id)
            opp = container.top()
            pid_list.append(int(opp["Processes"][0][1]))
    return (sorted(pid_list))



def read_counting():
    while True:
        COUNT = do_count(2)
        print(COUNT,"+++++++++++++++++++++")
        c1 = math.ceil(COUNT/20)
        print("read count",c1)
        lst = worker_list2()
        print(lst,"length of list = ",len(lst))
        c2 = len(lst)-1
        print("difference",c1 - c2)
        create_slave(c1-c2)
        count_zero()
        time.sleep(145)



@app.route('/api/v1/crash/slave', methods=['POST'])
def crash_slave():
    pid = dict()
    for container in client.containers.list():
        if "slv" in container.name:
            opp = container.top()
            pid.update(  {container.name : int(opp["Processes"][0][1])}   )
    max = 0
    print(pid)
    for key,value in pid.items():     
        if(max < value):
            max = value
            container_name = key 
            
    for container in client.containers.list():
        if container_name in container.name:        
            container.stop()
            #client.containers.prune()
    return jsonify({}),200



@app.route('/api/v1/crash/master', methods=['POST'])
def crash_master():
    for container in client.containers.list():
        if "mst" in container.name:
            container.stop()
            client.containers.prune()
    return jsonify({}),200



@app.route('/api/v1/db/clear', methods=['POST'])
def clear():
    channel.queue_declare(queue='writeQ', durable=True)
    message = "clear_db"
    print("message = " ,message)
    channel.basic_publish(
        exchange='',
        routing_key='writeQ',
        body=message,
        properties=pika.BasicProperties(
            delivery_mode=2,  # make message persistent
        ))

    print(" [x] Sent %r" % message)
    return jsonify({}), 201



@app.route('/api/v1/db/write', methods=['POST'])
def write():
    channel.queue_declare(queue='writeQ', durable=True)
    message = request.get_json()
    message = dumps(message)
    print("message = " ,message)
    channel.basic_publish(
        exchange='',
        routing_key='writeQ',
        body=message,
        properties=pika.BasicProperties(
            delivery_mode=2,  # make message persistent
        ))

    print(" [x] Sent %r" % message)
    return jsonify({}), 201



def send():
    channel.queue_declare(queue='readQ', durable=True)
    message = request.get_json()
    message = dumps(message)
    print("message = " ,message)
    channel.basic_publish(
        exchange='',
        routing_key='readQ',
        body=message,
        properties=pika.BasicProperties(
            delivery_mode=2,  # make message persistent
        ))

    print(" [x] Sent %r" % message)
    #connection.close()



global mybody
#///////////////////////////////////////////
def consume():
    channel.queue_declare(queue='responseQ', durable=True)
    print(' [*] Waiting for messages.')
    global mybody

    def callback(ch, method, properties, body):
        print(" [x] Received %r" % body)
        #time.sleep(body.count(b'.'))
        #print(" [x] Done")
        ch.basic_ack(delivery_tag=method.delivery_tag)                     
        global mybody
        mybody = copy.deepcopy(body)
        print("mybody inside = ",mybody)
        channel.stop_consuming()

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue='responseQ', on_message_callback=callback)

    channel.start_consuming()
    return (mybody)



@app.route('/api/v1/db/read', methods=['POST'])
def read():
    do_count(1)
    print("started exec")
    send()
    #/////////// op.decode() just brings in normal form eg from there it is sent in str converted to binary so, we need in str now thats why
    op = consume()
    print("------------",op.decode())
    return (op.decode()), 200



def listdiff(l1, l2):
    if len(l1) > len(l2):
        for i in l1:
            if i not in l2:
                return i
    else:
        for i in l2:
            if i not in l1:
                return i



class ZooWatch:
    def __init__(self):
        print("Zoo watch init")
        logging.basicConfig()
        self.zk = KazooClient(hosts='zoo:2181')
        self.zk.start()
        self.temp = []
        #self.master_db_name = "mongomaster"

    def start(self):
        print("[*] Starting zoo watch", file=sys.stdout)
        self.zk.ensure_path("/worker")

        @self.zk.ChildrenWatch("/worker")
        def callback_worker(workers):
            print("[*] Changes detected", file=sys.stdout)
            print(workers, self.temp)
            if len(workers) < len(self.temp):
                node = listdiff(self.temp, workers)
                print("[-] Node deleted: " + node, file=sys.stdout)
                print("[*] Current workers: " + str(workers), file=sys.stdout)
                if "slv_node" in node:
                    killed_containers = client.containers.list(all=True, filters={"exited": "137"})
                    print("[*] killed killed ++++++++",killed_containers)
                    #slave_cnt = client.containers.get(node)
                    
                    i = node[-1]
                    
                    global prune_cont
                    if prune_cont not in killed_containers and len(killed_containers)>0:
                        run_mongodb(i)
                        run_slave(i)
                    else:
                        print("[*] Scaling down - removing " + node)
                        #client.containers.prune()
                else:
                    print("[-] Master failed", file=sys.stdout)
                    

            elif len(workers) > len(self.temp):
                print("[+] Node added: " + listdiff(self.temp, workers), file=sys.stdout)
                print("[*] Current workers: " + str(workers), file=sys.stdout)

            else:
                pass

            self.temp = workers

        while True:
            pass



def start_zoo_watch():
    print("[+++]  thread started---------")
    watch = ZooWatch()
    watch.start()

if __name__ == '__main__':
    threading.Thread(target=start_zoo_watch).start()
    threading.Thread(target=read_counting).start()
    threading.Thread(target=app.run(host='0.0.0.0',port=80,debug=True,use_reloader=False)).start()
    #threading.Thread(target=start_zoo_watch).start()
