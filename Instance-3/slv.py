#!/usr/bin/env python
import pika
import os
import sys
from flask import Flask, jsonify, request,\
abort, Response,  redirect, url_for
from flask_pymongo import PyMongo
from pymongo import MongoClient        
from bson.json_util import dumps, loads
import json
import threading
import logging
from kazoo.client import KazooClient
from kazoo.client import KazooState 
  

connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='rmq'))
channel = connection.channel()


app = Flask(__name__)
if(os.environ['type'] == 'slave' ):
    app.config["MONGO_URI"] = 'mongodb://' + os.environ['MONGODB_USERNAME'] + ':' + os.environ['MONGODB_PASSWORD'] + '@' + os.environ['MONGODB_HOSTNAME'] + ':27017/' + os.environ['MONGODB_DATABASE']  
    print("slave mongodb connected")

if(os.environ['type'] == 'master' ):
    app.config["MONGO_URI"] = 'mongodb://' + os.environ['MONGODB_USR'] + ':' + os.environ['MONGODB_PASS'] + '@' + os.environ['MONGODB_NAME'] + ':27017/' + os.environ['MONGODB_DB']  
    print("master mongodb connected")
mongo = PyMongo(app)    
db = mongo.db   



def read(body):
    #req_data = request.get_json()
    req_data = body
    req_data = loads(req_data)
    collection = req_data['collection']
    data = req_data['data']
    if(data == 'distinct'):
        data1 =  req_data['value']
        send_data = db[collection].distinct(data1)
        return dumps(send_data)
        
    send_data = db[collection].find(data)
    return dumps(send_data)



def clear_db():
    db.users.delete_many({})
    db.rides.delete_many({})
    return jsonify({})



def response(output):
    channel.queue_declare(queue='responseQ', durable=True)

    message = output
    channel.basic_publish(
    exchange='',
    routing_key='responseQ',
    body=message,
    properties=pika.BasicProperties(
        delivery_mode=2,  # make message persistent
    ))
    print(" [x] Sent data in responseQ from slave %r" % message)
    #connection.close()



def write(body):
    #req_data = request.get_json()
    req_data = body
    req_data = loads(req_data)
    collection = req_data['collection']
    data = req_data['data']

    if(req_data['work'] == 'insert'):    
        db[collection].insert_one(data)
        return jsonify({})

    if(req_data['work'] == 'delete'):
        db[collection].remove(data)
        return jsonify({})

    if(req_data['work'] == 'update'):
        data = req_data['data']
        #print("updatea here --- ",data[0],data[1])
        db[collection].update(data[0],data[1])
        return jsonify({})    



def callback_slv_syncQ(ch, method, properties, body):
    print(" [x] Received in slave_syncQ %r" % body)
    with app.app_context():
        if(body.decode() == "clear_db"):
            clear_db()
        else:
            op = write(body)
        ch.basic_ack(delivery_tag=method.delivery_tag)



def syncQ_rec():
    connection_2 = pika.BlockingConnection(
        pika.ConnectionParameters(host='rmq'))
    channel_2 = connection_2.channel()
    '''
    channel_2.queue_declare(queue='syncQ', durable=True)
    print(' [*] Waiting for messages in syncQ_slave')
    channel_2.basic_qos(prefetch_count=1)
    channel_2.basic_consume(queue='syncQ', on_message_callback=callback_slv_syncQ)

    channel_2.start_consuming()
    '''
    channel_2.exchange_declare(exchange='sync_exchange', exchange_type='fanout')

    result = channel_2.queue_declare(queue='', exclusive=True)
    queue_name = result.method.queue
    channel_2.queue_bind(exchange='sync_exchange', queue=queue_name)
    print(' [*] Waiting for logs. To exit press CTRL+C')

    channel_2.basic_consume(
        queue=queue_name, on_message_callback=callback_slv_syncQ)
    channel_2.start_consuming()



def syncQ_send(data):
    channel.exchange_declare(exchange='sync_exchange', exchange_type='fanout')

    message = data
    channel.basic_publish(exchange='sync_exchange', routing_key='', body=message)
    print(" [x] Sent %r" % message)
    #connection.close()
    ''' channel.queue_declare(queue='syncQ', durable=True)
    
    message = data
    channel.basic_publish(
    exchange='',
    routing_key='syncQ',
    body=message,
    properties=pika.BasicProperties(
        delivery_mode=2,  # make message persistent
    ))
    print(" [x] Sent from sync_master %r" % message)
    '''    



def callback_slv(ch, method, properties, body):
    print(" [x] Received in slave %r" % body)
    with app.app_context():
        op = read(body)
        response(op)
        #syncQ_rec()
        #print(" [x] Done")
        ch.basic_ack(delivery_tag=method.delivery_tag)


def callback_mst(ch, method, properties, body):
    print(" [x] Received in master %r" % body)
    with app.app_context():
        if(body.decode() == "clear_db"):
            clear_db()
        else:
            op = write(body)
        syncQ_send(body)
        #print(" [x] Done")
        ch.basic_ack(delivery_tag=method.delivery_tag)

'''
if(os.environ['type'] == 'master'):
    channel.queue_declare(queue='writeQ', durable=True)
    print(' [*] Waiting for messages in master')
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue='writeQ', on_message_callback=callback_mst)

    channel.start_consuming()
'''

def main_slave():
#if(os.environ['type'] == 'slave')
    channel.queue_declare(queue='readQ', durable=True)
    print(' [*] Waiting for messages in slave')
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue='readQ', on_message_callback=callback_slv)

    channel.start_consuming()
    
    
    
def main():
    logging.basicConfig()
    zk = KazooClient(hosts='zoo:2181')
    zk.start()
    zk.ensure_path("/worker")
    node_name = "/worker/" + os.environ["NODE_NAME"]
    if not zk.exists(node_name):
        msg = "Creating node: " + node_name
        print(msg, file=sys.stdout)
        #db_name = os.environ["MONGODB_NAME"]
        zk.create(node_name,b"master node" , ephemeral=True)
        
    if(os.environ['type'] == 'slave'):
        t1 = threading.Thread(target = main_slave).start()
        t2 = threading.Thread(target = syncQ_rec).start()
    
    elif(os.environ['type'] == 'master'):
        channel.queue_declare(queue='writeQ', durable=True)
        print(' [*] Waiting for messages in master')
        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(queue='writeQ', on_message_callback=callback_mst)
        channel.start_consuming()

if __name__ == "__main__": 
    main()    
