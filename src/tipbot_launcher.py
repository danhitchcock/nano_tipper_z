import subprocess
import configparser
from time import sleep
from translations import python_command, tipper_options

filename = "nano_tipper_z.py"
while True:
    p = subprocess.Popen(python_command + " " + filename, shell=True).wait()
    if p != 0:
        sleep(5)
        continue
    else:
        break
