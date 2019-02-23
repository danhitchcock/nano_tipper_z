import subprocess

filename = "nano_tipper_z.py"
while True:
    p = subprocess.Popen("python " + filename, shell=True).wait()
    if p != 0:
        continue
    else:
        break
