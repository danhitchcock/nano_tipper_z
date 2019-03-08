import subprocess
from time import sleep
import configparser

config = configparser.ConfigParser()
config.read('./tipper.ini')
print(config.sections())
python_command = config['BOT']['python_command']

filename = 'messenger.py'
while True:
    p = subprocess.Popen([python_command, filename], shell=False).wait()
    if p != 0:
        sleep(2)
        continue
    else:
        break

