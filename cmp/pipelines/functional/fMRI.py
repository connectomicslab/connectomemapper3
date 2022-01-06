# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""Functional pipeline Class definition."""

import datetime
import shutil

import nipype.interfaces.io as nio
from nipype import config, logging
from nipype.interfaces.utility import Merge

from cmtklib.bids.io import __cmp_directory__, __nipype_directory__
from cmp.pipelines.common import *
from cmp.stages.connectome.fmri_connectome import ConnectomeStage
from cmp.stages.functional.functionalMRI import FunctionalMRIStage
from cmp.stages.preprocessing.fmri_preprocessing import PreprocessingStage
from cmp.stages.registration.registration import RegistrationStage


class GlobalConfiguration(HasTraits):
    """Global pipeline configurations.

    Attributes
    ----------
    process_type : 'fMRI'
        Processing pipeline type

    imaging_model : 'fMRI'
        Imaging model used by `RegistrationStage`
    """

    process_type = Str("fMRI")
    imaging_model = Str


class fMRIPipeline(Pipeline):
    """Class that extends a :class:`Pipeline` and represents the processing pipeline for structural MRI.

    It is composed of:
        * the preprocessing stage that can perform slice timing correction, deskiping and motion correction

        * the registration stage that co-registered the anatomical T1w scan to the mean BOLD image
          and projects the parcellations to the native fMRI space

        * the extra-preprocessing stage (FunctionalMRIStage) that can perform nuisance regression
          and bandpass filtering

        * the connectome stage that extracts the time-series of each parcellation ROI and
          computes the Pearson's correlation coefficient between ROI time-series to create
          the functional connectome.

    See Also
    --------
    cmp.stages.preprocessing.fmri_preprocessing.PreprocessingStage
    cmp.stages.registration.registration.RegistrationStage
    cmp.stages.functional.functionalMRI.FunctionalMRIStage
    cmp.stages.connectome.fmri_connectome.ConnectomeStage
    """

    now = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    pipeline_name = Str("fMRI_pipeline")
    input_folders = ["anat", "func"]
    seg_tool = Str
    subject = Str
    subject_directory = Directory
    derivatives_directory = Directory
    ordered_stage_list = [
        "Preprocessing",
        "Registration",
        "FunctionalMRI",
        "Connectome",
    ]
    global_conf = GlobalConfiguration()
    config_file = Str
    parcellation_scheme = Str
    atlas_info = Dict()
    custom_atlas_name = Str
    custom_atlas_res = Str
    subjects_dir = Str
    subject_id = Str

    def __init__(self, project_info):
        """Constructor of a `fMRIPipeline` object.

        Parameters
        ----------
        project_info: cmp.project.ProjectInfo
            Instance of `CMP_Project_Info` object.

        See Also
        --------
        cmp.project.CMP_Project_Info
        """
        self.subjects_dir = project_info.freesurfer_subjects_dir
        self.subject_id = project_info.freesurfer_subject_id

        self.global_conf.subjects = project_info.subjects
        self.global_conf.subject = project_info.subject

        if len(project_info.subject_sessions) > 0:
            self.global_conf.subject_session = project_info.subject_session
            self.subject_directory = os.path.join(
                project_info.base_directory,
                project_info.subject,
                project_info.subject_session,
            )
        else:
            self.global_conf.subject_session = ""
            self.subject_directory = os.path.join(
                project_info.base_directory, project_info.subject
            )

        self.derivatives_directory = os.path.abspath(project_info.output_directory)

        if project_info.output_directory is not None:
            self.output_directory = os.path.abspath(project_info.output_directory)
        else:
            self.output_directory = os.path.join(self.base_directory, "derivatives")

        self.stages = {
            "Preprocessing": PreprocessingStage(
                bids_dir=project_info.base_directory, output_dir=self.output_directory
            ),
            "Registration": RegistrationStage(
                pipeline_mode="fMRI",
                fs_subjects_dir=project_info.freesurfer_subjects_dir,
                fs_subject_id=os.path.basename(project_info.freesurfer_subject_id),
                bids_dir=project_info.base_directory,
                output_dir=self.output_directory,
            ),
            "FunctionalMRI": FunctionalMRIStage(
                bids_dir=project_info.base_directory, output_dir=self.output_directory
            ),
            "Connectome": ConnectomeStage(
                bids_dir=project_info.base_directory, output_dir=self.output_directory
            ),
        }

        Pipeline.__init__(self, project_info)

        self.subject = project_info.subject

        self.stages["FunctionalMRI"].config.on_trait_change(
            self.update_nuisance_requirements, "global_nuisance"
        )
        self.stages["FunctionalMRI"].config.on_trait_change(
            self.update_nuisance_requirements, "csf"
        )
        self.stages["FunctionalMRI"].config.on_trait_change(
            self.update_nuisance_requirements, "wm"
        )
        self.stages["Connectome"].config.on_trait_change(
            self.update_scrubbing, "apply_scrubbing"
        )

    def _subject_changed(self, new):
        """ "Update subject in the connectome stage configuration when ``subject`` is updated.

        Parameters
        ----------
        new : string
            New value.
        """
        self.stages["Connectome"].config.subject = new

    def update_registration(self):
        """Configure the list of registration tools."""
        if (
                "Nonlinear (FSL)"
                in self.stages["Registration"].config.registration_mode_trait
        ):
            self.stages["Registration"].config.registration_mode_trait = [
                "Linear (FSL)",
                "BBregister (FS)",
                "Nonlinear (FSL)",
            ]
        else:
            self.stages["Registration"].config.registration_mode_trait = [
                "Linear (FSL)",
                "BBregister (FS)",
            ]

    def update_nuisance_requirements(self):
        """Update nuisance requirements.

        Configure the registration to apply the estimated transformation to multiple segmentation masks
        depending on the Nuisance correction steps performed.
        """
        self.stages["Registration"].config.apply_to_eroded_brain = self.stages[
            "FunctionalMRI"
        ].config.global_nuisance
        self.stages["Registration"].config.apply_to_eroded_csf = self.stages[
            "FunctionalMRI"
        ].config.csf
        self.stages["Registration"].config.apply_to_eroded_wm = self.stages[
            "FunctionalMRI"
        ].config.wm

    def update_scrubbing(self):
        """Update to precompute or inputs for scrubbing during the FunctionalMRI stage."""
        self.stages["FunctionalMRI"].config.scrubbing = self.stages[
            "Connectome"
        ].config.apply_scrubbing

    def define_custom_mapping(self, custom_last_stage):
        """Define the pipeline to be executed until a specific stages.

        Not used yet by CMP3.

        Parameters
        ----------
        custom_last_stage : string
            Last stage to execute. Valid values are: "Preprocessing",
            "Registration", "FunctionalMRI" and "Connectome".
        """
        # start by disabling all stages
        for stage in self.ordered_stage_list:
            self.stages[stage].enabled = False
        # enable until selected one
        for stage in self.ordered_stage_list:
            print("Enable stage : %s" % stage)
            self.stages[stage].enabled = True
            if stage == custom_last_stage:
                break

    def check_input(self, layout, gui=True):
        """Check if input of the diffusion pipeline are available.

        Parameters
        ----------
        layout : bids.BIDSLayout
            Instance of BIDSLayout

        gui : traits.Bool
            Boolean used to display different messages
            but not really meaningful anymore since the GUI
            components have been migrated to `cmp.bidsappmanager`

        Returns
        -------

        valid_inputs : traits.Bool
            True if inputs are available
        """
        print("**** Check Inputs ****")
        fMRI_available = False
        fMRI_json_available = False
        t1_available = False
        t2_available = False
        valid_inputs = False

        if self.global_conf.subject_session == "":
            subject = self.subject
        else:
            subject = "_".join((self.subject, self.global_conf.subject_session))

        fmri_file = os.path.join(
            self.subject_directory, "func", subject + "_task-rest_bold.nii.gz"
        )
        json_file = os.path.join(
            self.subject_directory, "func", subject + "_task-rest_bold.json"
        )
        t1_file = os.path.join(self.subject_directory, "anat", subject + "_T1w.nii.gz")
        t2_file = os.path.join(self.subject_directory, "anat", subject + "_T2w.nii.gz")

        subjid = self.subject.split("-")[1]

        print("> Looking for....")
        if self.global_conf.subject_session == "":

            files = layout.get(subject=subjid, suffix="bold", extension=".nii.gz")
            if len(files) > 0:
                fmri_file = os.path.join(files[0].dirname, files[0].filename)
            else:
                print("ERROR : BOLD image not found for subject %s." % subjid)
                return

            files = layout.get(subject=subjid, suffix="bold", extension=".json")
            if len(files) > 0:
                json_file = os.path.join(files[0].dirname, files[0].filename)
            else:
                print("WARNING : BOLD json sidecar not found for subject %s." % subjid)

            files = layout.get(subject=subjid, suffix="T1w", extension=".nii.gz")
            if len(files) > 0:
                t1_file = os.path.join(files[0].dirname, files[0].filename)
            else:
                print("WARNING : T1w image not found for subject %s." % subjid)

            files = layout.get(subject=subjid, suffix="T2w", extension=".nii.gz")
            if len(files) > 0:
                t2_file = os.path.join(files[0].dirname, files[0].filename)
            else:
                print("WARNING : T2w image not found for subject %s." % subjid)

        else:
            sessid = self.global_conf.subject_session.split("-")[1]

            files = layout.get(
                subject=subjid, suffix="bold", extension=".nii.gz", session=sessid
            )
            if len(files) > 0:
                fmri_file = os.path.join(files[0].dirname, files[0].filename)
            else:
                print(
                    "ERROR : BOLD image not found for subject %s, session %s."
                    % (subjid, self.global_conf.subject_session)
                )
                return

            files = layout.get(
                subject=subjid, suffix="bold", extension=".json", session=sessid
            )
            if len(files) > 0:
                json_file = os.path.join(files[0].dirname, files[0].filename)
            else:
                print(
                    "WARNING : BOLD json sidecar not found for subject %s, session %s."
                    % (subjid, self.global_conf.subject_session)
                )

            files = layout.get(
                subject=subjid, suffix="T1w", extension=".nii.gz", session=sessid
            )
            if len(files) > 0:
                t1_file = os.path.join(files[0].dirname, files[0].filename)
            else:
                print(
                    "WARNING : T1w image not found for subject %s, session %s."
                    % (subjid, self.global_conf.subject_session)
                )

            files = layout.get(
                subject=subjid, suffix="T2w", extension=".nii.gz", session=sessid
            )
            if len(files) > 0:
                t2_file = os.path.join(files[0].dirname, files[0].filename)
            else:
                print(
                    "WARNING : T2w image not found for subject %s, session %s."
                    % (subjid, self.global_conf.subject_session)
                )

        print("... t1_file : %s" % t1_file)
        print("... t2_file : %s" % t2_file)
        print("... fmri_file : %s" % fmri_file)
        print("... json_file : %s" % json_file)

        if os.path.isfile(t1_file):
            t1_available = True
        if os.path.isfile(t2_file):
            t2_available = True
        if os.path.isfile(fmri_file):
            fMRI_available = True
        if os.path.isfile(json_file):
            fMRI_json_available = True

        if fMRI_available:
            if self.global_conf.subject_session == "":
                out_dir = os.path.join(self.output_directory, __cmp_directory__, self.subject)
            else:
                out_dir = os.path.join(
                    self.output_directory,
                    __cmp_directory__,
                    self.subject,
                    self.global_conf.subject_session,
                )

            out_fmri_file = os.path.join(
                out_dir, "func", subject + "_task-rest_desc-cmp_bold.nii.gz"
            )
            shutil.copy(src=fmri_file, dst=out_fmri_file)

            valid_inputs = True
            input_message = "Inputs check finished successfully.\nfMRI data available."

            if t2_available:
                out_t2_file = os.path.join(out_dir, "anat", subject + "_T2w.nii.gz")
                shutil.copy(src=t2_file, dst=out_t2_file)
                # swap_and_reorient(src_file=os.path.join(self.base_directory,'NIFTI','T2_orig.nii.gz'),
                #                   ref_file=os.path.join(self.base_directory,'NIFTI','fMRI.nii.gz'),
                #                   out_file=os.path.join(self.base_directory,'NIFTI','T2.nii.gz'))

            if fMRI_json_available:
                out_json_file = os.path.join(
                    out_dir, "func", subject + "_task-rest_desc-cmp_bold.json"
                )
                shutil.copy(src=json_file, dst=out_json_file)

        else:
            input_message = (
                "Error during inputs check. \nfMRI data not available (fMRI)."
            )

        print(input_message)

        self.global_conf.imaging_model = "fMRI"
        self.stages["Registration"].config.imaging_model = "fMRI"

        if t2_available:
            self.stages["Registration"].config.registration_mode_trait = [
                "FSL (Linear)",
                "BBregister (FS)",
            ]
        else:
            self.stages["Registration"].config.registration_mode_trait = [
                "FSL (Linear)"
            ]
        # self.fill_stages_outputs()

        return valid_inputs

    def check_config(self):
        """Check if the fMRI pipeline parameters is properly configured.

        Returns
        -------
        message : string
            String that is empty if success, otherwise it contains the error message
        """
        if (
            self.stages["FunctionalMRI"].config.motion is True
            and self.stages["Preprocessing"].config.motion_correction is False
        ):
            return (
                "\n\tMotion signal regression selected but no motion correction set.\t\n\t"
                "Please activate motion correction in the preprocessing configuration window,\n\t"
                "or disable the motion signal regression in the functional configuration window.\t\n"
            )
        if (
                self.stages["Connectome"].config.apply_scrubbing is True
                and self.stages["Preprocessing"].config.motion_correction is False
        ):
            return (
                "\n\tScrubbing applied but no motion correction set.\t\n\t"
                "Please activate motion correction in the preprocessing configutation window,\n\t"
                "or disable scrubbing in the connectome configuration window.\t\n"
            )
        return ""

    def create_datagrabber_node(self, base_directory, bids_atlas_label):
        """Create the appropriate Nipype DataGrabber node depending on the `parcellation_scheme`

        Parameters
        ----------
        base_directory : Directory
            Main CMP output directory of a subject
            e.g. ``/output_dir/cmp/sub-XX/(ses-YY)``

        bids_atlas_label : string
            Parcellation atlas label

        Returns
        -------
        datasource : Output Nipype DataGrabber Node
            Output Nipype Node with :obj:`~nipype.interfaces.io.DataGrabber` interface
        """
        datasource = pe.Node(
            interface=nio.DataGrabber(
                outfields=[
                    "fMRI",
                    "T1",
                    "T2",
                    "aseg",
                    "brain",
                    "brain_mask",
                    "wm_mask_file",
                    "wm_eroded",
                    "brain_eroded",
                    "csf_eroded",
                    "roi_volume_s1",
                    "roi_volume_s2",
                    "roi_volume_s3",
                    "roi_volume_s4",
                    "roi_volume_s5",
                    "roi_graphml_s1",
                    "roi_graphml_s2",
                    "roi_graphml_s3",
                    "roi_graphml_s4",
                    "roi_graphml_s5",
                ]
            ),
            name="func_datasource",
        )
        datasource.inputs.base_directory = base_directory
        datasource.inputs.template = "*"
        datasource.inputs.raise_on_empty = False

        if self.parcellation_scheme == "NativeFreesurfer":
            # fmt:off
            datasource.inputs.field_template = dict(
                fMRI="func/" + self.subject + "_task-rest_desc-cmp_bold.nii.gz",
                T1="anat/" + self.subject + "_desc-head_T1w.nii.gz",
                T2="anat/" + self.subject + "_T2w.nii.gz",
                aseg="anat/" + self.subject + "_desc-aseg_dseg.nii.gz",
                brain="anat/" + self.subject + "_desc-brain_T1w.nii.gz",
                brain_mask="anat/" + self.subject + "_desc-brain_mask.nii.gz",
                wm_mask_file="anat/" + self.subject + "_label-WM_dseg.nii.gz",
                wm_eroded="anat/" + self.subject + "_label-WM_desc-eroded_dseg.nii.gz",
                brain_eroded="anat/" + self.subject + "_label-brain_desc-eroded_dseg.nii.gz",
                csf_eroded="anat/" + self.subject + "_label-CSF_desc-eroded_dseg.nii.gz",
                roi_volume_s1="anat/" + self.subject + "_atlas-Desikan_dseg.nii.gz",
                roi_volume_s2="anat/irrelevant.nii.gz",
                roi_volume_s3="anat/irrelevant.nii.gz",
                roi_volume_s4="anat/irrelevant.nii.gz",
                roi_volume_s5="anat/irrelevant.nii.gz",
                roi_graphml_s1="anat/" + self.subject + "_atlas-Desikan_dseg.graphml",
                roi_graphml_s2="anat/irrelevant.graphml",
                roi_graphml_s3="anat/irrelevant.graphml",
                roi_graphml_s4="anat/irrelevant.graphml",
                roi_graphml_s5="anat/irrelevant.graphml",
            )
            # fmt:on
        elif self.parcellation_scheme == "Custom":
            # fmt:off
            datasource.inputs.field_template = dict(
                fMRI="func/" + self.subject + "_task-rest_desc-cmp_bold.nii.gz",
                T1="anat/" + self.subject + "_desc-head_T1w.nii.gz",
                T2="anat/" + self.subject + "_T2w.nii.gz",
                aseg="anat/" + self.subject + "_desc-aseg_dseg.nii.gz",
                brain="anat/" + self.subject + "_desc-brain_T1w.nii.gz",
                brain_mask="anat/" + self.subject + "_desc-brain_mask.nii.gz",
                wm_mask_file="anat/" + self.subject + "_label-WM_dseg.nii.gz",
                wm_eroded="anat/" + self.subject + "_label-WM_desc-eroded_dseg.nii.gz",
                brain_eroded="anat/" + self.subject + "_label-brain_desc-eroded_dseg.nii.gz",
                csf_eroded="anat/" + self.subject + "_label-CSF_desc-eroded_dseg.nii.gz",
                roi_volume_s1="anat/" + self.subject + "_atlas-" + bids_atlas_label + "_dseg.nii.gz",
                roi_volume_s2="anat/irrelevant.nii.gz",
                roi_volume_s3="anat/irrelevant.nii.gz",
                roi_volume_s4="anat/irrelevant.nii.gz",
                roi_volume_s5="anat/irrelevant.nii.gz",
                roi_graphml_s1="anat/" + self.subject + "_atlas-" + bids_atlas_label + "_dseg.graphml",
                roi_graphml_s2="anat/irrelevant.graphml",
                roi_graphml_s3="anat/irrelevant.graphml",
                roi_graphml_s4="anat/irrelevant.graphml",
                roi_graphml_s5="anat/irrelevant.graphml",
            )
            # fmt:on
        else:
            # fmt:off
            datasource.inputs.field_template = dict(
                fMRI="func/" + self.subject + "_task-rest_desc-cmp_bold.nii.gz",
                T1="anat/" + self.subject + "_desc-head_T1w.nii.gz",
                T2="anat/" + self.subject + "_T2w.nii.gz",
                aseg="anat/" + self.subject + "_desc-aseg_dseg.nii.gz",
                brain="anat/" + self.subject + "_desc-brain_T1w.nii.gz",
                brain_mask="anat/" + self.subject + "_desc-brain_mask.nii.gz",
                wm_mask_file="anat/" + self.subject + "_label-WM_dseg.nii.gz",
                wm_eroded="anat/" + self.subject + "_label-WM_desc-eroded_dseg.nii.gz",
                brain_eroded="anat/" + self.subject + "_label-brain_desc-eroded_dseg.nii.gz",
                csf_eroded="anat/" + self.subject + "_label-CSF_desc-eroded_dseg.nii.gz",
                roi_volume_s1="anat/" + self.subject + "_atlas-" + bids_atlas_label + "_res-scale1_dseg.nii.gz",
                roi_volume_s2="anat/" + self.subject + "_atlas-" + bids_atlas_label + "_res-scale2_dseg.nii.gz",
                roi_volume_s3="anat/" + self.subject + "_atlas-" + bids_atlas_label + "_res-scale3_dseg.nii.gz",
                roi_volume_s4="anat/" + self.subject + "_atlas-" + bids_atlas_label + "_res-scale4_dseg.nii.gz",
                roi_volume_s5="anat/" + self.subject + "_atlas-" + bids_atlas_label + "_res-scale5_dseg.nii.gz",
                roi_graphml_s1="anat/" + self.subject + "_atlas-" + bids_atlas_label + "_res-scale1_dseg.graphml",
                roi_graphml_s2="anat/" + self.subject + "_atlas-" + bids_atlas_label + "_res-scale2_dseg.graphml",
                roi_graphml_s3="anat/" + self.subject + "_atlas-" + bids_atlas_label + "_res-scale3_dseg.graphml",
                roi_graphml_s4="anat/" + self.subject + "_atlas-" + bids_atlas_label + "_res-scale4_dseg.graphml",
                roi_graphml_s5="anat/" + self.subject + "_atlas-" + bids_atlas_label + "_res-scale5_dseg.graphml",
            )
            # fmt:on

        datasource.inputs.sort_filelist = False

        return datasource

    def create_datasinker_node(self, base_directory, bids_atlas_label):
        """Create the appropriate Nipype DataSink node depending on the `parcellation_scheme`

        Parameters
        ----------
        base_directory : Directory
            Main CMP output directory of a subject
            e.g. ``/output_dir/cmp/sub-XX/(ses-YY)``

        bids_atlas_label : string
            Parcellation atlas label

        recon_model : string
            Diffusion signal model (`DTI` or `CSD`)

        tracking_model : string
            Tractography algorithm (`DET` or `PROB`)

        Returns
        -------
        sinker : Output Nipype DataSink Node
            Output Nipype Node with :obj:`~nipype.interfaces.io.DataSink` interface
        """
        sinker = pe.Node(nio.DataSink(), name="func_datasinker")
        sinker.inputs.base_directory = os.path.join(base_directory)
        # fmt:off
        substitutions = [
            ("eroded_brain_registered.nii.gz", self.subject + "_space-meanBOLD_desc-eroded_label-brain_dseg.nii.gz"),
            ("wm_mask_registered.nii.gz", self.subject + "_space-meanBOLD_label-WM_dseg.nii.gz",),
            ("eroded_csf_registered.nii.gz", self.subject + "_space-meanBOLD_desc-eroded_label-CSF_dseg.nii.gz"),
            ("eroded_wm_registered.nii.gz", self.subject + "_space-meanBOLD_desc-eroded_label-WM_dseg.nii.gz"),
            ("fMRI_despike_st_mcf.nii.gz_mean_reg.nii.gz", self.subject + "_meanBOLD.nii.gz"),
            ("fMRI_despike_st_mcf.nii.gz.par", self.subject + "_motion.tsv"),
            ("FD.npy", self.subject + "_desc-scrubbing_FD.npy"),
            ("DVARS.npy", self.subject + "_desc-scrubbing_DVARS.npy"),
            ("fMRI_bandpass.nii.gz", self.subject + "_task-rest_desc-bandpass_bold.nii.gz"),
            ("fMRI_discard_mean.nii.gz",  self.subject + "_meanBOLD.nii.gz")
        ]
        # fmt:on

        if self.parcellation_scheme == "NativeFreesurfer":
            # fmt:off
            substitutions += [
                (
                    f'{self.subject}_atlas-{bids_atlas_label}_dseg_flirt.nii.gz',
                    f'{self.subject}_space-meanBOLD_atlas-{bids_atlas_label}_dseg.nii.gz'
                ),
                ("connectome_freesurferaparc", self.subject + "_atlas-Desikan_conndata-network_connectivity"),
                ("averageTimeseries_freesurferaparc", self.subject + "_atlas-Desikan_timeseries"),
            ]
            # fmt:on
        elif self.parcellation_scheme == "Custom":
            bids_atlas_name = bids_atlas_label if "res" not in bids_atlas_label else bids_atlas_label.split("_")[0]
            # fmt:off
            substitutions += [
                (f'{self.subject}_task-rest_desc-cmp_bold_mean.nii.gz', f'{self.subject}_meanBOLD.nii.gz'),
                (
                    f'{self.subject}_atlas-{bids_atlas_label}_dseg_flirt.nii.gz',
                    f'{self.subject}_space-meanBOLD_atlas-{bids_atlas_label}_dseg.nii.gz'
                ),
                (f"connectome_{bids_atlas_name}", self.subject + f"_atlas-{bids_atlas_label}_conndata-network_connectivity"),
                (f"averageTimeseries_{bids_atlas_name}", self.subject + f"_atlas-{bids_atlas_label}_timeseries"),
            ]
            # fmt:on
        else:
            for scale in ['scale1', 'scale2', 'scale3', 'scale4', 'scale5']:
                # fmt:off
                substitutions += [
                    (
                        f'{self.subject}_atlas-{bids_atlas_label}_res-{scale}_dseg_flirt.nii.gz',
                        f'{self.subject}_space-meanBOLD_atlas-{bids_atlas_label}_res-{scale}_dseg.nii.gz'
                    ),
                    (f'connectome_{scale}',
                     f'{self.subject}_atlas-{bids_atlas_label}_res-{scale}_conndata-network_connectivity'),
                    (f'averageTimeseries_{scale}', f'{self.subject}_atlas-{bids_atlas_label}_res-{scale}_timeseries')
                ]
                # fmt:on

        sinker.inputs.substitutions = substitutions

        return sinker

    def create_pipeline_flow(
        self, cmp_deriv_subject_directory, nipype_deriv_subject_directory
    ):
        """Create the pipeline workflow.

        Parameters
        ----------
        cmp_deriv_subject_directory : Directory
            Main CMP output directory of a subject
            e.g. ``/output_dir/cmp/sub-XX/(ses-YY)``

        nipype_deriv_subject_directory : Directory
            Intermediate Nipype output directory of a subject
            e.g. ``/output_dir/nipype/sub-XX/(ses-YY)``

        Returns
        -------
        fMRI_flow : nipype.pipeline.engine.Workflow
            An instance of :class:`nipype.pipeline.engine.Workflow`
        """
        if self.parcellation_scheme == "Lausanne2018":
            bids_atlas_label = "L2018"
        elif self.parcellation_scheme == "NativeFreesurfer":
            bids_atlas_label = "Desikan"
        elif self.parcellation_scheme == "Custom":
            bids_atlas_label = self.custom_atlas_name
            if self.custom_atlas_res is not None and self.custom_atlas_res != "":
                bids_atlas_label += f'_res-{self.custom_atlas_res}'

        # Data sinker for output
        sinker = self.create_datasinker_node(
            base_directory=cmp_deriv_subject_directory,
            bids_atlas_label=bids_atlas_label
        )

        # Data import
        datasource = self.create_datagrabber_node(
            base_directory=cmp_deriv_subject_directory,
            bids_atlas_label=bids_atlas_label
        )

        # Clear previous outputs
        self.clear_stages_outputs()

        # Create fMRI flow
        fMRI_flow = pe.Workflow(
            name="fMRI_pipeline",
            base_dir=os.path.abspath(nipype_deriv_subject_directory),
        )
        fMRI_inputnode = pe.Node(
            interface=util.IdentityInterface(
                fields=[
                    "fMRI",
                    "T1",
                    "T2",
                    "subjects_dir",
                    "subject_id",
                    "wm_mask_file",
                    "roi_volumes",
                    "roi_graphMLs",
                    "wm_eroded",
                    "brain_eroded",
                    "csf_eroded",
                ]
            ),
            name="inputnode",
        )
        fMRI_inputnode.inputs.parcellation_scheme = self.parcellation_scheme
        fMRI_inputnode.inputs.atlas_info = self.atlas_info
        fMRI_inputnode.subjects_dir = self.subjects_dir
        fMRI_inputnode.subject_id = os.path.basename(self.subject_id)

        fMRI_outputnode = pe.Node(
            interface=util.IdentityInterface(fields=["connectivity_matrices"]),
            name="outputnode",
        )

        fMRI_flow.add_nodes([fMRI_inputnode, fMRI_outputnode])

        merge_roi_volumes = pe.Node(interface=Merge(5), name="merge_roi_volumes")
        merge_roi_graphmls = pe.Node(interface=Merge(5), name="merge_roi_graphmls")

        def remove_non_existing_scales(roi_volumes):
            """Returns a list which do not contained any empty element.

            Parameters
            ----------
            roi_volumes : list
                A list of output parcellations that might contain empty element
                in the case of the monoscale Desikan scheme for instance

            Returns
            -------
            out_roi_volumes : list
                The list with no empty element
            """
            out_roi_volumes = []
            for vol in roi_volumes:
                if vol is not None:
                    out_roi_volumes.append(vol)
            return out_roi_volumes

        # fmt:off
        fMRI_flow.connect(
            [
                (datasource, merge_roi_volumes, [("roi_volume_s1", "in1"),
                                                 ("roi_volume_s2", "in2"),
                                                 ("roi_volume_s3", "in3"),
                                                 ("roi_volume_s4", "in4"),
                                                 ("roi_volume_s5", "in5")])
            ]
        )
        # fmt:on

        # fmt:off
        fMRI_flow.connect(
            [
                (datasource, merge_roi_graphmls, [("roi_graphml_s1", "in1"),
                                                  ("roi_graphml_s2", "in2"),
                                                  ("roi_graphml_s3", "in3"),
                                                  ("roi_graphml_s4", "in4"),
                                                  ("roi_graphml_s5", "in5")])
            ]
        )
        # fmt:on

        # fmt:off
        fMRI_flow.connect(
            [
                (datasource, fMRI_inputnode, [("fMRI", "fMRI"),
                                              ("T1", "T1"),
                                              ("T2", "T2"),
                                              ("aseg", "aseg"),
                                              ("wm_mask_file", "wm_mask_file"),
                                              ("brain_eroded", "brain_eroded"),
                                              ("wm_eroded", "wm_eroded"),
                                              ("csf_eroded", "csf_eroded")]),
                (merge_roi_volumes, fMRI_inputnode, [(("out", remove_non_existing_scales), "roi_volumes")]),
                (merge_roi_graphmls, fMRI_inputnode, [(("out", remove_non_existing_scales), "roi_graphMLs")])
            ]
        )
        # fmt:on

        if self.stages["Preprocessing"].enabled:
            preproc_flow = self.create_stage_flow("Preprocessing")
            # fmt:off
            fMRI_flow.connect(
                [
                    (fMRI_inputnode, preproc_flow, [("fMRI", "inputnode.functional")]),
                    (preproc_flow, sinker, [("outputnode.mean_vol", "func.@mean_vol")]),
                ]
            )
            # fmt:on

        if self.stages["Registration"].enabled:
            reg_flow = self.create_stage_flow("Registration")
            # fmt:off
            fMRI_flow.connect(
                [
                    (fMRI_inputnode, reg_flow, [("T1", "inputnode.T1")]),
                    (fMRI_inputnode, reg_flow, [("T2", "inputnode.T2")]),
                    (preproc_flow, reg_flow, [("outputnode.mean_vol", "inputnode.target")],),
                    (fMRI_inputnode, reg_flow, [("wm_mask_file", "inputnode.wm_mask"),
                                                ("roi_volumes", "inputnode.roi_volumes"),
                                                ("brain_eroded", "inputnode.eroded_brain"),
                                                ("wm_eroded", "inputnode.eroded_wm"),
                                                ("csf_eroded", "inputnode.eroded_csf")]),
                    (reg_flow, sinker, [("outputnode.wm_mask_registered_crop", "anat.@registered_wm"),
                                        ("outputnode.roi_volumes_registered_crop", "anat.@registered_roi_volumes"),
                                        ("outputnode.eroded_wm_registered_crop", "anat.@eroded_wm"),
                                        ("outputnode.eroded_csf_registered_crop", "anat.@eroded_csf"),
                                        ("outputnode.eroded_brain_registered_crop", "anat.@eroded_brain")]),
                ]
            )
            # fmt:on

        if self.stages["FunctionalMRI"].enabled:
            func_flow = self.create_stage_flow("FunctionalMRI")
            # fmt:off
            fMRI_flow.connect(
                [
                    (preproc_flow, func_flow, [("outputnode.functional_preproc", "inputnode.preproc_file")],),
                    (reg_flow, func_flow, [("outputnode.wm_mask_registered_crop", "inputnode.registered_wm"),
                                           ("outputnode.roi_volumes_registered_crop",
                                            "inputnode.registered_roi_volumes"),
                                           ("outputnode.eroded_wm_registered_crop", "inputnode.eroded_wm"),
                                           ("outputnode.eroded_csf_registered_crop", "inputnode.eroded_csf"),
                                           ("outputnode.eroded_brain_registered_crop", "inputnode.eroded_brain")]),
                    (func_flow, sinker, [("outputnode.func_file", "func.@func_file"),
                                         ("outputnode.FD", "func.@FD"),
                                         ("outputnode.DVARS", "func.@DVARS")]),
                ]
            )
            # fmt:on

            if self.stages["FunctionalMRI"].config.scrubbing or self.stages["FunctionalMRI"].config.motion:
                # fmt:off
                fMRI_flow.connect(
                    [
                        (preproc_flow, func_flow, [("outputnode.par_file", "inputnode.motion_par_file")]),
                        (preproc_flow, sinker, [("outputnode.par_file", "func.@motion_par_file")]),
                    ]
                )
                # fmt:on

        if self.stages["Connectome"].enabled:
            self.stages["Connectome"].config.subject = self.global_conf.subject
            con_flow = self.create_stage_flow("Connectome")
            # fmt:off
            fMRI_flow.connect(
                [
                    (fMRI_inputnode, con_flow, [("parcellation_scheme", "inputnode.parcellation_scheme"),
                                                ("atlas_info", "inputnode.atlas_info"),
                                                ("roi_graphMLs", "inputnode.roi_graphMLs")]),
                    (func_flow, con_flow, [("outputnode.func_file", "inputnode.func_file"),
                                           ("outputnode.FD", "inputnode.FD"),
                                           ("outputnode.DVARS", "inputnode.DVARS")]),
                    (reg_flow, con_flow, [("outputnode.roi_volumes_registered_crop", "inputnode.roi_volumes_registered")]),
                    (con_flow, fMRI_outputnode, [("outputnode.connectivity_matrices", "connectivity_matrices")]),
                    (con_flow, sinker, [("outputnode.connectivity_matrices", "func.@connectivity_matrices"),
                                        ("outputnode.avg_timeseries", "func.@avg_timeseries")])
                ]
            )
            # fmt:on

        return fMRI_flow

    def process(self):
        """Executes the fMRI pipeline workflow and returns True if successful."""
        # Enable the use of the the W3C PROV data model to capture and represent provenance in Nipype
        # config.enable_provenance()

        # Process time
        self.now = datetime.datetime.now().strftime("%Y%m%d_%H%M")

        if "_" in self.subject:
            self.subject = self.subject.split("_")[0]

        if self.global_conf.subject_session == "":
            cmp_deriv_subject_directory = os.path.join(
                self.output_directory, __cmp_directory__, self.subject
            )
            nipype_deriv_subject_directory = os.path.join(
                self.output_directory, __nipype_directory__, self.subject
            )
        else:
            cmp_deriv_subject_directory = os.path.join(
                self.output_directory,
                __cmp_directory__,
                self.subject,
                self.global_conf.subject_session,
            )
            nipype_deriv_subject_directory = os.path.join(
                self.output_directory,
                __nipype_directory__,
                self.subject,
                self.global_conf.subject_session,
            )

            self.subject = "_".join((self.subject, self.global_conf.subject_session))

        if not os.path.exists(
            os.path.join(nipype_deriv_subject_directory, "fMRI_pipeline")
        ):
            try:
                os.makedirs(
                    os.path.join(nipype_deriv_subject_directory, "fMRI_pipeline")
                )
            except os.error:
                print(
                    "%s was already existing"
                    % os.path.join(nipype_deriv_subject_directory, "fMRI_pipeline")
                )

        # Initialization
        if os.path.isfile(
            os.path.join(
                nipype_deriv_subject_directory, "fMRI_pipeline", "pypeline.log"
            )
        ):
            os.unlink(
                os.path.join(
                    nipype_deriv_subject_directory, "fMRI_pipeline", "pypeline.log"
                )
            )
        config.update_config(
            {
                "logging": {
                    "log_directory": os.path.join(
                        nipype_deriv_subject_directory, "fMRI_pipeline"
                    ),
                    "log_to_file": True,
                },
                "execution": {
                    "remove_unnecessary_outputs": False,
                    "stop_on_first_crash": True,
                    "stop_on_first_rerun": False,
                    "use_relative_paths": True,
                    "crashfile_format": "txt",
                },
            }
        )

        logging.update_logging(config)

        iflogger = logging.getLogger("nipype.interface")
        iflogger.info("**** Processing ****")

        flow = self.create_pipeline_flow(
            cmp_deriv_subject_directory=cmp_deriv_subject_directory,
            nipype_deriv_subject_directory=nipype_deriv_subject_directory,
        )
        flow.write_graph(graph2use="colored", format="svg", simple_form=False)

        if self.number_of_cores != 1:
            flow.run(plugin="MultiProc", plugin_args={"n_procs": self.number_of_cores})
        else:
            flow.run()

        iflogger.info("**** Processing finished ****")

        return True
