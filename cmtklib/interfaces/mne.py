# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.
"""The MNE module provides Nipype interfaces for MNE tools missing in Nipype or modified."""

# General imports
import csv
import os
import warnings
import subprocess
import numpy as np
import pandas as pd
import scipy.io as sio

# Nipype imports
from nipype.interfaces.base import (
    BaseInterface, BaseInterfaceInputSpec,
    TraitedSpec, traits, OutputMultiPath, File
)

# MNE imports
import mne
import mne_connectivity as mnec

# Own imports
from cmtklib.eeg import save_eeg_connectome_file


class CreateBEMInputSpec(BaseInterfaceInputSpec):
    fs_subject = traits.Str(desc="FreeSurfer subject ID", mandatory=True)

    fs_subjects_dir = traits.Directory(desc="Freesurfer subjects (derivatives) directory",
                                       exists=True,
                                       mandatory=True)

    out_bem_fname = traits.Str(desc="Name of output BEM file in fif format", mandatory=True)


class CreateBEMOutputSpec(TraitedSpec):
    bem_file = traits.File(desc="Path to output BEM file in fif format")


class CreateBEM(BaseInterface):
    """Use MNE to create the BEM surfaces.

    Examples
    --------
    >>> from cmtklib.interfaces.mne import CreateBEM
    >>> create_bem = CreateBEM()
    >>> create_bem.inputs.fs_subject = 'sub-01'
    >>> create_bem.inputs.fs_subjects_dir = '/path/to/bids_dataset/derivatives/freesurfer-7.1.1'
    >>> create_bem.inputs.out_bem_fname = 'bem.fif'
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
        self._create_bem(
            self.inputs.fs_subject,
            self.inputs.fs_subjects_dir,
            self._gen_output_filename_bem()
        )
        return runtime

    @staticmethod
    def _create_bem(fs_subject, fs_subjects_dir, out_bem_file):
        # Create the boundaries between the tissues, using segmentation file
        if "bem" not in os.listdir(os.path.join(fs_subjects_dir, fs_subject)):
            mne.bem.make_watershed_bem(
                fs_subject, fs_subjects_dir, overwrite=True
            )  # still need to check if this actually works
            # File names required by mne's make_bem_model not consistent with file names outputted by mne's make_watershed_bem - copy and rename
            for elem in ["inner_skull", "outer_skull", "outer_skin"]:
                elem1 = fs_subject + "_" + elem + "_surface"  # file name used by make_watershed_bem
                elem2 = elem + ".surf"  # file name used by make_bem_model
                if (elem2 not in os.listdir(os.path.join(fs_subjects_dir, fs_subject, "bem"))) and (
                    "watershed" in os.listdir(os.path.join(fs_subjects_dir, fs_subject, "bem"))
                ):
                    cmd = [
                        "cp",
                        os.path.join(fs_subjects_dir, fs_subject, "bem", "watershed", elem1),
                        os.path.join(fs_subjects_dir, fs_subject, "bem", elem2)
                    ]
                    subprocess.run(cmd, capture_output=True)

        # Create the conductor model
        # TODO: Add conductivity as input / parameter
        conductivity = (0.3, 0.006, 0.3)  # for three layers
        model = mne.make_bem_model(subject=fs_subject, ico=4, conductivity=conductivity, subjects_dir=fs_subjects_dir)
        bem = mne.make_bem_solution(model)
        mne.write_bem_solution(out_bem_file, bem)

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["bem_file"] = self._gen_output_filename_bem()
        return outputs

    def _gen_output_filename_bem(self):
        # Return the absolute path of the output BEM file
        return os.path.abspath(self.inputs.out_bem_fname)


class CreateCovInputSpec(BaseInterfaceInputSpec):
    epochs_file = traits.File(exists=True, desc="eeg * epochs in .set format", mandatory=True)

    out_noise_cov_fname = traits.Str(
        desc="Name of output file to save noise covariance matrix in fif format", mandatory=True
    )


class CreateCovOutputSpec(TraitedSpec):

    noise_cov_file = traits.File(desc="Location and name to store noise covariance matrix in fif format")


class CreateCov(BaseInterface):
    """Use MNE to create the noise covariance matrix.

    Examples
    --------
    >>> from cmtklib.interfaces.mne import CreateCov
    >>> create_cov = CreateCov()
    >>> create_cov.inputs.epochs_file = '/path/to/sub-01_epo.fif'
    >>> create_cov.inputs.out_noise_cov_fname = 'sub-01_noisecov.fif'
    >>> create_cov.run()  # doctest: +SKIP

    References
    ----------
    - https://mne.tools/stable/generated/mne.Covariance.html

    """

    input_spec = CreateCovInputSpec
    output_spec = CreateCovOutputSpec

    def _run_interface(self, runtime):
        noise_cov = self._create_cov(self.inputs.epochs_file)
        mne.write_cov(self._gen_output_filename_noise_cov(), noise_cov)
        return runtime

    @staticmethod
    def _create_cov(epochs_file):
        # load events and EEG data
        epochs = mne.read_epochs(epochs_file)
        # TODO: Add compute_covariance parameters as inputs of interface
        return mne.compute_covariance(
            epochs, keep_sample_mean=True, tmin=-0.2, tmax=0.0, method=["shrunk", "empirical"], verbose=True
        )

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["noise_cov_file"] = self._gen_output_filename_noise_cov()
        return outputs

    def _gen_output_filename_noise_cov(self):
        # Return the absolute path of the output noise covariance file
        return os.path.abspath(self.inputs.out_noise_cov_fname)


class CreateFwdInputSpec(BaseInterfaceInputSpec):
    src_file = traits.File(exists=True, desc="Source space file in fif format", mandatory=True)

    bem_file = traits.File(
        exists=True, desc="Boundary surfaces for MNE head model in fif format", mandatory=True
    )

    trans_file = traits.File(
        exists=True, desc="trans.fif file containing co-registration information (electrodes x MRI)"
    )

    epochs_file = traits.File(
        exists=True,
        desc="eeg * epochs in .fif format, containing information about electrode montage",
        mandatory=True
    )

    out_fwd_fname = traits.Str(desc="Name of output forward solution file created with MNE")


class CreateFwdOutputSpec(TraitedSpec):
    fwd_file = traits.File(desc="Path to generated forward solution file in fif format")


class CreateFwd(BaseInterface):
    """Use MNE to calculate the forward solution.

    Examples
    --------
    >>> from cmtklib.interfaces.mne import CreateFwd
    >>> create_fwd = CreateFwd()
    >>> create_fwd.inputs.epochs_file = '/path/to/sub-01_epo.fif'
    >>> create_fwd.inputs.out_fwd_fname = 'sub-01_fwd.fif'
    >>> create_fwd.inputs.src_file = '/path/to/sub-01_src.fif'
    >>> create_fwd.inputs.bem_file = '/path/to/sub-01_bem.fif'
    >>> create_fwd.inputs.trans_file = '/path/to/sub-01_trans.fif'
    >>> create_fwd.run()  # doctest: +SKIP

    References
    ----------
    - https://mne.tools/stable/generated/mne.make_forward_solution.html

    """

    input_spec = CreateFwdInputSpec
    output_spec = CreateFwdOutputSpec

    def _run_interface(self, runtime):
        fwd = self._create_fwd(
            self.inputs.src_file,
            self.inputs.bem_file,
            self.inputs.trans_file,
            self.inputs.epochs_file
        )
        mne.write_forward_solution(
            self._gen_output_filename_fwd(), fwd, overwrite=True, verbose=None
        )
        return runtime

    @staticmethod
    def _create_fwd(src_file, bem_file, trans_file, epochs_file, mindist=0.0):
        # TODO: Add mindist as input parameter
        epochs_info = mne.read_epochs(epochs_file).info
        return mne.make_forward_solution(
            epochs_info,
            trans=trans_file,
            src=src_file,
            bem=bem_file,
            meg=False,
            eeg=True,
            mindist=mindist, n_jobs=4
        )

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["fwd_file"] = self._gen_output_filename_fwd()
        return outputs

    def _gen_output_filename_fwd(self):
        # Return the absolute path of the output forward solution file
        return os.path.abspath(self.inputs.out_fwd_fname)


class CreateSrcInputSpec(BaseInterfaceInputSpec):
    fs_subject = traits.Str(desc="FreeSurfer subject ID", mandatory=True)

    fs_subjects_dir = traits.Directory(desc="Freesurfer subjects (derivatives) directory",
                                       exists=True,
                                       mandatory=True)

    out_src_fname = traits.Str(desc="Name of output source space file created with MNE")

    overwrite = traits.Bool(True, desc="Overwrite source space file if already existing")


class CreateSrcOutputSpec(TraitedSpec):
    src_file = traits.File(desc="Path to output source space files in fif format")


class CreateSrc(BaseInterface):
    """Use MNE to set up bilateral hemisphere surface-based source space with subsampling and write source spaces to a file.

    Examples
    --------
    >>> from cmtklib.interfaces.mne import CreateSrc
    >>> create_src = CreateSrc()
    >>> create_src.inputs.fs_subject = 'sub-01'
    >>> create_src.inputs.fs_subjects_dir = '/path/to/bids_dataset/derivatives/freesurfer-7.1.1'
    >>> create_src.inputs.out_src_fname = 'sub-01_src.fif'
    >>> create_src.run()  # doctest: +SKIP

    References
    ----------
    - https://mne.tools/stable/generated/mne.setup_source_space.html

    - https://mne.tools/stable/generated/mne.write_source_spaces.html

    """

    input_spec = CreateSrcInputSpec
    output_spec = CreateSrcOutputSpec

    def _run_interface(self, runtime):
        src = self._create_src_space(
            self.inputs.fs_subject,
            self.inputs.fs_subjects_dir
        )
        mne.write_source_spaces(
            self._gen_output_filename_src(),
            src,
            overwrite=self.inputs.overwrite
        )
        return runtime

    @staticmethod
    def _create_src_space(fs_subject, fs_subjects_dir):
        return mne.setup_source_space(
            subject=fs_subject, spacing="oct6", subjects_dir=fs_subjects_dir
        )

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["src_file"] = self._gen_output_filename_src()
        return outputs

    def _gen_output_filename_src(self):
        # Return the absolute path of the output forward solution file
        return os.path.abspath(self.inputs.out_src_fname)


class EEGLAB2fifInputSpec(BaseInterfaceInputSpec):
    eeg_ts_file = traits.File(exists=True, desc="eeg * epochs in .set format", mandatory=True)

    events_file = traits.File(exists=True, desc="epochs metadata in _behav.txt", mandatory=True)

    electrodes_file = traits.File(exists=True, desc="positions of EEG electrodes in a txt file")

    t_min = traits.Float(-0.2, desc="Start time of the epochs in seconds, relative to the time-locked event.")
    t_max = traits.Float(0.5, desc="End time of the epochs in seconds, relative to the time-locked event.")
    event_ids = traits.Dict(
        None,
        desc="The id of the events to consider in `dict` form. "
             "The keys of the `dict` can later be used to access associated events. "
             "If None, all events will be used and a dict is created with string integer "
             "names corresponding to the event id integers."
    )

    out_epochs_fif_fname = traits.Str(
        desc="Output filename for eeg * epochs in .fif format, e.g. sub-01_epo.fif",
        mandatory=True
    )


class EEGLAB2fifOutputSpec(TraitedSpec):
    epochs_file = traits.File(exists=True, desc="eeg * epochs in .fif format", mandatory=True)


class EEGLAB2fif(BaseInterface):
    """Use MNE to convert EEG data from EEGlab to MNE format.

    Examples
    --------
    >>> from cmtklib.interfaces.mne import EEGLAB2fif
    >>> eeglab2fif = EEGLAB2fif()
    >>> eeglab2fif.inputs.eeg_ts_file = ['sub-01_task-faces_desc-preproc_eeg.set']
    >>> eeglab2fif.inputs.events_file = ['sub-01_task-faces_events.tsv']
    >>> eeglab2fif.inputs.out_epochs_fif_fname = 'sub-01_epo.fif'
    >>> eeglab2fif.inputs.electrodes_file = 'sub-01_eeg.xyz'
    >>> eeglab2fif.inputs.event_ids = {"SCRAMBLED":0, "FACES":1}
    >>> eeglab2fif.inputs.t_min = -0.2
    >>> eeglab2fif.inputs.t_max = 0.6
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
        print(self.inputs)
        self._convert_eeglab2fif(
            self.inputs.eeg_ts_file,
            self.inputs.events_file,
            self.inputs.electrodes_file,
            self.inputs.event_ids,
            self.inputs.t_min,
            self.inputs.t_max,
            self._gen_output_filename()
        )
        return runtime

    @staticmethod
    def _convert_eeglab2fif(epochs_file, event_file, montage_fname, event_id, tmin, tmax, epochs_fif_fname, overwrite=True):
        behav = pd.read_csv(event_file, sep="\t")
        behav = behav[behav.bad_epoch == 0]
        with warnings.catch_warnings(): # suppress some irrelevant warnings coming from mne.read_epochs_eeglab()
            warnings.simplefilter("ignore")
            epochs = mne.read_epochs_eeglab(
                epochs_file, events=None, event_id=None, eog=(), verbose=None, uint16_codec=None
            )
        epochs.events[:, 2] = list(behav.iloc[:, 3])
        epochs.event_id = event_id

        # Apply user-defined parameters for epoch extraction
        epochs.apply_baseline((tmin, 0))
        epochs.set_eeg_reference(ref_channels="average", projection=True)
        epochs.crop(tmin=tmin, tmax=tmax)

        # In case electrode position file was supplied, create info object
        # with information about electrode positions
        print(f'.. INFO: montage_fname = {montage_fname}')
        if os.path.exists(montage_fname):
            montage_root, montage_format = os.path.splitext(montage_fname)
            if montage_format == ".xyz": # Cartool electrode file
                print("\t.. INFO: Create montage from Cartool electrodes file...")
                montage = EEGLAB2fif._create_montage_from_electrode_xyz(montage_fname)
            elif montage_format == ".tsv" and "_electrodes" in montage_root:
                print("\t.. INFO: Create montage from standard BIDS TSV electrodes file...")
                montage = EEGLAB2fif._create_montage_from_electrode_tsv(montage_fname)
            else:
                raise ValueError(f"Invalid format () for electrode position file. "
                                 'Valid formats are: BIDS "_electrodes.tsv" and Cartool ".xyz"')
            epochs.info.set_montage(montage)

        epochs.save(epochs_fif_fname, overwrite=overwrite)

    @staticmethod
    def _create_montage_from_electrode_xyz(montage_fname):
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

        # Create the montage object with the extracted channel names and positions
        montage = mne.channels.make_dig_montage(ch_pos=dict(zip(ch_names, ch_coord)), coord_frame="head")
        return montage

    @staticmethod
    def _create_montage_from_electrode_tsv(montage_fname):
        with open(montage_fname) as file:
            tsv_file = csv.reader(file, delimiter="\t")
            ch_coord = [line[1:4] for line in tsv_file if line[0] not in ["lpa", "rpa", "nasion"]]
            ch_names = [line[0] for line in tsv_file if line[0] not in ["lpa", "rpa", "nasion"]]

        # Create the montage object with the extracted channel names and positions
        montage = mne.channels.make_dig_montage(ch_pos=dict(zip(ch_names, ch_coord)), coord_frame="head")
        return montage

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["epochs_file"] = self._gen_output_filename()
        return outputs

    def _gen_output_filename(self):
        # Generate the path of the outputs automatically if not
        # provided as input
        return os.path.abspath(self.inputs.out_epochs_fif_fname)


