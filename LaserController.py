import RPi.GPIO as GPIO


laser_to_pin = {
      'hside23': 22,
      'hside12': 21,
      'hside31': 16,
      'bside12': 24,
      'bside23': 25,
      'bside31': 20,
      'top': 23
}

class Laser():
    def __init__(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        for lname, pin in laser_to_pin.items():
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, False)

    def set_laser_frame(self, frame):
        for laser, action in frame.items():
            if laser in laser_to_pin:
                GPIO.output(laser_to_pin[laser], bool(action))

    def reset(self):
        for lname, pin in laser_to_pin.items():
            GPIO.output(pin, False)