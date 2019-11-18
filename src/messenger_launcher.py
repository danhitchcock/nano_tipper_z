import subprocess
from time import sleep
import configparser

config = configparser.ConfigParser()
config.read('./tipper.ini')
# config.sections()
python_command = config['BOT']['python_command']
messenger_options = config['BOT']['messenger_options']

filename = 'messenger.py'
print(python_command + " " + filename)
while True:
    p = subprocess.Popen(python_command + " " + filename, shell=True).wait()
    if p != 0:
        sleep(2)
        continue
    else:
        break

