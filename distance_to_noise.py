"""
Reads Distance using HC-SR04
Outputs Sound via fluidsynth
"""

# from math import dist
import subprocess
from time import sleep, time
# from random import random
from threading import Thread
# from threading import Event
from gpiozero import DistanceSensor

from statemachine import StateMachine, State


PIN_ECHO = "GPIO23"
PIN_TRIGGER = "GPIO24"


# FLUID_CMD = """fluidsynth -s -p "fluid" -C0 -R0 -r48000 -a alsa \
# -m alsa_seq -o "shell.port=9800" -f config.txt"""
FLUID_CMD = """fluidsynth -s -p "fluid" -C0 -R0 -r48000 -a alsa -m alsa_seq -f config.txt"""

FLUID_NOTEON = """noteon {channel} {note} {volume}\n"""
FLUID_NOTEOFF = """noteoff {channel} {note}\n"""
FLUID_ALLNOTESOFF = """cc 1 123 0\n"""
FLUID_QUIT = """quit\n"""


class SynthInterface():
    """
        Synthesizer Interface
        Creates fluidsynth instance and sends commands through stdin
    """

    def __init__(self) -> None:
        self.fluidproc = None

    def start(self) -> None:
        """Start Subprocess """
        self.fluidproc = subprocess.Popen(
            FLUID_CMD, shell=True, stdout=subprocess.PIPE,
            stdin=subprocess.PIPE, stderr=subprocess.PIPE)

        # read signature until after the second empty newline
        linecnt = 0
        while True:
            line = self.fluidproc.stdout.readline()
            print(line)
            if line == b'\n':
                linecnt += 1
            if linecnt > 1:
                break

    def buzz(self) -> None:
        """Instruct fluidsynth to make buzz sound"""
        notecmd = FLUID_NOTEON.format(
            channel=1, note=30, volume=60).encode('utf-8')
        self.fluidproc.stdin.write(notecmd)
        self.fluidproc.stdin.flush()
        # print("buzz")
        # sleep(delay)
        # self.fluidproc.stdin.write(FLUID_NOTEOFF.encode('utf-8'))
        # self.fluidproc.stdin.flush()

    def thunder(self) -> None:
        """Instruct fluidsynth to make thunder sound"""
        notecmd = FLUID_NOTEON.format(
            channel=1, note=18, volume=80).encode('utf-8')
        self.fluidproc.stdin.write(notecmd)
        self.fluidproc.stdin.flush()
        # sleep(delay)
        # self.fluidproc.stdin.write(FLUID_NOTEOFF.encode('utf-8'))
        # self.fluidproc.stdin.flush()

    def silent(self) -> None:
        """Stop all Notes"""
        self.fluidproc.stdin.write(FLUID_ALLNOTESOFF.encode('utf-8'))
        self.fluidproc.stdin.flush()


class NoiseGenerator():
    """
        NoiseGenerator helper class
        Creates Sound dependent on Sttes
    """

    def __init__(self, synthif) -> None:
        self.synthif = synthif

        self.interval_buzz: float = -1
        self.interval_thunder: float = -1
        self.last_buzz: float = 0
        self.last_thunder: float = 0

    def start(self) -> None:
        """Start Threads """

        self.synthif.start()

        thread_sound_buzz = Thread(
            target=self.sound_buzz, args=[0.4])
        thread_sound_buzz.start()

        thread_sound_thunder = Thread(
            target=self.sound_thunder, args=[0.4])
        thread_sound_thunder.start()

    def sound_buzz(self, delay: int) -> None:
        """output buzz """
        while True:
            cur_time = time()
            if self.interval_buzz != -1 \
                    and cur_time - self.last_buzz >= self.interval_buzz - 0.1:
                # print(cur_time - self.last_buzz)
                self.last_buzz = cur_time
                # print("buzz")
                print(f"Buzz Intv: {self.interval_buzz:.2f}")
                self.synthif.buzz()
                sleep(self.interval_buzz)
            else:
                sleep(delay)

    def sound_thunder(self, delay: int) -> None:
        """output thunder """
        while True:
            cur_time = time()
            if self.interval_thunder != -1 \
                    and cur_time - self.last_thunder >= self.interval_thunder:
                # print(cur_time - self.last_thunder)
                self.last_thunder = cur_time
                # print("thunder")
                print(f"Thunder Intv: {self.interval_thunder:.2f}")
                self.synthif.thunder()
                sleep(self.interval_thunder)
            else:
                sleep(delay)


