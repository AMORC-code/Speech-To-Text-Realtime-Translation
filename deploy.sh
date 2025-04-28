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

echo "Building Docker image..."
docker build -t whisper-streaming -f Dockerfile .

echo "Tagging image for DigitalOcean registry..."
docker tag whisper-streaming registry.digitalocean.com/$DIGITALOCEAN_REGISTRY_NAME/whisper-streaming:latest

echo "Pushing to DigitalOcean registry..."
docker push registry.digitalocean.com/$DIGITALOCEAN_REGISTRY_NAME/whisper-streaming:latest

echo "Deploying to DigitalOcean droplet..."
ssh root@$DIGITALOCEAN_DROPLET_IP << EOF
    # Install Docker if not already installed
    if ! command -v docker &> /dev/null; then
        curl -fsSL https://get.docker.com -o get-docker.sh
        sh get-docker.sh
    fi

    # Install NVIDIA Container Toolkit
    distribution=\$(. /etc/os-release;echo \$ID\$VERSION_ID) \
        && curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
        && curl -s -L https://nvidia.github.io/libnvidia-container/\$distribution/libnvidia-container.list | \
            sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
            sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
    
    apt-get update && apt-get install -y nvidia-container-toolkit
    nvidia-ctk runtime configure --runtime=docker
    systemctl restart docker

    # Create app directory if it doesn't exist
    mkdir -p /opt/whisper-streaming

    # Pull the latest image
    docker pull registry.digitalocean.com/$DIGITALOCEAN_REGISTRY_NAME/whisper-streaming:latest

    # Stop existing container if running
    docker stop whisper-streaming || true
    docker rm whisper-streaming || true

    # Run the new container
    docker run -d \
        --name whisper-streaming \
        --restart unless-stopped \
        --gpus all \
        -p 7878:7878 \
        registry.digitalocean.com/$DIGITALOCEAN_REGISTRY_NAME/whisper-streaming:latest
EOF

echo "Deployment complete! The application should be available at http://$DIGITALOCEAN_DROPLET_IP:7878" 