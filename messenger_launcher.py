import subprocess
from time import sleep
filename = 'messenger.py'
with open('python_version') as f:
    python_version = f.read()
while True:
    p = subprocess.Popen(python_version + ' ' + filename, shell=True).wait()
    print('something went wrong.')
    if p != 0:
        sleep(10)
        continue
    else:
        break

