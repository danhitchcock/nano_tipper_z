import subprocess
from time import sleep
filename = 'nano_tipper_z.py'
with open('python_version') as f:
    python_version = f.read().replace('\n', '')
while True:
    p = subprocess.Popen([python_version, filename], shell=False).wait()
    if p != 0:
        continue
    else:
        break

