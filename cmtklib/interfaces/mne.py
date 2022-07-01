# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.
"""The MNE module provides Nipype interfaces for MNE tools missing in Nipype or modified."""

import os
import pickle
import warnings
import subprocess

import mne
import numpy as np
import pandas as pd
from nipype.interfaces.base import (
    BaseInterface, BaseInterfaceInputSpec,
    TraitedSpec, traits
)

from cmp import __version__
from cmtklib.bids.io import __cmp_directory__, __freesurfer_directory__


class CreateBEMInputSpec(BaseInterfaceInputSpec):
    subject = traits.Str(desc="subject", mandatory=True)

    bids_dir = traits.Str(desc="base directory", mandatory=True)

    output_query = traits.Dict(desc="BIDSDataGrabber output_query", mandatory=True)

    derivative_list = traits.List(exists=True, desc="List of derivatives to add to the datagrabber", mandatory=True)


class CreateBEMOutputSpec(TraitedSpec):
    output_query = traits.Dict(desc="BIDSDataGrabber output_query", mandatory=True)

    derivative_list = traits.List(exists=True, desc="List of derivatives to add to the datagrabber", mandatory=True)


class CreateBEM(BaseInterface):
    """Use MNE to create the BEM surfaces.

    Examples
    --------
    >>> from cmtklib.interfaces.mne import CreateBEM
    >>> create_bem = CreateBEM()
    >>> create_bem.inputs.subject = 'sub-01'
    >>> create_bem.inputs.bids_dir = '/path/to/bids_dataset'
    >>> create_bem.inputs.output_query = {"src": {"suffix": "src", "extension": ["fif"]}}
    >>> create_bem.inputs.derivative_list = ['cmp-v3.0.3']
    >>> create_bem.run()  # doctest: +SKIP

    References
    ----------
    - https://mne.tools/stable/generated/mne.bem.make_watershed_bem.html

    - https://mne.tools/stable/generated/mne.make_bem_model.html

    - https://mne.tools/stable/generated/mne.write_bem_solution.html

    """

    input_spec = CreateBEMInputSpec
    output_spec = CreateBEMOutputSpec

    def _run_interface(self, runtime):
        subject = self.inputs.subject
        bids_dir = self.inputs.bids_dir
        self.derivative_list = self.inputs.derivative_list
        self.output_query = self.inputs.output_query

        self._create_BEM(subject, bids_dir)

        if __cmp_directory__ not in self.derivative_list:
            self.derivative_list.append(__cmp_directory__)

        self.output_query["bem"] = {"suffix": "bem", "extension": ["fif"]}

        return runtime

    @staticmethod
    def _create_BEM(subject, bids_dir):
        # Create the boundaries between the tissues, using segmentation file
        subjects_dir = os.path.join(bids_dir, "derivatives", __freesurfer_directory__)
        bemfilename = os.path.join(bids_dir, "derivatives", __cmp_directory__, subject, "eeg", subject + "_bem.fif")
        if "bem" not in os.listdir(os.path.join(subjects_dir, subject)):
            mne.bem.make_watershed_bem(
                subject, subjects_dir, overwrite=True
            )  # still need to check if this actually works
            # File names required by mne's make_bem_model not consistent with file names outputted by mne's make_watershed_bem - copy and rename
            for elem in ["inner_skull", "outer_skull", "outer_skin"]:
                elem1 = subject + "_" + elem + "_surface"  # file name used by make_watershed_bem
                elem2 = elem + ".surf"  # file name used by make_bem_model
                if (elem2 not in os.listdir(os.path.join(subjects_dir, subject, "bem"))) and (
                    "watershed" in os.listdir(os.path.join(subjects_dir, subject, "bem"))
                ):
                    cmd = [
                        "cp",
                        os.path.join(subjects_dir, subject, "bem", "watershed", elem1),
                        os.path.join(subjects_dir, subject, "bem", elem2)
                    ]
                    subprocess.run(cmd, capture_output=True)

        if not os.path.exists(bemfilename):
            # Create the conductor model
            conductivity = (0.3, 0.006, 0.3)  # for three layers
            model = mne.make_bem_model(subject=subject, ico=4, conductivity=conductivity, subjects_dir=subjects_dir)
            bem = mne.make_bem_solution(model)
            mne.write_bem_solution(bemfilename, bem)

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["output_query"] = self.output_query
        outputs["derivative_list"] = self.derivative_list
        return outputs


