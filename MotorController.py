#!/usr/bin/python
from Adafruit_MotorHAT import Adafruit_MotorHAT, Adafruit_DCMotor, Adafruit_StepperMotor
import time
import atexit
import threading
import random

stepstyles = [Adafruit_MotorHAT.SINGLE, Adafruit_MotorHAT.DOUBLE, Adafruit_MotorHAT.INTERLEAVE,
              Adafruit_MotorHAT.MICROSTEP]
steps_per_rev = 200

def stepper_worker(stepper, numsteps, direction, style):
    print("Steppin! "+str(numsteps),' steps')
    stepper.step(numsteps, direction, style)
    print("Done")

class Motor():
    def __init__(self):
        # create a default object, no changes to I2C address or frequency
        self.mh = Adafruit_MotorHAT()

        # create empty threads (these will hold the stepper 1 and 2 threads)
        self.st = threading.Thread()
        atexit.register(self.turnOffMotors)
        self.stepper = self.mh.getStepper(steps_per_rev, 1)  # 200 steps/rev, motor port #1
        self.stepper.setSpeed(60)  # 30 RPM

    def set_motor_frame(self, frame):
        if 'speed' in frame:
            self.rotate(frame['angle'], frame['speed'])
        else:
            self.rotate(frame['angle'])

    def reset(self):
        self.turnOffMotors()

    # recommended for auto-disabling motors on shutdown!
    def turnOffMotors(self):
        self.mh.getMotor(1).run(Adafruit_MotorHAT.RELEASE)
        self.mh.getMotor(2).run(Adafruit_MotorHAT.RELEASE)
        self.mh.getMotor(3).run(Adafruit_MotorHAT.RELEASE)
        self.mh.getMotor(4).run(Adafruit_MotorHAT.RELEASE)

    def rotate(self, angle, speed=None):
        if speed:
            self.stepper.setSpeed(speed)
        steps = int((angle/360)*steps_per_rev)
        if angle > 0:
            dir = Adafruit_MotorHAT.FORWARD
        else:
            dir = Adafruit_MotorHAT.BACKWARD
        self.st = threading.Thread(target=stepper_worker,
                               args=(self.stepper, steps, dir, Adafruit_MotorHAT.DOUBLE,))
        self.st.start()