class MNEInverseSolutionROIInputSpec(BaseInterfaceInputSpec):
    fs_subject = traits.Str(desc="FreeSurfer subject ID", mandatory=True)

    fs_subjects_dir = traits.Directory(desc="Freesurfer subjects (derivatives) directory",
                                       exists=True,
                                       mandatory=True)

    epochs_file = traits.File(exists=True, desc="eeg * epochs in .fif format", mandatory=True)

    src_file = traits.File(exists=True, desc="Source space created with MNE in fif format", mandatory=True)

    bem_file = traits.File(exists=True, desc="Surfaces for head model in fif format", mandatory=True)

    noise_cov_file = traits.File(exists=True, desc="Noise covariance matrix in fif format", mandatory=True)

    fwd_file = traits.File(desc="Forward solution in fif format", mandatory=True)

    atlas_annot = traits.Enum(
        ['aparc', 'lausanne2018.scale1', 'lausanne2018.scale2',
         'lausanne2018.scale3', 'lausanne2018.scale4', 'lausanne2018.scale5'],
        desc="The parcellation to use, e.g., 'aparc', 'lausanne2018.scale1', "
             "'lausanne2018.scale2', 'lausanne2018.scale3', 'lausanne2018.scale4' or"
             "'lausanne2018.scale5'"
    )

    esi_method = traits.Enum(
        "sLORETA", "eLORETA", "MNE", "dSPM",
        desc="Use minimum norm 1, dSPM 2, sLORETA (default) 3, or eLORETA 4."
    )

    esi_method_snr = traits.Float(
        3.0,
        desc="SNR value such as the ESI method regularization weight lambda2 is set to  `1.0 / esi_method_snr ** 2`",
    )

    out_roi_ts_fname_prefix = traits.Str(desc="Output filename prefix (no extension) for rois * time series in .npy and .mat formats")

    out_inv_fname = traits.Str(desc="Output filename for inverse operator in fif format", mandatory=True)


