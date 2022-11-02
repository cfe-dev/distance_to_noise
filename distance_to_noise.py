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

FLUID_CHANNEL_BUZZ = 0
FLUID_CHANNEL_THUNDER = 1

THUNDER_INTERVAL_MIN = 9.6

BUZZ_INTERVAL_MAX = 2.5
BUZZ_INTERVAL_MIN = 0.05
BUZZ_NOTE_MAX = 60
BUZZ_NOTE_MIN = 36
BUZZ_VOL_MAX = 55
BUZZ_VOL_MIN = 35

STATE_DELAY_IDLE = 4
STATE_DELAY_LURE = 1
STATE_DELAY_SCARE = 0.5


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

    def make_sound(self, channel: int = 0, note: int = 60,
                   vol: int = 60, noteoff: bool = True) -> None:
        """Instruct fluidsynth to make buzz sound"""
        if noteoff:
            notecmd = FLUID_NOTEOFF.format(
                channel=channel, note=note).encode('utf-8')
            self.fluidproc.stdin.write(notecmd)

        notecmd = FLUID_NOTEON.format(
            channel=channel, note=note, volume=vol).encode('utf-8')
        self.fluidproc.stdin.write(notecmd)
        self.fluidproc.stdin.flush()
        print(
            f"Channel: {channel:.2f}; Note: {note:.2f}; Vol: {vol:.2f}")
        # sleep(delay)
        # self.fluidproc.stdin.write(FLUID_NOTEOFF.encode('utf-8'))
        # self.fluidproc.stdin.flush()

    def silent(self, channel: int = -1) -> None:
        """Stop all Notes"""
        if channel == -1:
            for i in range(0, 15):
                self.fluidproc.stdin.write(
                    FLUID_ALLNOTESOFF.format(channel=i).encode('utf-8'))
        else:
            self.fluidproc.stdin.write(
                FLUID_ALLNOTESOFF.format(channel=channel).encode('utf-8'))
        self.fluidproc.stdin.flush()


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
            target=self.sound_buzz, args=[0.1])
        thread_sound_buzz.start()

        thread_sound_thunder = Thread(
            target=self.sound_thunder, args=[0.6])
        thread_sound_thunder.start()

    def sound_buzz(self, delay: int) -> None:
        """output buzz """
        while True:
            cur_time: float = time()
            diff: float = cur_time - self.last_buzz
            if self.interval_buzz != -1 \
                    and diff >= self.interval_buzz - 0.01:
                self.last_buzz = cur_time
                note: int = self.map_interval_to_note(
                    interval_buzz=self.interval_buzz)
                vol: int = self.map_interval_to_vol(
                    interval_buzz=self.interval_buzz)
                self.synthif.make_sound(
                    channel=FLUID_CHANNEL_BUZZ, note=note, vol=vol)

            if self.interval_buzz != -1:
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
                    and diff >= THUNDER_INTERVAL_MIN:
                # print(cur_time - self.last_thunder)
                self.last_thunder = cur_time
                # print("thunder")
                # print(f"Thunder Intv: {self.interval_thunder:.2f}")
                self.synthif.make_sound(channel=FLUID_CHANNEL_THUNDER)

            if self.interval_thunder != -1:
                sleep(self.interval_thunder)
            else:
                sleep(delay)

    def map_interval_to_note(self, interval_buzz: float) -> int:
        """Map intensity rating to actual Note"""
        ratio: float = (BUZZ_NOTE_MAX - BUZZ_NOTE_MIN) / \
            (BUZZ_INTERVAL_MAX - BUZZ_INTERVAL_MIN)
        # note: float = ratio * \
        # (interval_buzz - BUZZ_INTERVAL_MIN) + BUZZ_NOTE_MIN
        note: float = BUZZ_NOTE_MAX - \
            (ratio * (interval_buzz - BUZZ_INTERVAL_MIN))
        note = min(note, BUZZ_NOTE_MAX)
        note = max(note, BUZZ_NOTE_MIN)
        return round(note)

    def map_interval_to_vol(self, interval_buzz: float) -> int:
        """Map intensity rating to actual Volume"""
        ratio: float = (BUZZ_VOL_MAX - BUZZ_VOL_MIN) / \
            (BUZZ_INTERVAL_MAX - BUZZ_INTERVAL_MIN)
        vol: float = BUZZ_VOL_MAX - \
            (ratio * (interval_buzz - BUZZ_INTERVAL_MIN))
        vol = min(vol, BUZZ_VOL_MAX)
        vol = max(vol, BUZZ_VOL_MIN)
        return round(vol)


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
        self.last_distances: float = [10]

        self.idle_since: float = 0
        self.lure_since: float = 0
        self.scare_since: float = 0
        self.state_since: float = 0

        self.noisegen: NoiseGenerator = noisegen

    def start(self) -> None:
        """Start Threads """
        self.noisegen.start()

        thread_sensor = Thread(target=self.read_sensor, args=[0.3])
        thread_sensor.start()

        thread_machine_update = Thread(target=self.update, args=[0.05])
        thread_machine_update.start()

    def update(self, delay: int) -> None:
        """runs & updates state machine """
        while True:
            cur_time = time()
            diff = cur_time - self.state_since

            # switch states based on distance & delay
            if (350 <= self.distance or self.distance <= 0) \
                    and self.current_state != NoiseState.idle \
                    and diff >= STATE_DELAY_IDLE:
                self.gone()
            if 70 <= self.distance < 350 \
                    and self.current_state != NoiseState.lure \
                    and diff >= STATE_DELAY_LURE:
                self.detected()
            if 0 < self.distance < 70 \
                    and self.current_state != NoiseState.scare \
                    and diff >= STATE_DELAY_SCARE:
                self.hooked()

            # sets lure noise interval
            if self.current_state == NoiseState.lure and self.distance > 0:
                self.noisegen.interval_buzz = self.map_dst_to_buzz()

            # sets scare noise interval
            if self.current_state == NoiseState.scare and self.distance > 0:
                self.noisegen.interval_buzz = self.map_dst_to_buzz()
                self.noisegen.interval_thunder = self.map_dst_to_thunder()

            sleep(delay)

    def on_enter_idle(self) -> None:
        """entering idle State"""
        self.noisegen.interval_buzz = -1
        self.noisegen.interval_thunder = -1
        self.noisegen.synthif.silent()
        print("State: idle")

    def on_enter_lure(self) -> None:
        """entering lure State"""
        self.noisegen.interval_buzz = self.map_dst_to_buzz()
        print("State: lure")

    def on_enter_scare(self) -> None:
        """entering scare State"""
        self.noisegen.interval_buzz = self.map_dst_to_buzz()
        self.noisegen.interval_thunder = self.map_dst_to_thunder()
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
            # self.last_distances has size 10, delay is 0.3s
            # so we take the clostest distance of the last 3 seconds
            # for interval calculations
            self.last_distances.append(sensor.distance * 100)
            self.distance = min(self.last_distances)
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
        thunder_interval: float = 0
        thunder_interval = self.distance / 40
        thunder_interval = max(thunder_interval, THUNDER_INTERVAL_MIN)
        return thunder_interval


synth_interface = SynthInterface()
noise_generator = NoiseGenerator(synth_interface)
noise_state = NoiseState(noise_generator)

noise_state.start()
