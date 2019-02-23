import subprocess
from time import sleep

filename = "messenger.py"
while True:
    p = subprocess.Popen("python " + filename, shell=True).wait()
    if p != 0:
        sleep(10)
        continue
    else:
        break