class MNEInverseSolutionROIOutputSpec(TraitedSpec):
    roi_ts_npy_file = traits.File(desc="Path to output ROI time series file in .npy format")

    roi_ts_mat_file = traits.File(desc="Path to output ROI time series file in .mat format")

    inv_file = traits.File(desc="Path to output inverse operator file in fif format.")


class MNEInverseSolutionROI(BaseInterface):
    """Use MNE to convert EEG data from EEGlab to MNE format.

    Examples
    --------
    >>> from cmtklib.interfaces.mne import MNEInverseSolutionROI
    >>> inv_sol = MNEInverseSolutionROI()
    >>> inv_sol.inputs.esi_method_snr = 3.0
    >>> inv_sol.inputs.fs_subject = 'sub-01'
    >>> inv_sol.inputs.fs_subjects_dir = '/path/to/bids_dataset/derivatives/freesurfer-7.1.1'
    >>> inv_sol.inputs.epochs_file = '/path/to/sub-01_epo.fif'
    >>> inv_sol.inputs.src_file = '/path/to/sub-01_src.fif'
    >>> inv_sol.inputs.bem_file = '/path/to/sub-01_bem.fif'
    >>> inv_sol.inputs.noise_cov_file = '/path/to/sub-01_noisecov.fif'
    >>> inv_sol.inputs.fwd_file = '/path/to/sub-01_fwd.fif'
    >>> inv_sol.inputs.atlas_annot = 'lausanne2018.scale1'
    >>> inv_sol.inputs.out_roi_ts_fname_prefix = 'sub-01_atlas-L2018_res-scale1_desc-epo_timeseries'
    >>> inv_sol.inputs.out_inv_fname = 'sub-01_inv.fif'
    >>> inv_sol.run()  # doctest: +SKIP

    References
    ----------
    - https://mne.tools/stable/generated/mne.read_forward_solution.html

    - https://mne.tools/stable/generated/mne.minimum_norm.make_inverse_operator.html

    - https://mne.tools/stable/generated/mne.minimum_norm.apply_inverse_epochs.html

    - https://mne.tools/stable/generated/mne.read_labels_from_annot.html

    - https://mne.tools/stable/generated/mne.extract_label_time_course.html

    """

    input_spec = MNEInverseSolutionROIInputSpec
    output_spec = MNEInverseSolutionROIOutputSpec

    def _run_interface(self, runtime):
        roi_tcs = self._createInv_MNE(
            self.inputs.fs_subjects_dir,
            self.inputs.fs_subject,
            self.inputs.epochs_file,
            self.inputs.fwd_file,
            self.inputs.noise_cov_file,
            self.inputs.src_file,
            self.inputs.atlas_annot,
            self.inputs.out_inv_fname,
            self.inputs.esi_method,
            self.inputs.esi_method_snr
        )
        np.save(self._gen_output_filename_roi_ts(extension=".npy"), roi_tcs)
        sio.savemat(self._gen_output_filename_roi_ts(extension=".mat"), {"ts": roi_tcs})
        return runtime

    @staticmethod
    def _createInv_MNE(
        fs_subjects_dir, subject, epochs_file, fwd_file, noise_cov_file,
        src_file, atlas_annot, out_inv_fname, esi_method, esi_method_snr
    ):
        # Load files
        epochs = mne.read_epochs(epochs_file)
        fwd = mne.read_forward_solution(fwd_file)
        noise_cov = mne.read_cov(noise_cov_file)
        src = mne.read_source_spaces(src_file, patch_stats=False, verbose=None)

        # Compute the inverse operator
        inverse_operator = mne.minimum_norm.make_inverse_operator(
            epochs.info, fwd, noise_cov, loose=1, depth=None, fixed=False
        )
        # inverse_operator = mne.minimum_norm.make_inverse_operator(
        #     epochs.info, fwd, noise_cov, loose=0, depth=None, fixed=True)
        mne.minimum_norm.write_inverse_operator(out_inv_fname, inverse_operator)

        # Compute the time courses of the source points
        lambda2 = 1.0 / esi_method_snr ** 2
        evoked = epochs.average().pick("eeg")
        stcs = mne.minimum_norm.apply_inverse_epochs(
            epochs, inverse_operator, lambda2, esi_method,
            pick_ori=None, nave=evoked.nave, return_generator=False
        )

        # Read the labels of the source points
        labels_parc = mne.read_labels_from_annot(
            subject, parc=atlas_annot, subjects_dir=fs_subjects_dir
        )

        # Get the ROI time courses
        return mne.extract_label_time_course(
            stcs,
            labels_parc,
            src,
            mode="pca_flip",
            allow_empty=True,
            return_generator=False
        )

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["inv_file"] = self._gen_output_filename_inv()
        outputs["roi_ts_npy_file"] = self._gen_output_filename_roi_ts(extension=".npy")
        outputs["roi_ts_mat_file"] = self._gen_output_filename_roi_ts(extension=".mat")
        return outputs

    def _gen_output_filename_inv(self):
        # Return the absolute path of the output inverse operator file
        return os.path.abspath(self.inputs.out_inv_fname)

    def _gen_output_filename_roi_ts(self, extension):
        # Return the absolute path of the output ROI time series file
        return os.path.abspath(self.inputs.out_roi_ts_fname_prefix + extension)