class CreateCovInputSpec(BaseInterfaceInputSpec):
    epochs_fif_fname = traits.File(exists=True, desc="eeg * epochs in .set format", mandatory=True)

    noise_cov_fname = traits.File(
        desc="Location and name to store noise covariance matrix in fif format", mandatory=True
    )


class CreateCovOutputSpec(TraitedSpec):
    has_run = traits.Bool(False, desc="If true, covariance matrix has been produced")

    noise_cov_fname = traits.File(exists=True, desc="Location and name to store noise covariance matrix in fif format")


class CreateCov(BaseInterface):
    """Use MNE to create the noise covariance matrix.

    Examples
    --------
    >>> from cmtklib.interfaces.mne import CreateCov
    >>> create_cov = CreateCov()
    >>> create_cov.inputs.epochs_fif_fname = 'sub-01_epo.fif'
    >>> create_cov.inputs.noise_cov_fname = 'sub-01_noisecov.fif'
    >>> create_cov.run()  # doctest: +SKIP

    References
    ----------
    - https://mne.tools/stable/generated/mne.Covariance.html

    """

    input_spec = CreateCovInputSpec
    output_spec = CreateCovOutputSpec

    def _run_interface(self, runtime):
        epochs_fname = self.inputs.epochs_fif_fname
        self.noise_cov_fname = self.inputs.noise_cov_fname
        if os.path.exists(self.noise_cov_fname):
            self.has_run = True
        else:
            self.has_run = self._create_Cov(epochs_fname, self.noise_cov_fname)

        return runtime

    @staticmethod
    def _create_Cov(epochs_fname, noise_cov_fname):
        # load events and EEG data
        epochs = mne.read_epochs(epochs_fname)
        noise_cov = mne.compute_covariance(
            epochs, keep_sample_mean=True, tmin=-0.2, tmax=0.0, method=["shrunk", "empirical"], verbose=True
        )
        mne.write_cov(noise_cov_fname, noise_cov)
        has_run = True
        return has_run

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["noise_cov_fname"] = self.noise_cov_fname
        outputs["has_run"] = self.has_run
        return outputs


class CreateFwdInputSpec(BaseInterfaceInputSpec):
    fwd_fname = traits.File(desc="Forward solution created with MNE")

    src = traits.List(exists=True, desc="Source space created with MNE", mandatory=True)

    bem = traits.List(exists=True, desc="Boundary surfaces for MNE head model", mandatory=True)

    trans_fname = traits.File(
        exists=True, desc="trans.fif file containing co-registration information (electrodes x MRI)"
    )

    epochs_fif_fname = traits.File(
        desc="eeg * epochs in .fif format, containing information about electrode montage", mandatory=True
    )


class CreateFwdOutputSpec(TraitedSpec):
    has_run = traits.Bool(False, desc="If true, forward solution has been produced")


