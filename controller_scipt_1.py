from controller.xbox_controller import VirtualXboxController
import time

controller = VirtualXboxController()

controller.connect()

print("Resetting...")
controller.reset()
controller.update()

input("Open joy.cpl -> Properties.\nAre ALL buttons OFF? Press Enter when checked...")

controller.disconnect()