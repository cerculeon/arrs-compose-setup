#!/bin/bash

# Enabled services are controlled by services.yml.
# Edit that file (or run: python3 select_containers.py --edit) to change
# which containers are started. Services marked false are never pulled or started.

if [ "$1" == "yes" ]; then
    # Run: start only the services enabled in services.yml
    echo "Starting enabled services (as defined in services.yml)..."
    echo "Current directory: $(pwd)"
    python3 select_containers.py \
        --file htpcServices.yml \
        --env-file HTPC/HTPC_envValues.env \
        --run --build
else
    # Dry-run: print the docker compose command that would be executed
    echo "Dry-run: showing command for enabled services (services.yml)..."
    python3 select_containers.py \
        --file htpcServices.yml \
        --env-file HTPC/HTPC_envValues.env
fi
