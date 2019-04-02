import subprocess
import configparser
from time import sleep

config = configparser.ConfigParser()
config.read('./tipper.ini')
#config.sections()
python_command = config['BOT']['python_command']

filename = 'nano_tipper_z.py'
while True:
    print('yup')
    p = subprocess.Popen([python_command, filename], shell=False).wait()
    if p != 0:
        sleep(5)
        continue
    else:
        break