class MNESpectralConnectivityInputSpec(BaseInterfaceInputSpec):
    fs_subject = traits.Str(desc="FreeSurfer subject ID", mandatory=True)

    fs_subjects_dir = traits.Directory(desc="Freesurfer subjects (derivatives) directory",
                                       exists=True,
                                       mandatory=True)

    epochs_file = File(exists=True, desc="Epochs file in fif format")

    roi_ts_file = File(exists=True, desc="Extracted ROI time courses from ESI in .npy format")

    roi_volume_tsv_file = File(exists=True, desc="Index / label atlas mapping file in .tsv format accordingly to BIDS")

    atlas_annot = traits.Enum(
        ['aparc', 'lausanne2018.scale1', 'lausanne2018.scale2',
         'lausanne2018.scale3', 'lausanne2018.scale4', 'lausanne2018.scale5'],
        desc="The parcellation to use, e.g., 'aparc', 'lausanne2018.scale1', "
             "'lausanne2018.scale2', 'lausanne2018.scale3', 'lausanne2018.scale4' or"
             "'lausanne2018.scale5'"
    )

    connectivity_metrics = traits.List(
        ['coh', 'cohy', 'imcoh',
         'plv', 'ciplv', 'ppc',
         'pli', 'wpli', 'wpli2_debiased'],
        desc="Set of frequency- and time-frequency-domain connectivity metrics to compute"
    )

    output_types = traits.List(
        ['tsv', 'gpickle', 'mat', 'graphml'],
        desc="Set of format to save output connectome files"
    )

    out_cmat_fname = traits.Str(
        "conndata-network_connectivity",
        desc="Basename of output connectome file (without any extension)"
    )


