#!/bin/bash

# Exit on error
set -e

# Load environment variables
if [ -f .env ]; then
    source .env
else
    echo "Error: .env file not found"
    exit 1
fi

# Check required variables
if [ -z "$DIGITALOCEAN_REGISTRY_NAME" ] || [ -z "$DIGITALOCEAN_DROPLET_IP" ]; then
    echo "Error: Required environment variables not set"
    exit 1
fi

# Build and push Docker image
echo "Building Docker image..."
docker build -t whisper-streaming .

# Tag and push to DigitalOcean Container Registry
echo "Tagging image for DigitalOcean registry..."
docker tag whisper-streaming registry.digitalocean.com/$DIGITALOCEAN_REGISTRY_NAME/whisper-streaming:latest

echo "Pushing to DigitalOcean registry..."
docker push registry.digitalocean.com/$DIGITALOCEAN_REGISTRY_NAME/whisper-streaming:latest

# SSH into DigitalOcean droplet and deploy
echo "Deploying to DigitalOcean droplet..."
ssh root@$DIGITALOCEAN_DROPLET_IP << EOF
    cd /opt/whisper-streaming
    docker pull registry.digitalocean.com/$DIGITALOCEAN_REGISTRY_NAME/whisper-streaming:latest
    docker-compose down
    docker-compose up -d
EOF

echo "Deployment complete! The application should be available at http://$DIGITALOCEAN_DROPLET_IP:7878" 