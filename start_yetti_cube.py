#!/usr/bin/python3
import functools
from MotorController import Motor
from MidiController import Midi
from LinkController import Link
from LEDController import LEDs
from LaserController import Laser
from RoutineManager import RoutineManager
import asyncio
import numpy as np

leds = LEDs()
#motor = Motor()
link = Link()
laser = Laser()
rm = RoutineManager(compile_routines=False)
system_on = True


def reset():
    laser.reset()
    leds.reset()
    #motor.reset()


def arm_system(on):
    """Turn on lights. FIXME Probably a better way to do this than a global?"""
    global system_on
    system_on = on
    if not on:
        reset()
    print('System On=', on)


def select_routine(type):
    rm.select_rand_routine_by_type(type)
    reset()


midi_map = {
    '176-1': leds.set_brightness,
    '176-4': lambda x: leds.change_color(1, x),
    '176-8': lambda x: leds.change_color(2, x),
    '128-57': lambda x: select_routine('base'),
    '128-59': lambda x: select_routine('low'),
    '128-60': lambda x: select_routine('med'),
    '128-62': lambda x: select_routine('high'),
    '128-64': lambda x: select_routine('build'),
    '128-68': lambda x: reset(),
    '128-67': lambda x: arm_system(True),
    '128-69': lambda x: arm_system(False),
    '128-71': lambda x: link.disable(),
    '128-72': lambda x: link.enable(),
    }
midi = Midi(midi_map)

loop = asyncio.get_event_loop()
print("Tessaract Online")

##'motor': motor.set_motor_frame,

device_run_functions = {
    'leds' : leds.set_led_frame,
    'laser': laser.set_laser_frame,
}


async def poll_for_SDJ():
    """Polls for SDJ connection, stops when done"""
    while not link.numPeers():
        await asyncio.sleep(2)  # poll link every 1 seconds, wating for connection
    # link.disable() #TODO uncomment this when midi done, so that we can always start as slave
poll_for_SDJ_task = loop.create_task(poll_for_SDJ())
poll_for_SDJ_task.add_done_callback(functools.partial(print, "Connected to SDJ"))


async def periodic_link_sync():
    """This task keeps the link session up to date, so our predicted event times are accurate"""
    while True:
        link.link_sync()
        await asyncio.sleep(.5)
periodic_link_sync_task = loop.create_task(periodic_link_sync())


def schedule_next_frame(frame_num):
    """This function is schedules the next frame (light, motor, lasers). It is trigged to run just before the next beat to give it time to prepare"""
    rm.update_beat()
    frames = rm.get_frames_for_next_beat()
    if system_on:
        for frame in frames:
            beat_offset = frame['all']['start_beat'] - np.floor(frame['all']['start_beat'])
            time_to_run = link.time_at_beat(frame_num+beat_offset)
            for device, commands in frame.items():
                if (device in device_run_functions) and (device != 'all'):
                    loop.call_at(time_to_run, functools.partial(device_run_functions[device], commands))
    frame_num += 1
    time_to_get_next_frames = link.time_at_beat(frame_num-0.3)
    loop.call_at(time_to_get_next_frames, functools.partial(schedule_next_frame, frame_num))


async def wait_for_rt_setup():
    while not rm.rts_inited:
        await asyncio.sleep(0.5)
    loop.call_soon(functools.partial(schedule_next_frame, np.ceil(link.beat())))
wait_for_rt_setup_task = loop.create_task(wait_for_rt_setup())
wait_for_rt_setup_task.add_done_callback(functools.partial(print, "Routines ready, beginning sequence"))


async def poll_for_midi_commands():
    while midi.connected:
        midi.get_msgs()
        await asyncio.sleep(0.2)
    #Not Connected:
    wait_for_midi_connect_task = loop.create_task(wait_for_midi_connect())
    wait_for_midi_connect_task.add_done_callback(functools.partial(print, "Midi Connected"))


async def wait_for_midi_connect():
    while not midi.connected:
        midi.connect_to_MPK()
        await asyncio.sleep(1)
    #Connected:
    poll_for_midi_commands_task = loop.create_task(poll_for_midi_commands())

wait_for_midi_connect_task = loop.create_task(wait_for_midi_connect())
wait_for_midi_connect_task.add_done_callback(functools.partial(print, "Midi Connected"))

loop.run_forever()

#TODO: Assign sides of lights
#TODO: make more complex routines
#TODO: Consider a way to offset beats
#TODO: Consider a way to speed up or slow down routine (x2)
#TODO: Laser controller
#TODO: 3D print gears
#TODO: PCB + solder components




