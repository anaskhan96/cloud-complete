#!/bin/bash

ACTS_PORT=8000
USERS_PORT=8080

#ACTS_PORT=9001
#USERS_PORT=9002

USERS_CID=""
ACTS_CID=""

function is_dockerd_running() {
    output=$(ps aux | grep dockerd | grep -v grep)
    len=${#output}
    if [ $len -gt 1 ]; then
        pid=$(echo $output | awk '{ print $2 }')
        echo "dockerd is running with PID $pid"
    else
        echo "dockerd isn't running on AWS instance" >&2
        exit
    fi
}

function is_users_running() { # sets USERS_CID
    output=$(sudo docker ps | grep "users")
    len=${#output}
    if [ $len -gt 1 ]; then
        USERS_CID=$(echo $output | awk '{ print $1 }')
        echo "Image 'users' is running with container ID $USERS_CID"
    else
        echo "Image 'users' isn't running on AWS instance" >&2
        exit
    fi
}

function is_acts_running() { # sets ACTS_CID
    output=$(sudo docker ps | grep "acts")
    len=${#output}
    if [ $len -gt 1 ]; then
        ACTS_CID=$(echo $output | awk '{ print $1 }')
        echo "Image 'acts' is running with container ID $ACTS_CID"
    else
        echo "Image 'acts' isn't running on AWS instance" >&2
        exit
    fi
}

function test_users_env_var() {
    output=$(sudo docker exec $USERS_CID printenv TEAM_ID)
    len=${#output}
    if [ $len -gt 1 ]; then
        echo "Environment varibale TEAM_ID is defined in 'users' container as '$output'"
    else
        echo "Environment varibale TEAM_ID isn't defined in 'users' container" >&2
        exit
    fi
}

function test_acts_env_var() {
    output=$(sudo docker exec $ACTS_CID printenv TEAM_ID)
    len=${#output}
    if [ $len -gt 1 ]; then
        echo "Environment varibale TEAM_ID is defined in 'acts' container as '$output'"
    else
        echo "Environment varibale TEAM_ID isn't defined in 'acts' container" >&2
        exit
    fi
}

function test_users_rest() {
    ROUTE="localhost:$USERS_PORT/api/v1/users"
    status_code=$(curl -o /dev/null -s -w "%{http_code}" $ROUTE)
    if [ $status_code -eq 000 ]; then
        echo "User management microservice isn't deployed on port $USERS_PORT" >&2
        exit
    else
        echo "User management microservice is deployed on port $USERS_PORT"
    fi
}

function test_acts_rest() {
    ROUTE=localhost:$ACTS_PORT/api/v1/categories
    status_code=$(curl -o /dev/null -s -w "%{http_code}" $ROUTE)
    if [ $status_code -eq 000 ]; then
        echo "Acts management microservice isn't deployed on port $ACTS_PORT" >&2
        exit
    else
        echo "Acts management microservice is deployed on port $ACTS_PORT"
    fi
}

function test_container_communication() {
    sudo apt install -y tcpflow > /dev/null 2> /dev/null

    # add user xyz
    curl -s -o /dev/null --header "Content-Type: application/json" \
        --request POST \
        --data '{"username":"xyz","password":"3d725109c7e7c0bfb9d709836735b56d943d263f"}' \
        localhost:$USERS_PORT/api/v1/users

    # add category abc
    curl -s -o /dev/null --header "Content-Type: application/json" \
        --request POST \
        --data '["abc"]' \
        localhost:$ACTS_PORT/api/v1/categories

    rm -f logs
    touch logs
    sudo tcpflow -p -c -i lo port $USERS_PORT > logs 2> /dev/null &
    sleep 5

    # add act
    curl -s -o /dev/null --header "Content-Type: application/json" \
        --request POST \
        --data '{"actId":1, "username":"xyz", "timestamp":"10-10-2019:45-23-03", "caption":"#helloworld", "categoryName":"abc", "imgB64":"bWF5byBvciBtdXN0Pw=="}' \
        localhost:$ACTS_PORT/api/v1/acts
    #curl -s -o /dev/null localhost:$USERS_PORT/api/v1/users

    sleep 10

    output=$(grep 'GET /api/v1/users' logs)
    len=${#output}
    if [ $len -gt 1 ]; then
        echo "Acts microservice did make GET request to users microservice for list of users"

        # delete act 1
        curl -s -o /dev/null --request DELETE localhost:$ACTS_PORT/api/v1/acts/1
    else
        echo "Acts microservice didn't make GET request to users microservice for list of users" >&2
        exit
    fi

    # delete user xyz
    curl -s -o /dev/null --request DELETE localhost:$USERS_PORT/api/v1/users/xyz

    # delete category abc
    curl -s -o /dev/null --request DELETE localhost:$ACTS_PORT/api/v1/categories/abc
}

is_dockerd_running
is_users_running
is_acts_running
test_users_env_var
test_acts_env_var
test_users_rest
test_acts_rest
test_container_communication