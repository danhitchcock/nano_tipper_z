import subprocess
from time import sleep
import configparser
from translations import python_command, messenger_options

filename = "messenger.py"
print(python_command + " " + filename)
while True:
    p = subprocess.Popen(python_command + " " + filename, shell=True).wait()
    if p != 0:
        sleep(2)
        continue
    else:
        break