class NoiseState(StateMachine):
    """
        NoiseState helper class
        StateMachine to track and control active States
    """
    idle = State('Idle', initial=True)
    lure = State('Lure')
    scare = State('Scare')

    detected = lure.from_(idle, scare)
    hooked = scare.from_(idle, lure)
    gone = idle.from_(lure, scare)

    def __init__(self, noisegen: NoiseGenerator) -> None:
        super().__init__()

        self.distance = 0

        self.idle_since = 0
        self.lure_since = 0
        self.scare_since = 0
        self.state_since = 0

        self.noisegen = noisegen

    def start(self) -> None:
        """Start Threads """
        self.noisegen.start()

        thread_sensor = Thread(target=self.read_sensor, args=[0.05])
        thread_sensor.start()

        thread_machine_update = Thread(target=self.update, args=[0.2])
        thread_machine_update.start()

        thread_lure = Thread(target=self.check_lure, args=[0.6])
        thread_lure.start()

        thread_scare = Thread(target=self.check_scare, args=[0.6])
        thread_scare.start()

    def update(self, delay: int) -> None:
        """runs & updates state machine """
        while True:
            cur_time = time()
            diff = cur_time - self.state_since
            if (350 <= self.distance or self.distance <= 0) \
                    and self.current_state != NoiseState.idle \
                    and diff >= 5:
                self.gone()
            if 90 <= self.distance < 350 \
                    and self.current_state != NoiseState.lure \
                    and diff >= 2:
                self.detected()
            if 0 < self.distance < 90 \
                    and self.current_state != NoiseState.scare \
                    and diff >= 1:
                self.hooked()
            sleep(delay)

    def check_lure(self, delay: int) -> None:
        """sets lure noise interval """
        while True:
            cur_time = time()
            diff = cur_time - self.lure_since
            if self.current_state == NoiseState.lure and self.distance > 0 \
                    and diff > 2:
                self.noisegen.interval_buzz = self.map_dst_to_buzz()
                # print(f"Buzz Intv: {noise_generator.interval_buzz:.2f}")
            sleep(delay)
            # sleep(self.distance / 100)

    def check_scare(self, delay: int) -> None:
        """sets scare noise interval """
        while True:
            cur_time = time()
            diff = cur_time - self.scare_since
            if self.current_state == NoiseState.scare and self.distance > 0 \
                    and diff > 2:
                self.noisegen.interval_buzz = self.map_dst_to_buzz()
                self.noisegen.interval_thunder = self.map_dst_to_thunder()
                # print(f"Thunder Intv: {noise_generator.interval_thunder:.2f}")
            sleep(delay)

    def on_enter_idle(self) -> None:
        """entering idle State"""
        self.noisegen.interval_buzz = -1
        self.noisegen.interval_thunder = -1
        self.idle_since = time()
        self.noisegen.synthif.silent()
        print("State: idle")

    def on_enter_lure(self) -> None:
        """entering lure State"""
        self.lure_since = time()
        print("State: lure")

    def on_enter_scare(self) -> None:
        """entering scare State"""
        self.scare_since = time()
        print("State: scare")

    def on_exit_scare(self) -> None:
        """leaving scare State"""
        self.noisegen.interval_thunder = -1

    def on_detected(self) -> None:
        """transition 'detected' """
        self.state_since = time()

    def on_hooked(self) -> None:
        """transition 'hooked' """
        self.state_since = time()

    def on_gone(self) -> None:
        """transition 'gone' """
        self.state_since = time()

    def read_sensor(self, delay: int) -> None:
        """read sensor in fixed interval """
        sensor = DistanceSensor(
            echo=PIN_ECHO, trigger=PIN_TRIGGER, max_distance=4)
        while True:
            # global distance
            self.distance = sensor.distance * 100
            # print(
            #     f"Distance: { noise_state.distance:.2f} ;; Time: { noise_state.idle_since:.2f}")
            sleep(delay)

    def map_dst_to_buzz(self) -> float:
        """map distance to buzz sound interval"""
        return self.distance / 200
        # return (1-(20/(self.distance+20)))

    def map_dst_to_thunder(self) -> float:
        """map distance to thunder sound interval"""
        return self.distance / 30


synth_interface = SynthInterface()
noise_generator = NoiseGenerator(synth_interface)
noise_state = NoiseState(noise_generator)

noise_state.start()
