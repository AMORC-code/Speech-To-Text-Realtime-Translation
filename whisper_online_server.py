#!/usr/bin/env python3
from whisper_online import *
import sys
import argparse
import logging
import numpy as np
import asyncio
from aiohttp import web
from deep_translator import GoogleTranslator

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

PORT = 7878
clients = set()

async def broadcast_translation(english_text):
    if not clients:
        logger.debug("No clients connected to broadcast to")
        return
        
    try:
        translator = GoogleTranslator(source='en', target='it')
        italian_text = translator.translate(english_text)
        
        message = json.dumps({
            "type": "translation",
            "english": english_text.strip(),
            "italian": italian_text.strip()
        })
        
        logger.debug(f"Broadcasting to {len(clients)} clients: {message}")
        disconnected = set()
        
        for client in clients:
            try:
                data = f"data: {message}\n\n"
                await client.write(data.encode('utf-8'))
                await client.drain()
                logger.debug(f"Successfully sent message")
            except Exception as e:
                logger.error(f"Failed to send to client: {str(e)}")
                disconnected.add(client)
        
        clients.difference_update(disconnected)
        if disconnected:
            logger.debug(f"Removed {len(disconnected)} disconnected clients")
            
    except Exception as e:
        logger.error(f"Error in broadcast_translation: {str(e)}")

class SSEHandler:
    async def handle(self, request):
        response = web.StreamResponse(
            status=200,
            headers={
                'Content-Type': 'text/event-stream',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': '*',
            }
        )
        
        await response.prepare(request)
        clients.add(response)
        logger.info(f"New client connected. Total clients: {len(clients)}")
        
        try:
            # Send initial connection confirmation
            await response.write(b'data: {"type":"connected"}\n\n')
            
            # Keep connection alive
            while True:
                await asyncio.sleep(1)
                if not response.prepared:
                    break
                
        except ConnectionResetError:
            logger.info("Client connection reset")
        except Exception as e:
            logger.error(f"Client connection error: {str(e)}")
        finally:
            if response in clients:
                clients.remove(response)
                logger.info(f"Client disconnected. Remaining clients: {len(clients)}")
        
        return response

async def process_audio(args):
    asr, online = asr_factory(args)
    
    def output_transcript(o, now=None):
        if o[0] is not None:
            text = o[2].strip()
            if text:
                logger.info(f"Detected speech: {text}")
                asyncio.create_task(broadcast_translation(text))
    
    while True:
        try:
            o = online.process_iter()
            output_transcript(o)
            await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"Error in process_audio: {str(e)}")
            await asyncio.sleep(1)

async def run_server(args):
    app = web.Application()
    
    # Add routes
    app.router.add_get('/translations', SSEHandler().handle)
    app.router.add_static('/', '.')
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    logger.info(f"Server running at http://localhost:{PORT}")
    
    # Start audio processing
    audio_task = asyncio.create_task(process_audio(args))
    
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        logger.info("Server shutdown requested")
    finally:
        audio_task.cancel()
        await runner.cleanup()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    add_shared_args(parser)
    args = parser.parse_args()
    
    set_logging(args, logger)
    
    try:
        asyncio.run(run_server(args))
    except KeyboardInterrupt:
        logger.info("Server stopped")
