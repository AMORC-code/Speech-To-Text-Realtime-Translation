#!/bin/bash

# Kill any existing whisper server processes
pkill -f "python3 whisper_online_server.py"

# Start the whisper server in the background with explicit translation settings
WHISPER_TARGET_LANGUAGE=it python3 whisper_online_server.py --backend faster-whisper --model small --language it --task translate --buffer_trimming segment &

# Wait a moment for the server to start
sleep 3

# Start the microphone input
sox -d -t raw -r 48000 -c 1 -b 16 -e signed-integer - | sox -t raw -r 48000 -c 1 -b 16 -e signed-integer - -t raw -r 16000 -c 1 -b 16 -e signed-integer - | nc localhost 43007 