"""
Reads Distance using HC-SR04
"""

from math import dist
from time import sleep, time
# import time
from random import random
from threading import Thread
# from threading import Event
from gpiozero import DistanceSensor

from statemachine import StateMachine, State


PIN_ECHO = "GPIO24"
PIN_TRIGGER = "GPIO23"


class NoiseMachine(StateMachine):
    """ NoiseMachine helper class """
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
        thread_noise_lure = Thread(target=self.noise_lure)
        thread_noise_lure.start()

        thread_noise_scare = Thread(target=self.noise_scare)
        thread_noise_scare.start()

    def update(self):
        """ runs & updates state machine"""
        while True:
            if 300 <= self.distance and self.current_state != NoiseMachine.idle:
                self.gone()
            if 100 <= self.distance < 300 and self.current_state != NoiseMachine.lure:
                self.detected()
            if self.distance < 100 and self.current_state != NoiseMachine.scare:
                self.hooked()
            self.idle_since = time()
            sleep(0.1)

    def noise_lure(self):
        """ creates lure noise"""
        while True:
            # global distance
            if self.current_state == NoiseMachine.lure:
                print("make lure sound")
            sleep(0.5)

    def noise_scare(self):
        """ creates scare noise"""
        while True:
            # global distance
            if self.current_state == NoiseMachine.scare:
                print("make scare sound")
            sleep(0.5)


noise_machine = NoiseMachine()


def read_sensor():
    """ read sensor in fixed interval, 100ms"""
    sensor = DistanceSensor(echo=PIN_ECHO, trigger=PIN_TRIGGER, max_distance=4)
    while True:
        # global distance
        noise_machine.distance = sensor.distance * 100
        print(
            f"Distance: { noise_machine.distance:.2f} ;; Time: { noise_machine.idle_since:.2f}")
        sleep(0.2)


thread_sensor = Thread(target=read_sensor)
thread_sensor.start()

thread_machine_update = Thread(target=noise_machine.update)
thread_machine_update.start()
