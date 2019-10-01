import sys
import os
#from pygame import midi.Input as midi
import rtmidi
import numpy as np
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/link-python/lib/')
import link


class Link(link.Link):
    def __init__(self):
        super(Link, self).__init__(120)
        self.enabled = True
        self.quantum_ = 8
        self.phase_shift = 0
        self.phase_ticker = 0
        self.beat_nudge = 0
        self.sess = self.captureSessionState()
        self.disable()
        print('Link Up, but disabled')

    def link_sync(self):
        self.sess = self.captureSessionState()

    def time_at_beat(self, beat):
        return self.sess.timeAtBeat(beat, self.quantum_) / 1000000

    def beat(self, time_at_beat=None):
        t = self.captureSessionState()
        if time_at_beat is None:
            time_at_beat = self.clock().micros()
        return t.beatAtTime(time_at_beat, self.quantum_)

    def bpm(self):
        t = self.captureSessionState()
        return t.tempo()

    def time(self):
        return self.clock().micros() / 1000000

    def phase(self, time_at_phase=None):
        t = self.captureSessionState()
        if time_at_phase is None:
            time_at_phase = self.clock().micros()
        base_phase = t.phaseAtTime(time_at_phase, self.quantum_)
        return np.mod(base_phase - self.phase_shift, self.quantum_)

    def set_phase_shift(self, vel):
        t = self.captureSessionState()
        self.phase_shift = np.round(t.phaseAtTime(self.clock().micros(), self.quantum_))
        print(self.phase_shift)
        self.phase_ticker = 0
        self.beat_nudge = 0
        print('Phase Reset')

    def now(self):
        return self.clock().micros()

    def enable(self):
        print('Link Enabled')
        self.enabled = True

    def disable(self):
        print('Link Disabled')
        self.enabled = False

    def check_phase_complete(self, phase):
        if phase >= self.quantum_:
            self.phase_ticker += 1
            print('BPM:', self.bpm())

    def beat_nudge_back(self, args):
        self.beat_nudge += 0.001

    def beat_nudge_forward(self, args):
        self.beat_nudge -= 0.001
