"""MNE software for easily interacting with BIDS compatible datasets."""

__version__ = '0.5.dev0'


from mne_bids.read import (read_raw_bids, get_head_mri_trans,  # noqa: F401
                           get_matched_empty_room)  # noqa: F401
from mne_bids.utils import make_bids_folders, make_bids_basename  # noqa: F401
from mne_bids import commands  # noqa: F401
