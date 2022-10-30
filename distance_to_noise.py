"""
Reads Distance using HC-SR04
Outputs Sound via fluidsynth
"""

import subprocess
from time import sleep, time
from threading import Thread
from gpiozero import DistanceSensor
from statemachine import StateMachine, State


PIN_ECHO = "GPIO23"
PIN_TRIGGER = "GPIO24"


# FLUID_CMD = """fluidsynth -s -p "fluid" -C0 -R0 -r48000 -a alsa \
# -m alsa_seq -o "shell.port=9800" -f config.txt"""
FLUID_CMD = """fluidsynth -s -p "fluid" -C0 -R0 -r48000 -a alsa -m alsa_seq -f config.txt"""

FLUID_NOTEON = """noteon {channel} {note} {volume}\n"""
FLUID_NOTEOFF = """noteoff {channel} {note}\n"""
FLUID_ALLNOTESOFF = """cc {channel} 123 0\n"""
FLUID_QUIT = """quit\n"""

THUNDER_MIN_INTERVAL = 9.6

BUZZ_INTERVAL_MAX = 2.5
BUZZ_INTERVAL_MIN = 0.2
FLUID_BUZZ_NOTE_MAX = 60
FLUID_BUZZ_NOTE_MIN = 36
FLUID_BUZZ_VOL_MAX = 55
FLUID_BUZZ_VOL_MIN = 35


class SynthInterface():
    """
        Synthesizer Interface
        Creates fluidsynth instance and sends commands through stdin
    """

    def __init__(self) -> None:
        self.fluidproc: subprocess.Popen = None

    def start(self) -> None:
        """Start Subprocess """
        self.fluidproc = subprocess.Popen(
            FLUID_CMD, shell=True, stdout=subprocess.PIPE,
            stdin=subprocess.PIPE, stderr=subprocess.PIPE)

        # read signature until after the second empty newline
        linecnt: int = 0
        while True:
            line: bytes = self.fluidproc.stdout.readline()
            print(line)
            if line == b'\n':
                linecnt += 1
            if linecnt > 1:
                break

    def buzz(self, interval_buzz: float) -> None:
        """Instruct fluidsynth to make buzz sound"""
        note: int = self.map_interval_to_note(interval_buzz)
        vol: int = self.map_interval_to_vol(interval_buzz)
        notecmd = FLUID_NOTEOFF.format(
            channel=0, note=note).encode('utf-8')
        self.fluidproc.stdin.write(notecmd)
        notecmd = FLUID_NOTEON.format(
            channel=0, note=note, volume=vol).encode('utf-8')
        self.fluidproc.stdin.write(notecmd)
        self.fluidproc.stdin.flush()
        # print("buzz")
        print(
            f"Buzz Intv: {interval_buzz:.2f}; Note: {note:.2f}; Vol: {vol:.2f}")
        # sleep(delay)
        # self.fluidproc.stdin.write(FLUID_NOTEOFF.encode('utf-8'))
        # self.fluidproc.stdin.flush()

    def thunder(self) -> None:
        """Instruct fluidsynth to make thunder sound"""
        notecmd = FLUID_NOTEOFF.format(
            channel=1, note=60).encode('utf-8')
        self.fluidproc.stdin.write(notecmd)
        notecmd = FLUID_NOTEON.format(
            channel=1, note=60, volume=80).encode('utf-8')
        self.fluidproc.stdin.write(notecmd)
        self.fluidproc.stdin.flush()
        # sleep(delay)
        # self.fluidproc.stdin.write(FLUID_NOTEOFF.encode('utf-8'))
        # self.fluidproc.stdin.flush()

    def silent(self) -> None:
        """Stop all Notes"""
        self.fluidproc.stdin.write(
            FLUID_ALLNOTESOFF.format(channel=0).encode('utf-8'))
        # self.fluidproc.stdin.write(
        #     FLUID_ALLNOTESOFF.format(channel=1).encode('utf-8'))
        self.fluidproc.stdin.flush()

    def map_interval_to_note(self, interval_buzz: float) -> int:
        """Map intensity rating to actual Note"""
        ratio: float = (FLUID_BUZZ_NOTE_MAX - FLUID_BUZZ_NOTE_MIN) / \
            (BUZZ_INTERVAL_MAX - BUZZ_INTERVAL_MIN)
        # note: float = ratio * \
        # (interval_buzz - BUZZ_INTERVAL_MIN) + FLUID_BUZZ_NOTE_MIN
        note: float = FLUID_BUZZ_NOTE_MAX - \
            (ratio * (interval_buzz - BUZZ_INTERVAL_MIN))
        note = min(note, FLUID_BUZZ_NOTE_MAX)
        note = max(note, FLUID_BUZZ_NOTE_MIN)
        return round(note)

    def map_interval_to_vol(self, interval_buzz: float) -> int:
        """Map intensity rating to actual Volume"""
        ratio: float = (FLUID_BUZZ_VOL_MAX - FLUID_BUZZ_VOL_MIN) / \
            (BUZZ_INTERVAL_MAX - BUZZ_INTERVAL_MIN)
        vol: float = FLUID_BUZZ_VOL_MAX - \
            (ratio * (interval_buzz - BUZZ_INTERVAL_MIN))
        vol = min(vol, FLUID_BUZZ_VOL_MAX)
        vol = max(vol, FLUID_BUZZ_VOL_MIN)
        return round(vol)


