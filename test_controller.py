from controller.xbox_controller import VirtualXboxController
import time

controller = VirtualXboxController()

print(time.strftime("%H:%M:%S"), "Connecting")
controller.connect()

print(time.strftime("%H:%M:%S"), "Press A")
controller.press_button("A")
controller.update()

time.sleep(5)

print(time.strftime("%H:%M:%S"), "Release A")
controller.release_button("A")
controller.update()

input("Press Enter to disconnect...")

controller.disconnect()