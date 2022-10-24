'''
Reads Distance using HC-SR04
'''

from time import sleep
from random import random
from threading import Thread
from threading import Event
from gpiozero import DistanceSensor

PIN_ECHO = "GPIO24"
PIN_TRIGGER = "GPIO23"

sensor = DistanceSensor(echo=PIN_ECHO, trigger=PIN_TRIGGER, max_distance=4)
while True:
    print(f'Distance: { sensor.distance * 100 }')
    sleep(0.1)
    # sleep(0.005)


# # target task function
# def task(event, number):
#     # wait for the event to be set
#     event.wait()
#     # begin processing
#     value = random()
#     sleep(value)
#     print(f'Thread {number} got {value}')


# # create a shared event object
# event = Event()
# # create a suite of threads
# for i in range(5):
#     thread = Thread(target=task, args=(event, i))
#     thread.start()
# # block for a moment
# print('Main thread blocking...')
# sleep(2)
# # start processing in all threads
# event.set()
# # wait for all the threads to finish...
