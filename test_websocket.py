import asyncio
import websockets
import json

async def test_websocket():
    try:
        uri = 'ws://localhost:8000/ws'
        async with websockets.connect(uri) as websocket:
            print('Connected to WebSocket')
            # Wait for a few messages
            for i in range(5):
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=3)
                    data = json.loads(message)
                    print(f'Message {i+1}: {data}')
                except asyncio.TimeoutError:
                    print(f'Timeout waiting for message {i+1}')
                except Exception as e:
                    print(f'Error receiving message {i+1}: {e}')
    except Exception as e:
        print(f'WebSocket connection error: {e}')

if __name__ == "__main__":
    asyncio.run(test_websocket()) 