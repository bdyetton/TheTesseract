import pandas as pd
import glob
import numpy as np
import os
import pickle


def parse_str_list(str_list):
    list_strs = str_list.lstrip('[').rstrip(']').replace("'", '').replace(' ','').split(',')
    return [s for s in list_strs if s != '']


class RoutineManager():
    def __init__(self, starting_rt='TwinkleAll_high_rt', compile_routines=False):
        rt_files = sorted(glob.iglob('routines/*_rt.txt'), key=os.path.getmtime, reverse=True)
        if compile_routines:
            self._init_rt_status(rt_files)  # Uncomment to refresh routines  #TODO do init of all rts in rt_status here
        #TODO Look like there might be some error here still.... i have to init every time
        self.rt_status = self._load_rt_status()
        self.rt_name = starting_rt
        self.rts = {}
        self.rts_by_type = {
            'base':[],
            'high':[],
            'med':[],
            'low':[],
            'build':[]
        }
        self.rts_beatified = {}
        self.beat = -1
        self.rts_inited = False
        rt_parents_that_need_updating = []
        for rt_file in rt_files:
            rt_name = rt_file.replace('.txt', '').replace('routines/','')
            for rt_type in self.rts_by_type.keys(): # place in correct type based on filename
                if '_'+rt_type+'_' in rt_name:
                    self.rts_by_type[rt_type].append(rt_name)
            rt_never_pkled = np.isnan(self.rt_status.loc[rt_name, 'date_created'])
            rt_is_outdated = (self.rt_status.loc[rt_name, 'date_created'] < os.path.getmtime(rt_file))
            rt_child_was_updated = (rt_name in rt_parents_that_need_updating) #check if child was updated, and therefore parent should be
            if rt_never_pkled or rt_is_outdated or rt_child_was_updated:
                rt_parents_that_need_updating += self.rt_status.loc[rt_name, 'parents']
                rt = pd.read_csv(rt_file, delimiter='\t')
                rt = rt.set_index(['device', 'var'])
                rt = rt.T.reset_index(drop=True).T
                self.rts[rt_name] = rt #if a parent is here, then
            else:
                self.rts_beatified[rt_name] = pickle.load(open(rt_file.replace('.txt', '.pkl'),'rb'))
        self._expand_all_rt_frames()
        self._add_all_off_signals()
        self._beatify_routines()
        self.rt_status.to_csv('routines/rt_status.txt', sep='\t')
        self.rts_inited = True
        del self.rts  # to save memory (all have been beatified at this point)

    def get_frames_for_next_beat(self):
        return self.rts_beatified[self.rt_name][self.beat]

    def update_beat(self):
        self.beat += 1
        if self.beat >= len(self.rts_beatified[self.rt_name]):
            self.beat = 0

    def set_routine(self, rt):
        self.rt_name = rt

    def select_rand_routine_by_type(self, rt_type):
        """rt types are base, high, med, low (intensity)"""
        try:
            pos_choice = self.rts_by_type[rt_type].copy()
            self.set_routine(np.random.choice(pos_choice))
        except ValueError:
            print('No routines of that type, not selecting a new routine')

    def _load_rt_status(self):
        rt_status = pd.read_csv('routines/rt_status.txt', sep='\t').set_index('rt_name')
        rt_status['parents'] = rt_status['parents'].apply(parse_str_list)
        return rt_status

    def _init_rt_status(self, rt_files):
        pkls = glob.iglob('routines/*.pkl')
        [os.remove(pkl) for pkl in pkls]
        status = glob.iglob('routines/rt_status.txt')
        [os.remove(statu) for statu in status]
        rt_names = [rt_file.replace('.txt', '').replace('routines/', '') for rt_file in rt_files]
        rt_status = pd.DataFrame({'rt_name': rt_names}).set_index('rt_name')
        rt_status['date_created'] = np.nan
        rt_status['parents'] = np.empty((len(rt_status), 0)).tolist()
        rt_status.to_csv('routines/rt_status.txt', sep='\t')

    def _get_frames_for_beat(self, beat, rt_name):
        rt = self.rts[rt_name]
        slice = (rt.loc[('all', 'start_beat'), :] < beat+1) & (rt.loc[('all', 'start_beat'), :] >= beat)
        rt_slice = rt.loc[:, slice]
        ret = []
        for idx in rt_slice:
            df = rt_slice[idx].to_frame()
            df = df.dropna()
            ret.append(df.groupby(level=0).apply(lambda df: df.xs(df.name)[idx].to_dict()).to_dict())
        return ret

    def _beatify_routines(self):
        """This preprocesses the routines for each beat, thereby speeding the whole thing up when actually looping"""
        for rt_name, rt in self.rts.items():
            end = rt.shape[1] - 1
            seq = []
            #TODO when compling has moved off
            #FIXME these convertions to float should not be required, but the import is generating str's in some places for some reason
            for beat in range(0, int(round(float(rt.ix[('all', 'start_beat'), end])+float(rt.ix[('all', 'beats'), end])))):
                seq.append(self._get_frames_for_beat(beat, rt_name))
            self.rts_beatified[rt_name] = seq
            pickle.dump(seq, open('routines/'+rt_name+'.pkl', "wb"))
            print('Created', rt_name)
            self.rt_status.loc[rt_name, 'date_created'] = os.path.getmtime('routines/'+rt_name+'.pkl')

    def _expand_all_rt_frames(self):
        for rt_name, rt in self.rts.items():
            frame_container = []
            frame_idx = 0
            frame = np.nan
            while frame is not None:
                frame = self._get_frame(frame_idx, rt_name)
                frame_idx += 1
                frame_container.append(frame)
            df = pd.concat(frame_container, axis=1)
            df.columns = [idx for idx, val in enumerate(df.columns)]
            start_beat = [0]+list(np.cumsum(df.loc[('all', 'beats'),:].astype(float)).values[:-1])
            df.loc[('all', 'start_beat'), :] = np.array(start_beat)
            self.rts[rt_name] = df

    def _add_all_off_signals(self):
        """After we turn on a led, if we encounter a nan right after, this needs to be interpreted as a off signal"""
        for rt_name, rt in self.rts.items():
            null_locs = rt.isnull()
            command_locs = ~null_locs
            command_locs.loc[~rt.index.get_level_values(0).isin(['leds','laser']),:] = False
            command_locs.loc[('leds','bright'), :] = False
            cols = command_locs.columns.tolist()
            cols = cols[-1:] + cols[:-1]
            command_locs = command_locs[cols]
            self.rts[rt_name] = rt.mask(command_locs.values & null_locs.values, other=0)

    def _get_frame(self, frame, rt):
        if frame >= self.rts[rt].shape[1]:
            return None
        #expand routine dataframe if nessary
        self.rts[rt] = self._expand_frame(rt, frame) #FIXME this looks like it could be optimized
        return self.rts[rt].ix[:, frame]
        # df = df.dropna()
        # return df.groupby(level=0).apply(lambda df: df.xs(df.name).to_dict()).to_dict()

    def _expand_frame(self, rt, frame):
        if rt not in self.rts: #Hack to deal with bad logic. FIXME after moving compile to laptop
            rt_data = pd.read_csv('routines/'+rt+'.txt', delimiter='\t')
            rt_data = rt_data.set_index(['device', 'var'])
            rt_data = rt_data.T.reset_index(drop=True).T
        else:
            rt_data = self.rts[rt]

        if not pd.isnull(rt_data.ix[('all','routine'), frame]):
            len_to_rep = int(rt_data.ix[('all','beats'), frame])
            done = rt_data.ix[:, :frame-1]
            rt_str_to_expand = rt_data.ix[('all', 'routine'), frame]
            current_cont = []
            for rt_to_expand in rt_str_to_expand.lstrip('[').rstrip(']').replace(' ','').split(','):
                if rt not in self.rt_status.loc[rt_to_expand, 'parents']:
                    self.rt_status.loc[rt_to_expand, 'parents'].append(rt)
                current = self._expand_frame(rt_to_expand, 0)
                current = self._slice_or_expand_to_higher_order_beat_size(current, len_to_rep)
                top_current = current.loc[[('all','beats'), ('all','routine')], :]
                bottom_current = current.drop('all', axis=0)
                bottom_current = bottom_current.dropna(how='all', axis=0)
                current_cont.append(bottom_current)
            current_cont = [top_current]+current_cont
            current_all = pd.concat(current_cont, axis=0)
            todo = rt_data.ix[:, frame+1:]
            current_all = current_all[~current_all.index.duplicated(keep='first')]
            new_frame = pd.concat([done, current_all, todo], axis=1)
            return new_frame.T.reset_index(drop=True).T
        else:
            return rt_data

    def _slice_or_expand_to_higher_order_beat_size(self, rt, len_to_rep):
        rt_start_beat = np.array([0] + list(np.cumsum(rt.loc[('all', 'beats'), :]).values[1:]))
        if rt_start_beat[-1] < len_to_rep: #to small
            reps = int(len_to_rep / rt_start_beat[-1])
            rem = len_to_rep - rt_start_beat[-1]*reps
            rt = pd.concat([rt] * reps, ignore_index=True, axis=1)
            slice_idx = np.where(rt_start_beat > rem)[0][0]+1
            rem_slice = rt.iloc[:, 0:slice_idx]
            return pd.concat([rt, rem_slice], ignore_index=True, axis=1)
        if rt_start_beat[-1] > len_to_rep: #to big
            slice_idx = np.where(rt_start_beat > len_to_rep)[0][0]
            return rt.iloc[:, 0:slice_idx]
        else:
            return rt





