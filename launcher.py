import subprocess
import requests

proxies = {
  "https": "https://10.10.1.10:1080",
}

requests.get("http://example.org", proxies=proxies)
from time import sleep
filename = 'nano_tipper_z.py'
with open('python_version') as f:
    python_version = f.read().replace('\n', '')
while True:
    p = subprocess.Popen([python_version, filename], shell=False).wait()
    if p != 0:
        sleep(5)
        continue
    else:
        break