class CreateFwd(BaseInterface):
    """Use MNE to calculate the forward solution.

    Examples
    --------
    >>> from cmtklib.interfaces.mne import CreateFwd
    >>> create_fwd = CreateFwd()
    >>> create_fwd.inputs.epochs_fif_fname = 'sub-01_epo.fif'
    >>> create_fwd.inputs.fwd_fname = 'sub-01_fwd.fif'
    >>> create_fwd.inputs.src = 'sub-01_src.fif'
    >>> create_fwd.inputs.bem = 'sub-01_bem.fif'
    >>> create_fwd.inputs.trans_fname = 'sub-01_trans.fif'
    >>> create_fwd.run()  # doctest: +SKIP

    References
    ----------
    - https://mne.tools/stable/generated/mne.make_forward_solution.html

    """

    input_spec = CreateFwdInputSpec
    output_spec = CreateFwdOutputSpec

    def _run_interface(self, runtime):

        fwd_fname = self.inputs.fwd_fname
        src = self.inputs.src[0]
        bem = self.inputs.bem[0]
        trans = self.inputs.trans_fname
        epochs_fname = self.inputs.epochs_fif_fname
        epochs = mne.read_epochs(epochs_fname)
        info = epochs.info

        if os.path.exists(fwd_fname):
            self.has_run = True
        else:
            self.has_run = self._create_Fwd(src, bem, trans, info, fwd_fname)

        return runtime

    @staticmethod
    def _create_Fwd(src, bem, trans, info, fwd_fname):
        mindist = 0.0  # 5.0
        fwd = mne.make_forward_solution(
            info, trans=trans, src=src, bem=bem, meg=False, eeg=True, mindist=mindist, n_jobs=4
        )
        mne.write_forward_solution(fwd_fname, fwd, overwrite=True, verbose=None)
        has_run = True
        return has_run

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["has_run"] = self.has_run
        return outputs


class CreateSrcInputSpec(BaseInterfaceInputSpec):
    subject = traits.Str(desc="subject", mandatory=True)

    bids_dir = traits.Str(desc="base directory", mandatory=True)

    output_query = traits.Dict(desc="BIDSDataGrabber output_query", mandatory=True)

    derivative_list = traits.List(exists=True, desc="List of derivatives to add to the datagrabber", mandatory=True)


class CreateSrcOutputSpec(TraitedSpec):
    output_query = traits.Dict(desc="BIDSDataGrabber output_query", mandatory=True)

    derivative_list = traits.List(exists=True, desc="List of derivatives to add to the datagrabber", mandatory=True)


class CreateSrc(BaseInterface):
    """Use MNE to set up bilateral hemisphere surface-based source space with subsampling and write source spaces to a file.

    Examples
    --------
    >>> from cmtklib.interfaces.mne import CreateSrc
    >>> create_src = CreateSrc()
    >>> create_src.inputs.subject = 'sub-01'
    >>> create_src.inputs.bids_dir = '/path/to/bids_dataset'
    >>> create_src.inputs.output_query = {"src": {"suffix": "src", "extension": ["fif"]}}
    >>> create_src.inputs.derivative_list = ['cmp-v3.0.3']
    >>> create_src.run()  # doctest: +SKIP

    References
    ----------
    - https://mne.tools/stable/generated/mne.setup_source_space.html

    - https://mne.tools/stable/generated/mne.write_source_spaces.html

    """

    input_spec = CreateSrcInputSpec
    output_spec = CreateSrcOutputSpec

    def _run_interface(self, runtime):
        subject = self.inputs.subject
        bids_dir = self.inputs.bids_dir

        self.derivative_list = self.inputs.derivative_list
        self.output_query = self.inputs.output_query

        src_fname = os.path.join(bids_dir, "derivatives", __cmp_directory__, subject, "eeg", subject + "_src.fif")
        if not os.path.exists(src_fname):
            self._create_src_space(subject, bids_dir, src_fname)
        if __cmp_directory__ not in self.derivative_list:
            self.derivative_list.append(__cmp_directory__)

        self.output_query["src"] = {"suffix": "src", "extension": ["fif"]}

        return runtime

    @staticmethod
    def _create_src_space(subject, bids_dir, src_fname):
        # from notebook
        overwrite_src = True

        subjects_dir = os.path.join(bids_dir, "derivatives", __freesurfer_directory__)
        src = mne.setup_source_space(subject=subject, spacing="oct6", subjects_dir=subjects_dir)
        mne.write_source_spaces(src_fname, src, overwrite=overwrite_src)

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["output_query"] = self.output_query
        outputs["derivative_list"] = self.derivative_list
        return outputs


class EEGLAB2fifInputSpec(BaseInterfaceInputSpec):
    eeg_ts_file = traits.List(exists=True, desc="eeg * epochs in .set format", mandatory=True)

    behav_file = traits.List(exists=True, desc="epochs metadata in _behav.txt", mandatory=True)

    epochs_fif_fname = traits.File(desc="eeg * epochs in .fif format", mandatory=True)

    electrode_positions_file = traits.File(exists=True, desc="positions of EEG electrodes in a txt file")

    EEG_params = traits.Dict(desc="dictionary defining EEG parameters")

    output_query = traits.Dict(desc="BIDSDataGrabber output_query", mandatory=True)

    derivative_list = traits.List(exists=True, desc="List of derivatives to add to the datagrabber", mandatory=True)


