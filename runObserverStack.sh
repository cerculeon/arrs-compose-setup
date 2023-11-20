#!/bin/bash

# Define the path to your Docker Compose file
#COMPOSE_FILE="./htpcServices.yml"

if [ "$1" == "yes" ]; then
    # If the argument is "yes", run docker-compose up -d
    echo "Argument is 'yes'. Running docker-compose up -d..."
    docker-compose -f observabilityServices.yml --env-file OBSERVER/OBSERVER_envValues.env up -d --build
else
    # If the argument is not "yes", run docker-compose config
    echo "Argument is not 'yes'. Running docker-compose config..."
    docker-compose -f observabilityServices.yml --env-file OBSERVER/OBSERVER_envValues.env config >HTPCconfig.yml
fi

# Display status
echo "Docker Compose stack has been started."

