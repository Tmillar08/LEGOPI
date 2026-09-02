from gpiozero import Button
from signal import pause
import subprocess

button = Button(17, pull_up=True, hold_time=2)

def reboot():
    subprocess.run(["systemctl", "reboot"])

button.when_held = reboot

pause()