class EEGLAB2fifOutputSpec(TraitedSpec):
    output_query = traits.Dict(desc="BIDSDataGrabber output_query", mandatory=True)

    derivative_list = traits.List(exists=True, desc="List of derivatives to add to the datagrabber", mandatory=True)

    epochs_fif_fname = traits.File(exists=True, desc="eeg * epochs in .fif format", mandatory=True)


class EEGLAB2fif(BaseInterface):
    """Use MNE to convert EEG data from EEGlab to MNE format.

    Examples
    --------
    >>> from cmtklib.interfaces.mne import EEGLAB2fif
    >>> eeglab2fif = EEGLAB2fif()
    >>> eeglab2fif.inputs.eeg_ts_file = ['sub-01_task-faces_desc-preproc_eeg.set']
    >>> eeglab2fif.inputs.behav_file = ['sub-01_task-faces_events.tsv']
    >>> eeglab2fif.inputs.epochs_fif_fname = 'sub-01_epo.fif'
    >>> eeglab2fif.inputs.electrode_positions_file = 'sub-01_eeg.xyz'
    >>> eeglab2fif.inputs.EEG_params = {"expe_name":"faces",
                                        EEG_event_IDs": {"SCRAMBLED":0, "FACES":1},
                                        "start_t":-0.2, "end_t":0.6}
    >>> eeglab2fif.inputs.output_query = {"src": {"suffix": "src", "extension": ["fif"]}}
    >>> eeglab2fif.inputs.derivative_list = ['cmp-v3.0.3']
    >>> eeglab2fif.run()  # doctest: +SKIP

    References
    ----------
    - https://mne.tools/stable/generated/mne.read_epochs_eeglab.html

    - https://mne.tools/stable/generated/mne.channels.make_dig_montage.html

    - https://mne.tools/stable/generated/mne.Epochs.html?highlight=set_montage#mne.Epochs.set_montage

    - https://mne.tools/stable/generated/mne.Epochs.html?highlight=set_montage#mne.Epochs.save

    """

    input_spec = EEGLAB2fifInputSpec
    output_spec = EEGLAB2fifOutputSpec

    def _run_interface(self, runtime):
        epochs_file = self.inputs.eeg_ts_file[0]
        behav_file = self.inputs.behav_file[0]
        montage_fname = self.inputs.electrode_positions_file
        EEG_params = self.inputs.EEG_params
        self.epochs_fif_fname = self.inputs.epochs_fif_fname
        self.derivative_list = self.inputs.derivative_list
        self.output_query = self.inputs.output_query
        if not os.path.exists(self.epochs_fif_fname):
            self._convert_eeglab2fif(epochs_file, behav_file, self.epochs_fif_fname, montage_fname, EEG_params)
        self.derivative_list.append(f"cmp-{__version__}")
        self.output_query["EEG"] = {"suffix": "epo", "extension": ["fif"]}
        return runtime

    @staticmethod
    def _convert_eeglab2fif(epochs_file, behav_file, epochs_fif_fname, montage_fname, EEG_params):
        behav = pd.read_csv(behav_file, sep="\t")
        behav = behav[behav.bad_epoch == 0]
        with warnings.catch_warnings(): # suppress some irrelevant warnings coming from mne.read_epochs_eeglab()
            warnings.simplefilter("ignore")
            epochs = mne.read_epochs_eeglab(
                epochs_file, events=None, event_id=None, eog=(), verbose=None, uint16_codec=None
            )
        epochs.events[:, 2] = list(behav.iloc[:, 3])
        epochs.event_id = EEG_params["EEG_event_IDs"]

        # apply user-defined EEG parameters
        start_t = EEG_params["start_t"]
        end_t = EEG_params["end_t"]
        epochs.apply_baseline((start_t, 0))
        epochs.set_eeg_reference(ref_channels="average", projection=True)
        epochs.crop(tmin=start_t, tmax=end_t)

        # in case electrode position file was supplied, create info object
        # with information about electrode positions
        try:
            n = int(open(montage_fname).readline().lstrip().split(" ")[0])
        except Exception as e:
            print(e)
        else:
            all_coord = np.loadtxt(montage_fname, skiprows=1, usecols=(0, 1, 2), max_rows=n)
            all_names = np.loadtxt(montage_fname, skiprows=1, usecols=3, max_rows=n, dtype=np.dtype(str)).tolist()
            all_coord = list(map(lambda x: x / 1000, all_coord))
            ch_coord = [all_coord[idx] for idx, chan in enumerate(all_names) if chan not in ["lpa", "rpa", "nasion"]]
            # overwrite channel names?
            ch_names = [all_names[idx] for idx, chan in enumerate(all_names) if chan not in ["lpa", "rpa", "nasion"]]

            # create the montage object with the channel names and positions
            # read from the file
            montage = mne.channels.make_dig_montage(ch_pos=dict(zip(ch_names, ch_coord)), coord_frame="head")
            epochs.info.set_montage(montage)

        epochs.save(epochs_fif_fname, overwrite=True)

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["epochs_fif_fname"] = self.epochs_fif_fname
        outputs["output_query"] = self.output_query
        outputs["derivative_list"] = self.derivative_list
        return outputs


