import asyncio
from websockets.server import serve

connected_trackers = set()

async def handler(websocket):
    print(f"✅ Tracker connected from {websocket.remote_address}")
    connected_trackers.add(websocket)
    try:
        async for _ in websocket:
            pass
    except Exception as e:
        print(f"⚠️ Error with {websocket.remote_address}: {e}")
    finally:
        print(f"⚠️ Tracker disconnected: {websocket.remote_address}")
        connected_trackers.remove(websocket)

async def broadcast(message):
    if not connected_trackers:
        print("⚠️ No connected trackers.")
        return
    print(f"📡 Broadcasting: {message}")
    disconnected = []
    for ws in connected_trackers:
        try:
            await ws.send(message)
        except Exception:
            print(f"⚠️ Client disconnected: {ws.remote_address}")
            disconnected.append(ws)
    for ws in disconnected:
        connected_trackers.remove(ws)

async def cli_loop():
    while True:
        print("\nCommands:")
        print("1. Set Target ID")
        print("2. Stop Tracking")
        print("3. Show Connected Clients")
        print("4. Quit")
        choice = input("> ").strip()

        if choice == "1":
            target_id = input("Enter target Track ID: ").strip()
            await broadcast(f"SET_ID {target_id}")

        elif choice == "2":
            await broadcast("STOP")

        elif choice == "3":
            print(f"🔎 Connected clients: {len(connected_trackers)}")
            for ws in connected_trackers:
                print(f" - {ws.remote_address}")

        elif choice == "4":
            print("👋 Shutting down.")
            for ws in connected_trackers:
                await ws.close()
            break

        else:
            print("❓ Invalid choice")

async def main():
    async with serve(handler, "localhost", 8765):
        print("🌐 WebSocket server running at ws://localhost:8765")
        await cli_loop()

if __name__ == "__main__":
    asyncio.run(main())
