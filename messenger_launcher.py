import subprocess
from time import sleep
filename = 'messenger.py'
with open('python_version') as f:
    python_version = f.read().replace('\n', '')
while True:
    p = subprocess.Popen(python_version + ' ' + filename, shell=False).wait()
    print('something went wrong.')
    if p != 0:
        sleep(10)
        continue
    else:
        break

