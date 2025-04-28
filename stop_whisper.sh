#!/bin/bash

# Kill the whisper server process
pkill -f "python3 whisper_online_server.py"

# Kill the sox process
pkill -f "sox -d"

echo "Whisper server and microphone input stopped." 