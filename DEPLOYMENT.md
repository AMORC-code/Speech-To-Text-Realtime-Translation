# Deployment Guide

This guide explains how to deploy the Whisper Streaming application on DigitalOcean.

## Prerequisites

1. DigitalOcean account
2. Docker installed locally
3. DigitalOcean CLI installed (`doctl`)
4. SSH access to your DigitalOcean droplet

## Setup Steps

1. **Create a DigitalOcean Droplet**
   - Recommended: Ubuntu 22.04 LTS
   - Minimum specs: 4GB RAM, 2 vCPUs
   - Enable IPv6 and monitoring

2. **Set up Container Registry**
   ```bash
   doctl registry create your-registry-name
   doctl registry login
   ```

3. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your values
   ```

4. **Prepare Droplet**
   ```bash
   ssh root@your-droplet-ip
   apt update && apt upgrade -y
   apt install -y docker.io docker-compose
   mkdir -p /opt/whisper-streaming
   exit
   ```

5. **Deploy Application**
   ```bash
   chmod +x deploy.sh
   ./deploy.sh
   ```

## Post-Deployment

1. **Verify Deployment**
   - Check container status: `docker ps`
   - View logs: `docker logs whisper-app`
   - Test the application at `http://your-droplet-ip:7878`

2. **Set up Domain (Optional)**
   - Add A record pointing to your droplet's IP
   - Configure Nginx as reverse proxy
   - Set up SSL with Let's Encrypt

## Maintenance

- **Update Application**
  ```bash
  ./deploy.sh
  ```

- **View Logs**
  ```bash
  ssh root@your-droplet-ip
  docker logs -f whisper-app
  ```

- **Restart Service**
  ```bash
  ssh root@your-droplet-ip
  cd /opt/whisper-streaming
  docker-compose restart
  ```

## Troubleshooting

1. **Container Fails to Start**
   - Check logs: `docker logs whisper-app`
   - Verify environment variables
   - Ensure sufficient disk space

2. **Audio Processing Issues**
   - Verify FFmpeg installation
   - Check model files in volume
   - Monitor system resources

3. **Network Issues**
   - Verify firewall settings
   - Check port forwarding
   - Test network connectivity

## Security Considerations

1. **Firewall Configuration**
   ```bash
   ufw allow 22/tcp
   ufw allow 80/tcp
   ufw allow 443/tcp
   ufw enable
   ```

2. **Regular Updates**
   - Update system packages
   - Update Docker images
   - Rotate credentials

3. **Monitoring**
   - Set up alerts
   - Monitor resource usage
   - Regular backups

For additional support, please open an issue in the GitHub repository. 