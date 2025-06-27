import paho.mqtt.client as mqtt

BROKER = "localhost"
PORT = 1883
TOPIC = "commands/target"

def main():
    client = mqtt.Client()
    client.connect(BROKER, PORT, 60)

    print("✅ Connected to MQTT broker at {}:{}".format(BROKER, PORT))
    print("Commands:")
    print("1. Set Target ID")
    print("2. Stop Tracking")
    print("3. Quit")

    while True:
        choice = input("\n> ").strip()
        if choice == "1":
            target_id = input("Enter Target Track ID: ").strip()
            msg = f"SET_ID {target_id}"
            client.publish(TOPIC, msg)
            print(f"📤 Sent: {msg}")

        elif choice == "2":
            client.publish(TOPIC, "STOP")
            print("📤 Sent: STOP")

        elif choice == "3":
            print("👋 Exiting.")
            break

        else:
            print("❓ Invalid choice")

    client.disconnect()
    print("✅ Disconnected from broker.")

if __name__ == "__main__":
    main()