class MNEInverseSolutionInputSpec(BaseInterfaceInputSpec):
    subject = traits.Str(desc="Subject", mandatory=True)

    bids_dir = traits.Str(desc="Base directory", mandatory=True)

    epochs_fif_fname = traits.File(exists=True, desc="eeg * epochs in .fif format", mandatory=True)

    src_file = traits.List(exists=True, desc="Source space created with MNE", mandatory=True)

    bem_file = traits.List(exists=True, desc="Surfaces for head model", mandatory=True)

    cov_has_run = traits.Bool(desc="Indicate if covariance matrix has been produced", mandatory=True)

    noise_cov_fname = traits.File(exists=True, desc="Noise covariance matrix in fif format", mandatory=True)

    fwd_has_run = traits.Bool(desc="Indicate if forward solution has been produced")

    fwd_fname = traits.File(desc="Forward solution in fif format", mandatory=True)

    inv_fname = traits.File(desc="Inverse operator in fif format", mandatory=True)

    parcellation = traits.Str(desc="Parcellation scheme")

    roi_ts_file = traits.File(exists=False, desc="rois * time series in .npy format")


class MNEInverseSolutionOutputSpec(TraitedSpec):
    roi_ts_file = traits.File(exists=True, desc="rois * time series in .npy format")

    fwd_fname = traits.File(exists=True, desc="Forward solution in fif format", mandatory=True)


