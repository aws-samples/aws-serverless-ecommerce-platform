#!/bin/bash

SERVICE="$1" # arg passed to the script

if [ -z "$SERVICE" ]; then
        echo "Usage: $0 <service>"
        exit 1
fi

# Function to check if the last command executed successfully
check_error() {
        if [ $? -ne 0 ]; then
                echo "Error occured. Existing .."
                exit 1
        fi
}

echo "================= CLEAN SERVICE  ================"
./tools/clean "$SERVICE"
check_error

# Evaluate if SERVICE equals "payment-3p"
if [ "$SERVICE" == "payment-3p" ]; then
    cd payment-3p/ || exit 1
    # Copy files to the build folder
    if [ ! -d build/ ]; then 
        mkdir build/ 
    fi

    cp -rp src/ build/src/

    npx cdk synth --verbose > build/template.yaml

    # Save the current directory
    CURDIR=$(pwd)

    # Install packages and transpile to Javascript for each Lambda function
    for function_folder in build/src/* ; do
        cd "$function_folder" || exit
        npm i
        cd "$CURDIR" || exit
        npx tsc -p "$function_folder"
    done

    cd ../ || exit 1
else
    echo "============ BUILD RESOUCES SERVICE  =============="
    ./tools/build resources "$SERVICE"
    check_error

    echo "============ BUILD OPENAPI SERVICE  =============="
    ./tools/build openapi "$SERVICE"
    check_error

    echo "============ BUILD PYTHON3 SERVICE  =============="
    ./tools/build python3 "$SERVICE"
    check_error
fi

echo "============ BUILD CLOUDFORMATION SERVICE  =============="
./tools/build cloudformation "$SERVICE"
check_error

if [ ! "$SERVICE" == "payment-3p" ]; then
    echo "============ LINT CLOUDFORMATION SERVICE  =============="
    ./tools/lint cloudformation "$SERVICE"
    check_error

    echo "============ TESTS-UNIT PYTHON3 SERVICE  =============="
    ./tools/tests-unit python3 "$SERVICE"
    check_error
fi



echo "============ PACKAGE CLOUDFORMATION SERVICE  =============="
./tools/package cloudformation "$SERVICE"
check_error

echo "============ CHECK-DEPS CLOUDFORMATION SERVICE  =============="
./tools/check-deps cloudformation "$SERVICE" &
check_error

wait
echo "Ready to deploy : $SERVICE "