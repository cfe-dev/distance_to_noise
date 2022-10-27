"""
  Test Synth Communication
"""
import subprocess
import random
from time import sleep

# start synth session
# FLUID_CMD = """fluidsynth -s -p "fluid" -C0 -R0 -r48000 -a alsa \
# -m alsa_seq -o "shell.port=9800" -f config.txt"""
FLUID_CMD = """ fluidsynth -s -p "fluid" -C0 -R0 -r48000 -a alsa -m alsa_seq -f config.txt """

# FLUID_NOTEON = """noteon 1 30 40\n"""
FLUID_NOTEON = """noteon {channel} {note} {volume}\n"""
# FLUID_NOTEOFF = """noteoff 1 30\n"""
FLUID_NOTEOFF = """noteoff {channel} {note}\n"""

FLUID_ALLNOTESOFF = """cc 1 123 0\n"""
FLUID_QUIT = """quit\n"""

fluidproc = subprocess.Popen(
    FLUID_CMD, shell=True, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

linecnt = 0
while True:
    line = fluidproc.stdout.readline()
    print(line)
    if line == b'\n':
        linecnt += 1
    if linecnt > 1:
        break

# try:
# outs, errs = fluidproc.communicate(
#     input=FLUID_NOTEON.encode('utf-8'), timeout=15)
# outs, errs = fluidproc.communicate(
#     input=FLUID_NOTEOFF.encode('utf-8'), timeout=15)
# fluidproc.stdin.write(FLUID_NOTEON.encode('utf-8'))
# fluidproc.stdin.write(FLUID_NOTEOFF.encode('utf-8'))
# except subprocess.TimeoutExpired:
#     fluidproc.kill()
#     outs, errs = fluidproc.communicate()

# while True:
for i in range(20):
    note = random.randint(29, 32)
    volume = random.randint(30, 50)

    notecmd = FLUID_NOTEON.format(
        channel=1, note=note, volume=volume).encode('utf-8')
    fluidproc.stdin.write(notecmd)
    fluidproc.stdin.flush()
    sleep(0.2)
    notecmd = FLUID_NOTEOFF.format(
        channel=1, note=note).encode('utf-8')
    fluidproc.stdin.write(notecmd)
    fluidproc.stdin.flush()

    # fluidproc.stdin.write(FLUID_NOTEON.encode('utf-8'))
    # fluidproc.stdin.flush()
    # sleep(0.2)
    # fluidproc.stdin.write(FLUID_NOTEON.encode('utf-8'))
    # fluidproc.stdin.flush()
    # sleep(0.2)
    # fluidproc.stdin.write(FLUID_NOTEON.encode('utf-8'))
    # fluidproc.stdin.flush()
    # sleep(0.2)
    # # fluidproc.stdin.write(FLUID_NOTEOFF.encode('utf-8'))
    # # fluidproc.stdin.flush()
    # # sleep(0.2)

fluidproc.stdin.write(FLUID_ALLNOTESOFF.encode('utf-8'))
fluidproc.stdin.flush()

fluidproc.stdin.write(FLUID_QUIT.encode('utf-8'))
fluidproc.stdin.flush()
fluidproc.wait()

print("end.")
# fluidproc.kill()
