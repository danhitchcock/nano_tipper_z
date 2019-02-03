import subprocess
from time import sleep
filename = 'nano_tipper_z.py'
while True:
    p = subprocess.Popen('python ' + filename, shell=True).wait()
    if p != 0:
        sleep(10)
        continue
    else:
        break

