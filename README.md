# Cloud-Computing RideShare on Amazon AWS

# Rides-Instance
It has all the API's related to rides such as creating ride, joining ride, searching rides etc...

Has docker-compose.yml file to run just use sudo docker-compose up -d (detached mode) or sudo docker-compose up 

For the Project we used it in different ec2 instance.

All the read and write requests are directed to the orchestrator.

# Users-Instance
It has all the API's related to users such as creating users, deleting users etc...

Same as above

# Orchestrator, Master and Slave Workers, Zookeeper, Rabbitmq
docker-compose.yml file has all the images to build and run initially

command : sudo docker-compose up -d

file: orc.py 

It is Orchestrator where all the read and write requests arrive and are put in the respective
queues.

file : mst.py 

Master worker who reads the write requests from the writeQ put by the orchestrator 
and writes to the Db.

file: slv.py 

Slave worker who reads the read requests from readQ and put the data back in responseQ back to the
Orchestrator.

mongo-init.js files help in automated authentication of mongo database

Some commands:

sudo docker logs 'container name'     // to get logs of the container

If problem with rmq then do :

sudo docker stop $(sudo docker ps -a -q)    // to stop all containers

sudo docker rm rmq     //To remove the stoped container here rmq ( name of rabbitmq conainer as in docker-compose file )

sudo docker system prune -a --volumes      // To delete all the stopped images, caches everything its used ( carefull)
