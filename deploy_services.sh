#!/bin/bash

#Get the list of services
#services=$(./tools/services --graph --env-only)

#Iterate over each service and deploy it
echo "============= #Iterate over each service and deploy it ==="

while read -r services; do
    IFS=',' read -ra service_array <<< "$services"
    for service in "${service_array[@]}";do
        ./tools/deploy cloudformation "$service"
    done
done <<< "$(./tools/services --graph --env-only)"

echo "all services deploy to aws cloud"