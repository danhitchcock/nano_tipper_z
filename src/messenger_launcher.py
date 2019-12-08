import subprocess
from time import sleep
from shared import python_command

filename = "messenger.py"
print(python_command + " " + filename)
while True:
    p = subprocess.Popen(python_command + " " + filename, shell=True).wait()
    if p != 0:
        sleep(2)
        continue
    else:
        break