class MNESpectralConnectivityOutputSpec(TraitedSpec):
    connectivity_matrices = OutputMultiPath(File, desc="Connectivity matrices")


class MNESpectralConnectivity(BaseInterface):
    """Use MNE to compute frequency- and time-frequency-domain connectivity measures.

    Examples
    --------
    >>> from cmtklib.interfaces.mne import MNESpectralConnectivity
    >>> eeg_cmat = MNESpectralConnectivity()
    >>> eeg_cmat.inputs.fs_subject = 'sub-01'
    >>> eeg_cmat.inputs.fs_subjects_dir = '/path/to/bids_dataset/derivatives/freesurfer-7.1.1'
    >>> eeg_cmat.inputs.atlas_annot = 'lausanne2018.scale1'
    >>> eeg_cmat.inputs.connectivity_metrics = ['imcoh', 'pli', 'wpli']
    >>> eeg_cmat.inputs.output_types = ['tsv', 'gpickle', 'mat', 'graphml']
    >>> eeg_cmat.inputs.epochs_file = '/path/to/sub-01_epo.fif'
    >>> eeg_cmat.inputs.roi_ts_file = '/path/to/sub-01_timeseries.npy'
    >>> eeg_cmat.run()  # doctest: +SKIP

    References
    ----------
    - https://mne.tools/mne-connectivity/stable/generated/mne_connectivity.spectral_connectivity_epochs.html

    """

    input_spec = MNESpectralConnectivityInputSpec
    output_spec = MNESpectralConnectivityOutputSpec

    def _run_interface(self, runtime):
        # Load Epochs file in fif format
        epochs = mne.read_epochs(self.inputs.epochs_file)

        # Load Epochs ROI time series file
        roi_ts_epo = np.load(self.inputs.roi_ts_file)

        # Compute time / frequency connectivity metrics
        # of input Epochs ROI time series
        con = mnec.spectral_connectivity_epochs(
            data=roi_ts_epo,
            method=self.inputs.connectivity_metrics,
            mode='multitaper',
            sfreq=epochs.info['sfreq'],  # the sampling frequency
            faverage=True,
            mt_adaptive=True,
            n_jobs=1,
            verbose='WARNING'
        )

        # Prepare the connectivity data for saving with CMP3 the connectome files
        # con is a 3D array, get the connectivity for the first (and only) freq. band
        # for each method
        con_res = dict()
        nb_rois: int = 0
        for method, c in zip(self.inputs.connectivity_metrics, con):
            con_res[method] = np.squeeze(c.get_data(output='dense'))

            if nb_rois == 0:
                nb_rois = con_res[method].shape[0]

        # Get parcellation labels used by MNE
        labels_parc = mne.read_labels_from_annot(
            subject=self.inputs.fs_subject,
            parc=self.inputs.atlas_annot,
            subjects_dir=self.inputs.fs_subjects_dir
        )
        roi_labels = [label.name for label in labels_parc]

        print(f'nb_rois: {nb_rois}')
        print(f'roi_labels (length): {len(roi_labels)}')

        # Special handle of labels for Cartool as it includes
        # all cortical and sub-cortical rois
        if self.inputs.roi_volume_tsv_file and (len(roi_labels) < nb_rois):
            # Cartool is also using sub-cortical
            df_labels = pd.read_csv(self.inputs.roi_volume_tsv_file, delimiter="\t")
            roi_labels = list(df_labels["name"])
            print(f'new roi_labels (length): {len(roi_labels)}')

        save_eeg_connectome_file(
            con_res=con_res,
            roi_labels=roi_labels,
            output_dir=os.getcwd(),
            output_basename=self.inputs.out_cmat_fname,
            output_types=self.inputs.output_types
        )

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["connectivity_matrices"] = [
            f'{self._gen_output_filename_cmat()}.{ext}'
            for ext in self.inputs.output_types
        ]
        return outputs

    def _gen_output_filename_cmat(self):
        # Return the absolute path of the output inverse operator file
        return os.path.abspath(self.inputs.out_cmat_fname)