class MNEInverseSolution(BaseInterface):
    """Use MNE to convert EEG data from EEGlab to MNE format.

    Examples
    --------
    >>> from cmtklib.interfaces.mne import MNEInverseSolution
    >>> inv_sol = MNEInverseSolution()
    >>> inv_sol.inputs.subject = 'sub-01'
    >>> inv_sol.inputs.bids_dir = '/path/to/bids_dataset'
    >>> inv_sol.inputs.epochs_fif_fname = 'sub-01_epo.fif'
    >>> inv_sol.inputs.src_file = ['sub-01_src.fif']
    >>> inv_sol.inputs.bem_file = ['sub-01_bem.fif']
    >>> inv_sol.inputs.cov_has_run = 'True'
    >>> inv_sol.inputs.noise_cov_fname = 'sub-01_noisecov.fif'
    >>> inv_sol.inputs.fwd_has_run = 'True'
    >>> inv_sol.inputs.fwd_fname = 'sub-01_fwd.fif'
    >>> inv_sol.inputs.inv_fname = 'sub-01_inv.fif'
    >>> inv_sol.inputs.parcellation = 'lausanne2018.scale1'
    >>> inv_sol.inputs.roi_ts_file = 'sub-01_atlas-L2018_res-scale1_desc-epo_timeseries.npy'
    >>> inv_sol.run()  # doctest: +SKIP

    References
    ----------
    - https://mne.tools/stable/generated/mne.read_forward_solution.html

    - https://mne.tools/stable/generated/mne.minimum_norm.make_inverse_operator.html

    - https://mne.tools/stable/generated/mne.minimum_norm.apply_inverse_epochs.html

    - https://mne.tools/stable/generated/mne.read_labels_from_annot.html

    - https://mne.tools/stable/generated/mne.extract_label_time_course.html

    """

    input_spec = MNEInverseSolutionInputSpec
    output_spec = MNEInverseSolutionOutputSpec

    def _run_interface(self, runtime):
        bids_dir = self.inputs.bids_dir
        subject = self.inputs.subject
        epochs_file = self.inputs.epochs_fif_fname
        src_file = self.inputs.src_file[0]
        self.fwd_fname = self.inputs.fwd_fname
        inv_fname = self.inputs.inv_fname
        noise_cov_fname = self.inputs.noise_cov_fname
        parcellation = self.inputs.parcellation
        self.roi_ts_file = self.inputs.roi_ts_file

        # temporary workaround until harmonized with invsol (cartool):
        # want to use pickle so labels can be saved alongside time courses
        if self.roi_ts_file[-3:] == "npy":
            self.roi_ts_file = self.roi_ts_file[:-3] + "pkl"

        if not os.path.exists(self.roi_ts_file):
            roi_tcs = self._createInv_MNE(
                bids_dir, subject, epochs_file, self.fwd_fname, noise_cov_fname, src_file, parcellation, inv_fname
            )

            with open(self.roi_ts_file, "wb") as f:
                pickle.dump(roi_tcs, f, pickle.HIGHEST_PROTOCOL)
            # np.save(self.roi_ts_file, roi_tcs)

        return runtime

    @staticmethod
    def _createInv_MNE(
        bids_dir, subject, epochs_file, fwd_fname, noise_cov_fname, src_file, parcellation, inv_fname
    ):
        epochs = mne.read_epochs(epochs_file)
        fwd = mne.read_forward_solution(fwd_fname)
        noise_cov = mne.read_cov(noise_cov_fname)
        src = mne.read_source_spaces(src_file, patch_stats=False, verbose=None)
        # compute the inverse operator
        inverse_operator = mne.minimum_norm.make_inverse_operator(
            epochs.info, fwd, noise_cov, loose=1, depth=None, fixed=False
        )
        # inverse_operator = mne.minimum_norm.make_inverse_operator(
        #     epochs.info, fwd, noise_cov, loose=0, depth=None, fixed=True)
        mne.minimum_norm.write_inverse_operator(inv_fname, inverse_operator)
        # compute the time courses of the source points
        # some parameters
        method = "sLORETA"
        snr = 3.0
        lambda2 = 1.0 / snr ** 2
        evoked = epochs.average().pick("eeg")
        # stcs, inverse_matrix = my_mne_minimum_norm_inverse.apply_inverse_epochs(
        #   epochs, inverse_operator, lambda2, method, pick_ori="normal", nave=evoked.nave,return_generator=False
        # )
        stcs = mne.minimum_norm.apply_inverse_epochs(
            epochs, inverse_operator, lambda2, method, pick_ori=None, nave=evoked.nave, return_generator=False
        )
        # get ROI time courses
        # read the labels of the source points
        subjects_dir = os.path.join(bids_dir, "derivatives", __freesurfer_directory__)
        labels_parc = mne.read_labels_from_annot(subject, parc=parcellation, subjects_dir=subjects_dir)
        # get the ROI time courses
        data = mne.extract_label_time_course(
            stcs, labels_parc, src, mode="pca_flip", allow_empty=True, return_generator=False
        )

        roi_tcs = dict()
        roi_tcs["data"] = data
        roi_tcs["labels"] = labels_parc

        return roi_tcs

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["fwd_fname"] = self.fwd_fname
        outputs["roi_ts_file"] = self.roi_ts_file
        return outputs