class NoiseGenerator():
    """
        NoiseGenerator helper class
        Creates Sound dependent on Sttes
    """

    def __init__(self, synthif: SynthInterface) -> None:
        self.synthif: SynthInterface = synthif

        self.interval_buzz: float = -1
        self.interval_thunder: float = -1
        self.last_buzz: float = 0
        self.last_thunder: float = 0

    def start(self) -> None:
        """Start Threads """

        self.synthif.start()

        thread_sound_buzz = Thread(
            target=self.sound_buzz, args=[0.2])
        thread_sound_buzz.start()

        thread_sound_thunder = Thread(
            target=self.sound_thunder, args=[0.6])
        thread_sound_thunder.start()

    def sound_buzz(self, delay: int) -> None:
        """output buzz """
        while True:
            cur_time: float = time()
            diff: float = cur_time - self.last_thunder
            if self.interval_buzz != -1 \
                    and diff >= self.interval_buzz - 0.1:
                # print(cur_time - self.last_buzz)
                self.last_buzz = cur_time
                # print("buzz")
                # print(f"Buzz Intv: {self.interval_buzz:.2f}")
                self.synthif.buzz(interval_buzz=self.interval_buzz)
                sleep(self.interval_buzz)
            else:
                sleep(delay)

    def sound_thunder(self, delay: int) -> None:
        """output thunder """
        while True:
            cur_time: float = time()
            diff: float = cur_time - self.last_thunder
            if self.interval_thunder != -1 \
                    and diff >= self.interval_thunder \
                    and diff >= THUNDER_MIN_INTERVAL:
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
    idle: State = State('Idle', initial=True)
    lure: State = State('Lure')
    scare: State = State('Scare')

    detected = lure.from_(idle, scare)
    hooked = scare.from_(idle, lure)
    gone = idle.from_(lure, scare)

    def __init__(self, noisegen: NoiseGenerator) -> None:
        super().__init__()

        self.distance: float = 0

        self.idle_since: float = 0
        self.lure_since: float = 0
        self.scare_since: float = 0
        self.state_since: float = 0

        self.noisegen: NoiseGenerator = noisegen

    def start(self) -> None:
        """Start Threads """
        self.noisegen.start()

        thread_sensor = Thread(target=self.read_sensor, args=[0.1])
        thread_sensor.start()

        thread_machine_update = Thread(target=self.update, args=[0.3])
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
                    and diff >= 0.5:
                self.gone()
            if 50 <= self.distance < 350 \
                    and self.current_state != NoiseState.lure \
                    and diff >= 0.2:
                self.detected()
            if 0 < self.distance < 50 \
                    and self.current_state != NoiseState.scare \
                    and diff >= 0.2:
                self.hooked()
            sleep(delay)

    def check_lure(self, delay: int) -> None:
        """sets lure noise interval """
        while True:
            cur_time = time()
            diff = cur_time - self.lure_since
            if self.current_state == NoiseState.lure and self.distance > 0 \
                    and diff > 1:
                self.noisegen.interval_buzz = self.map_dst_to_buzz()
                # print(f"Buzz Intv: {noise_generator.interval_buzz:.2f}")
            sleep(delay)
            # sleep(self.distance / 100)

    def check_scare(self, delay: int) -> None:
        """sets scare noise interval """
        while True:
            cur_time = time()
            diff = cur_time - self.scare_since
            if self.current_state == NoiseState.scare and self.distance > 0:
                if diff > 0.3:
                    self.noisegen.interval_buzz = self.map_dst_to_buzz()
                if diff > 3:
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
            #     f"Distance: { noise_state.distance:.2f} ;; Time: { noise_state.state_since:.2f}")
            sleep(delay)

    def map_dst_to_buzz(self) -> float:
        """map distance to buzz sound interval"""
        buzz_interval: float = 0
        buzz_interval = self.distance / 200
        # return (1-(20/(self.distance+20)))
        # buzz_interval = 8.65471 + (-0.001402315 - 8.65471) / \
        #     (1 + (self.distance/945.7285) ** 1.011464)
        buzz_interval = min(buzz_interval, BUZZ_INTERVAL_MAX)
        buzz_interval = max(buzz_interval, BUZZ_INTERVAL_MIN)
        return buzz_interval

    def map_dst_to_thunder(self) -> float:
        """map distance to thunder sound interval"""
        return self.distance / 40


synth_interface = SynthInterface()
noise_generator = NoiseGenerator(synth_interface)
noise_state = NoiseState(noise_generator)

noise_state.start()
