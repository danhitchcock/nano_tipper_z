import subprocess
from time import sleep
filename = 'nano_tipper_z.py'
with open('python_version') as f:
    python_version = f.read()
while True:
    p = subprocess.Popen(python_version + ' ' + filename, shell=True).wait()
    if p != 0:
        continue
    else:
        break

