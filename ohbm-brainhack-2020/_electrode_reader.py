import json
from collections import OrderedDict

import mne
import numpy as np
from mne.io.constants import FIFF
from mne.utils import _check_ch_locs, logger, warn
from _tsv_handler import _from_tsv
from _montages import make_dig_montage, set_montage

def _handle_electrodes_reading(electrodes_fname, coord_frame,
                               coord_unit, raw, verbose):
    """Read associated electrodes.tsv and populate raw.
    Handle xyz coordinates and coordinate frame of each channel.
    Assumes units of coordinates are in 'm'.
    """
    logger.info('Reading electrode '
                'coords from {}.'.format(electrodes_fname))
    electrodes_dict = _from_tsv(electrodes_fname)
    # First, make sure that ordering of names in channels.tsv matches the
    # ordering of names in the raw data. The "name" column is mandatory in BIDS
    ch_names_raw = list(raw.ch_names)
    ch_names_tsv = electrodes_dict['name']

    if ch_names_raw != ch_names_tsv:
        msg = ('Channels do not correspond between raw data and the '
               'channels.tsv file. For MNE-BIDS, the channel names in the '
               'tsv MUST be equal and in the same order as the channels in '
               'the raw data.\n\n'
               '{} channels in tsv file: "{}"\n\n --> {}\n\n'
               '{} channels in raw file: "{}"\n\n --> {}\n\n'
               .format(len(ch_names_tsv), electrodes_fname, ch_names_tsv,
                       len(ch_names_raw), raw.filenames, ch_names_raw)
               )

        # XXX: this could be due to MNE inserting a 'STI 014' channel as the
        # last channel: In that case, we can work. --> Can be removed soon,
        # because MNE will stop the synthesis of stim channels in the near
        # future
        if not (ch_names_raw[-1] == 'STI 014' and
                ch_names_raw[:-1] == ch_names_tsv):
            raise RuntimeError(msg)

    if verbose:
        summary_str = [(ch, coord) for idx, (ch, coord)
                       in enumerate(electrodes_dict.items())
                       if idx < 5]
        print("The read in electrodes file is: \n", summary_str)

    def _float_or_nan(val):
        if val == "n/a":
            return np.nan
        else:
            return float(val)

    # convert coordinates to float and create list of tuples
    electrodes_dict['x'] = [_float_or_nan(x) for x in electrodes_dict['x']]
    electrodes_dict['y'] = [_float_or_nan(x) for x in electrodes_dict['y']]
    electrodes_dict['z'] = [_float_or_nan(x) for x in electrodes_dict['z']]
    
    if coord_frame in ['ARS']:
        tmp_x = np.copy(electrodes_dict['x'])
        tmp_y = np.copy(electrodes_dict['y'])
        electrodes_dict['x'] = tmp_y 
        electrodes_dict['y'] = tmp_x 
        coord_frame = 'head'
       
    if ch_names_raw[-1] in ['STI 014']:
        ch_names_raw = [x.encode('utf-8') for i, x in enumerate(ch_names_raw[:-1])
                    if (electrodes_dict['x'][i] != "n/a")]

    else:
        ch_names_raw = [x.encode('utf-8') for i, x in enumerate(ch_names_raw)
                    if (electrodes_dict['x'][i] != "n/a")]
        
    ch_locs = np.c_[electrodes_dict['x'],
                    electrodes_dict['y'],
                    electrodes_dict['z']]

    # determine if there are problematic channels
    nan_chs = []
    for ch_name, ch_coord in zip(ch_names_raw, ch_locs):
        if any(np.isnan(ch_coord)) and ch_name not in raw.info['bads']:
            nan_chs.append(ch_name)
    if len(nan_chs) > 0:
        warn("There are channels without locations "
             "(n/a) that are not marked as bad: {}".format(nan_chs))

    # convert coordinates to meters
    ch_locs = _scale_coord_to_meters(ch_locs, coord_unit)

    # create mne.DigMontage
    ch_pos = dict(zip(ch_names_raw, ch_locs))
    montage = make_dig_montage(ch_pos=ch_pos,
                                            coord_frame=coord_frame)
    raw.set_montage(montage)
    return raw

def _scale_coord_to_meters(coord, unit):
    """Scale units to meters (mne-python default)."""
    if unit == 'cm':
        return np.divide(coord, 100.)
    elif unit == 'mm':
        return np.divide(coord, 1000.)
    else:
        return coord
