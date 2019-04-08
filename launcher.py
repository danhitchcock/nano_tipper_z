import subprocess
import configparser
from time import sleep

config = configparser.ConfigParser()
config.read('./tipper.ini')
#config.sections()
python_command = config['BOT']['python_command']
tipper_options = config['BOT']['tipper_options']

filename = 'nano_tipper_z.py'
print(python_command + " " + filename + " " + tipper_options)
while True:
    print('yup')
    p = subprocess.Popen(python_command + " " + filename, shell=True).wait()
    if p != 0:
        sleep(5)
        continue
    else:
        break

