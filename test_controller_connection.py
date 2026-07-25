from controller.xbox_controller import VirtualXboxController

try:
    controller = VirtualXboxController()

    print("Connecting...")
    controller.connect()

    print("Connected successfully!")
    input("Keep this window open and check joy.cpl. Press Enter to disconnect...")

    controller.disconnect()
    print("Disconnected.")

except Exception as e:
    print(f"Error: {e}")