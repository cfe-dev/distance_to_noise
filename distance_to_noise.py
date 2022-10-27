"""
Reads Distance using HC-SR04
"""

# from math import dist
from time import sleep, time
# from random import random
from threading import Thread
# from threading import Event
from gpiozero import DistanceSensor

from statemachine import StateMachine, State


PIN_ECHO = "GPIO24"
PIN_TRIGGER = "GPIO23"


class NoiseState(StateMachine):
    """
        NoiseState helper class
        StateMachine to track and control active States
    """
    distance = 0

    idle = State('Idle', initial=True)
    lure = State('Lure')
    scare = State('Scare')

    detected = lure.from_(idle, scare)
    hooked = scare.from_(idle, lure)
    gone = idle.from_(lure, scare)

    idle_since = 0
    lure_since = 0
    scare_since = 0

    def __init__(self) -> None:
        super().__init__()
        thread_sensor = Thread(target=self.read_sensor)
        thread_sensor.start()

        thread_machine_update = Thread(target=self.update)
        thread_machine_update.start()

        thread_lure = Thread(target=self.check_lure)
        thread_lure.start()

        thread_scare = Thread(target=self.check_scare)
        thread_scare.start()

    def update(self):
        """ runs & updates state machine """
        while True:
            if (300 <= self.distance or self.distance <= 0) and self.current_state != NoiseState.idle:
                self.gone()
            if 100 <= self.distance < 300 and self.current_state != NoiseState.lure:
                self.detected()
            if 0 < self.distance < 100 and self.current_state != NoiseState.scare:
                self.hooked()
            sleep(0.1)

    def check_lure(self):
        """ sets lure noise interval """
        while True:
            cur_time = time()
            if self.current_state == NoiseState.lure and self.distance > 0 and cur_time - self.lure_since < 150:
                noise_generator.interval_buzz = self.map_dst_to_buzz()
                # print(f"Buzz Intv: {noise_generator.interval_buzz:.2f}")
            sleep(0.1)
            # sleep(self.distance / 100)

    def check_scare(self):
        """ sets scare noise interval """
        while True:
            cur_time = time()
            if self.current_state == NoiseState.scare and self.distance > 0 and cur_time - self.scare_since < 150:
                noise_generator.interval_thunder = self.map_dst_to_thunder()
                # print(f"Thunder Intv: {noise_generator.interval_thunder:.2f}")
            sleep(0.1)

    def on_enter_idle(self):
        """ entering idle State"""
        noise_generator.interval_buzz = -1
        noise_generator.interval_thunder = -1
        self.idle_since = time()
        print("State: idle")

    def on_enter_lure(self):
        """ entering lure State"""
        self.lure_since = time()
        print("State: lure")

    def on_enter_scare(self):
        """ entering scare State"""
        self.scare_since = time()
        print("State: scare")

    def on_exit_scare(self):
        """ leaving scare State"""
        noise_generator.interval_thunder = -1

    def read_sensor(self):
        """ read sensor in fixed interval, 100ms"""
        sensor = DistanceSensor(
            echo=PIN_ECHO, trigger=PIN_TRIGGER, max_distance=4)
        while True:
            # global distance
            self.distance = sensor.distance * 100
            # print(
            #     f"Distance: { noise_state.distance:.2f} ;; Time: { noise_state.idle_since:.2f}")
            sleep(0.3)

    def map_dst_to_buzz(self) -> int:
        """ map distance to buzz sound interval"""
        return self.distance / 350

    def map_dst_to_thunder(self) -> int:
        """ map distance to thunder sound interval"""
        return self.distance / 30


class NoiseGenerator():
    """
        NoiseGenerator helper class
        Creates Sound dependent on Sttes
    """

    interval_buzz = -1
    interval_thunder = -1
    last_buzz = 0
    last_thunder = 0

    def __init__(self) -> None:
        thread_sound_buzz = Thread(target=self.sound_buzz)
        thread_sound_buzz.start()

        thread_sound_thunder = Thread(target=self.sound_thunder)
        thread_sound_thunder.start()

    def sound_buzz(self):
        """ output buzz """
        while True:
            curr_time = time()
            if self.interval_buzz != -1 and curr_time - self.last_buzz >= self.interval_buzz:
                self.last_buzz = curr_time
                # print("buzz")
                print(f"Buzz Intv: {noise_generator.interval_buzz:.2f}")
            sleep(0.05)

    def sound_thunder(self):
        """ output thunder """
        while True:
            curr_time = time()
            if self.interval_thunder != -1 and curr_time - self.last_thunder >= self.interval_thunder:
                self.last_thunder = curr_time
                # print("thunder")
                print(f"Thunder Intv: {noise_generator.interval_thunder:.2f}")
            sleep(0.05)


noise_state = NoiseState()
noise_generator = NoiseGenerator()
