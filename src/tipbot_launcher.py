import subprocess
from time import sleep
from shared import python_command

filename = "tipbot.py"
while True:
    p = subprocess.Popen(python_command + " " + filename, shell=True).wait()
    if p != 0:
        sleep(5)
        continue
    else:
        break
