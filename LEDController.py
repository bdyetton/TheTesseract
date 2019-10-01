from neopixel import Adafruit_NeoPixel, Color, ws
import numpy as np
import colorsys

face_side_config = {
    'B2': {'NE':6, 'SE':8, 'SW':8, 'NW':8},
    'B3': {'NE':8, 'SE':8, 'SW':8, 'NW':6},
    'B1': {'NE':7, 'SE':8, 'SW':7, 'NW':8},
    'T3': {'NE':8, 'SE':8, 'SW':7, 'NW':7},
    'T1': {'NE':7, 'SE':7, 'SW':8, 'NW':8},
    'T2': {'NE':7, 'SE':8, 'SW':8, 'NW':7}
}

anticlockwise_faces = ['T1', 'T2', 'B2', 'B1']
sort_order = {'NE':1, 'SE':2, 'SW':3, 'NW':4}
sort_order_inverted = {'SW':1, 'NW':2, 'NE':3, 'SE':4}

face_idxs={}
side_idxs={}
all_idxs = []
start_idx = 0
end_idx = 0
for f, face in face_side_config.items():
    if 'B' in f:
        face_sort_order = sort_order_inverted
    else:
        face_sort_order = sort_order
    side_keys = sorted(face.keys(), key=face_sort_order.__getitem__)
    side_idxs[f] = {}
    start_face_idx = end_idx
    if f in anticlockwise_faces:
        side_keys = sorted(side_keys, key=face_sort_order.__getitem__, reverse=True)
    for s in side_keys:
        side = face_side_config[f][s]
        end_idx = start_idx+side
        side_leds = list(range(start_idx, end_idx))
        if f in anticlockwise_faces:
            side_leds.reverse()
        # if (f not in inverted_faces) and('W' in s):
        #     side_leds.reverse()
        # if (f in inverted_faces) and ('E' in s):
        #     side_leds.reverse()
        side_idxs[f][s] = side_leds
        start_idx = end_idx
    face_idxs[f] = list(range(start_face_idx, end_idx))
    all_idxs += face_idxs[f]


class LEDs(Adafruit_NeoPixel):
    def __init__(self, *args, **kwargs):
        super(LEDs, self).__init__(int(end_idx), 18, strip_type=ws.WS2811_STRIP_RGB)
        self.begin()
        self.brightness = 0.5 #0=black, 0.5=color, 1=white this is the absolute brightness, which is scaled by the routine
        self.color_nums = [Color(0, 0, 0), Color(23, 45, 67), Color(0, 45, 1), Color(100, 45, 1)] #color 0 should never change
        self.color_hues = [0, 77, 40, 99] #not actually used, defaults to color nums above

    def hue_to_color(self, hue):
        rgb = colorsys.hls_to_rgb(hue, 0.5, 1)
        rgb_scaled = [int(c*255) for c in rgb]
        return Color(*rgb_scaled)

    def make_color(self, hue, brightness):
        rgb = colorsys.hls_to_rgb(hue, brightness, 1)
        rgb_scaled = [int(c*255) for c in rgb]
        return Color(*rgb_scaled)

    def reset(self): #TODO test
        for pix in all_idxs:
            self.setPixelColor(pix, self.color_nums[0])
        self.show()

    def set_brightness(self, brightness):
        self.brightness = brightness
        self.make_brightness(self.brightness)

    def make_brightness(self, brightness):
        for i, h in enumerate(self.color_hues[1:]):
            self.color_nums[i+1] = self.make_color(h, brightness)

    def change_color(self, color_num, hue):
        self.color_hues[color_num] = hue
        self.color_nums[color_num] = self.make_color(self.color_hues[color_num], self.brightness)

    def set_led_frame(self, led_frame):
        if 'bright' in led_frame:
            self.make_brightness(float(led_frame['bright'])*self.brightness) #brightness comes in as percentage
            del led_frame['bright']
        leds_frame_idxs = []
        leds_frame_colors = []
        sort_map = {'led': 1,
                    'side': 2,
                    'face': 3} #want to sort so order of preperence: LED, side, then face
        unit_names = led_frame.keys()
        unit_names = sorted(unit_names, key=lambda x: sort_map[x.split('_')[0]])
        for unit in unit_names:
            color = led_frame[unit]
            if 'led' in unit: #Order of preperence: LED, side, then face
                unit = unit.replace('led_', '')
                (face, side, led_idx) = unit.split('_')
                led_idx = int(led_idx)
                leds_frame_idxs += [side_idxs[face][side][led_idx]]
                leds_frame_colors += [self.color_nums[int(color)]]
            elif 'side' in unit:
                unit = unit.replace('side_', '')
                (face, side) = unit.split('_')
                side_led_idxs = side_idxs[face][side]
                leds_frame_idxs += side_led_idxs
                leds_frame_colors += [self.color_nums[int(color)]]*len(side_led_idxs)
            elif 'face' in unit:
                face_led_idxs = face_idxs[unit.replace('face_', '')]
                leds_frame_idxs += face_led_idxs
                leds_frame_colors += [self.color_nums[int(color)]]*len(face_led_idxs)

        leds_frame_idxs_uq, unique_idx = np.unique(leds_frame_idxs, return_index=True) #drop all the duplicates if we accendetally sets sides and faces etc
        leds_frame_colors = np.array(leds_frame_colors)[unique_idx]

        for led, color in zip(leds_frame_idxs_uq, leds_frame_colors):
            self.setPixelColor(int(led), int(color))
        self.show()

    def set_pixels_color(self, idxs, color):
        if not hasattr(idxs, '__iter__'):
            self._led_data[int(idxs)] = color
        for n in idxs:
            self._led_data[int(n)] = color

    def set_pixels_colors(self, idxs, colors):
        if not hasattr(idxs, '__iter__'):
            self.set_pixels_color(idxs, colors)

        elif not hasattr(colors, '__iter__'):
            for idx in idxs:
                self.set_pixels_color(idx, colors)
        else:
            for idx, color in zip(idxs, colors):
                self.set_pixels_color(idx, color)
