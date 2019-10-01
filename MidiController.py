import rtmidi

# midi_map = {'128-48': l.set_phase_shift,
#             '128-71': l.disable,
#             '128-72': l.enable,
#             '128-50': l.beat_nudge_back,
#             '128-52': l.beat_nudge_forward,
#             '128-57': rout_man.set_routine_type_all,
#             '128-59': rout_man.set_routine_type_normal,
#             '128-62': rout_man.set_routine_type_build,
#             '128-60': rout_man.set_routine_type_calm,
#             '176-8': rout_man.set_hue1,
#             '176-4': rout_man.set_hue2,
#             '128-65': rout_man.set_to_use_color1,
#             '128-67': rout_man.set_to_use_color2,
#             '128-66': rout_man.set_to_use_rand_colors,
#             '176-7': rout_man.set_sat
#             }

class Midi():
    def __init__(self, midi_map={}):
        self.midi_map = midi_map
        self.midi = rtmidi.MidiIn()
        self.connected = False
        print('Midi Mapped')

    def connect_to_MPK(self):
        available_ports = self.midi.get_ports()
        for idx, port in enumerate(available_ports):
            if 'MPK' in port:
                self.midi.open_port(idx)
                self.connected = True
                print('Connected to MPK')

    def __del__(self):
        del self.midi

    def get_msgs(self):
        ret = True
        msgs = {}
        while ret is not None:
            ret = self.midi.get_message()
            if ret is not None:
                msgs['-'.join([str(note) for note in ret[0][0:-1]])] = ret[0][-1]/127.0
        return self.process_msgs(msgs)

    def process_msgs(self, msgs):
        processed = False
        for msg in msgs:
            if msg in self.midi_map:
                self.midi_map[msg](msgs[msg])
                processed = True
        return processed