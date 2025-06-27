import asyncio
import websockets

async def send_commands():
    uri = "ws://localhost:8765"
    async with websockets.connect(uri) as websocket:
        print("✅ Connected to target_tracker")
        while True:
            print("\nCommands:")
            print("1. Set Target ID")
            print("2. Stop Tracking")
            print("3. Quit")
            choice = input("> ")

            if choice == "1":
                target_id = input("Enter target Track ID: ")
                await websocket.send(f"SET_ID {target_id}")
                response = await websocket.recv()
                print(f"Server: {response}")

            elif choice == "2":
                await websocket.send("STOP")
                response = await websocket.recv()
                print(f"Server: {response}")

            elif choice == "3":
                print("Goodbye!")
                break

            else:
                print("❓ Invalid choice")

asyncio.run(send_commands())
