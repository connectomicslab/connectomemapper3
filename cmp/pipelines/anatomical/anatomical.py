# Copyright (C) 2009-2021, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.


"""Anatomical pipeline Class definition."""

import datetime
import os
import glob
import shutil

import nipype.pipeline.engine as pe
import nipype.interfaces.utility as util
import nipype.interfaces.io as nio
from nipype import config, logging

from traits.api import *

# Own import
import cmp.pipelines.common as cmp_common
from cmp.stages.segmentation.segmentation import SegmentationStage
from cmp.stages.parcellation.parcellation import ParcellationStage


class Global_Configuration(HasTraits):
    """Global pipeline configurations.

    Attributes
    ----------
    process_type : 'anatomical'
        Processing pipeline type

    subjects : traits.List
       List of subjects ID (in the form ``sub-XX``)

    subject : traits.Str
       Subject to be processed (in the form ``sub-XX``)

    subject_session : traits.Str
       Subject session to be processed (in the form ``ses-YY``)
    """

    process_type = Str("anatomical")
    subjects = List(trait=Str)
    subject = Str
    subject_session = Str


class Check_Input_Notification(HasTraits):
    message = Str
    diffusion_imaging_model_options = List(["DSI", "DTI", "HARDI"])
    diffusion_imaging_model = Str
    diffusion_imaging_model_message = Str(
        "\nMultiple diffusion inputs available. Please select desired diffusion modality."
    )


class AnatomicalPipeline(cmp_common.Pipeline):
    """Class that extends a :class:`Pipeline` and represents the processing pipeline for structural MRI.

    It is composed of the segmentation stage that performs FreeSurfer recon-all
    and the parcellation stage that creates the Lausanne brain parcellations.

    See Also
    --------
    cmp.stages.segmentation.segmentation.SegmentationStage
    cmp.stages.parcellation.parcellation.ParcellationStage
    """

    now = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    pipeline_name = Str("anatomical_pipeline")
    input_folders = ["anat"]
    process_type = Str
    diffusion_imaging_model = Str
    parcellation_scheme = Str("Lausanne2008")
    atlas_info = Dict()
    subject_directory = Directory
    derivatives_directory = Directory
    ordered_stage_list = ["Segmentation", "Parcellation"]
    custom_last_stage = Enum("Parcellation", ["Segmentation", "Parcellation"])
    global_conf = Global_Configuration()
    config_file = Str
    flow = Instance(pe.Workflow)

    def __init__(self, project_info):
        """Constructor of an `AnatomicalPipeline` object.

        Parameters
        ----------
        project_info : cmp.project.CMP_Project_Info
            Instance of `CMP_Project_Info` object.

        See Also
        --------
        cmp.project.CMP_Project_Info
        """
        self.global_conf.subjects = project_info.subjects
        self.global_conf.subject = self.subject

        if len(project_info.subject_sessions) > 0:
            self.global_conf.subject_session = project_info.subject_session
            self.subject_directory = os.path.join(
                project_info.base_directory,
                project_info.subject,
                project_info.subject_session,
            )
            subject_id = "_".join((self.subject, self.global_conf.subject_session))
        else:
            self.global_conf.subject_session = ""
            self.subject_directory = os.path.join(
                project_info.base_directory, project_info.subject
            )
            subject_id = self.subject

        self.derivatives_directory = os.path.abspath(project_info.output_directory)
        self.output_directory = os.path.abspath(project_info.output_directory)

        self.stages = {
            "Segmentation": SegmentationStage(
                subject=self.global_conf.subject,
                session=self.global_conf.subject_session,
                bids_dir=project_info.base_directory,
                output_dir=self.output_directory
            ),
            "Parcellation": ParcellationStage(
                pipeline_mode="Diffusion",
                subject=self.global_conf.subject,
                session=self.global_conf.subject_session,
                bids_dir=project_info.base_directory,
                output_dir=self.output_directory,
            ),
        }
        cmp_common.Pipeline.__init__(self, project_info)

        self.subject = project_info.subject

        self.stages["Segmentation"].config.freesurfer_subjects_dir = os.path.join(
            self.output_directory, "freesurfer"
        )
        self.stages["Segmentation"].config.freesurfer_subject_id = os.path.join(
            self.output_directory, "freesurfer", subject_id
        )
        self.stages["Segmentation"].config.on_trait_change(
            self.update_parcellation, "seg_tool"
        )
        self.stages["Parcellation"].config.on_trait_change(
            self.update_segmentation, "parcellation_scheme"
        )
        self.stages["Parcellation"].config.on_trait_change(
            self.update_parcellation_scheme, "parcellation_scheme"
        )

    def check_config(self):
        """Check if custom white matter mask and custom atlas files specified in the configuration exist.

        Returns
        -------
        message : string
            String empty if all the checks pass, otherwise it contains the error message
        """
        message = ""
        if self.stages["Segmentation"].config.seg_tool == "Custom segmentation":
            if not os.path.exists(self.stages["Segmentation"].config.white_matter_mask):
                message = (
                    "\nCustom segmentation selected but no WM mask provided.\n"
                    "Please provide an existing WM mask file in the Segmentation configuration "
                    "window.\n"
                )
            if not os.path.exists(self.stages["Parcellation"].config.atlas_nifti_file):
                message = (
                    "\n\tCustom segmentation selected but no atlas provided.\n"
                    "Please specify an existing atlas file in the "
                    "Parcellation configuration window.\t\n"
                )
            if not os.path.exists(self.stages["Parcellation"].config.graphml_file):
                message = (
                    "\n\tCustom segmentation selected but no graphml info provided.\n"
                    "Please specify an existing graphml file in the "
                    "Parcellation configuration window.\t\n"
                )
        return message

    def update_parcellation_scheme(self):
        """Updates ``parcellation_scheme`` and ``atlas_info`` when ``parcellation_scheme`` is updated."""
        self.parcellation_scheme = self.stages[
            "Parcellation"
        ].config.parcellation_scheme
        self.atlas_info = self.stages["Parcellation"].config.atlas_info

    def update_parcellation(self):
        """Update self.stages['Parcellation'].config.parcellation_scheme when ``seg_tool`` is updated."""
        if self.stages["Segmentation"].config.seg_tool == "Custom segmentation":
            self.stages["Parcellation"].config.parcellation_scheme = "Custom"
        else:
            self.stages["Parcellation"].config.parcellation_scheme = self.stages[
                "Parcellation"
            ].config.pre_custom

    def update_segmentation(self):
        """Update self.stages['Segmentation'].config.seg_tool when ``parcellation_scheme`` is updated."""
        if self.stages["Parcellation"].config.parcellation_scheme == "Custom":
            self.stages["Segmentation"].config.seg_tool = "Custom segmentation"
        else:
            self.stages["Segmentation"].config.seg_tool = "Freesurfer"

    def define_custom_mapping(self, custom_last_stage):
        """Define the pipeline to be executed until a specific stages.

        Not used yet by CMP3.

        Parameters
        ----------
        custom_last_stage : string
            Last stage to execute. Valid values are
            "Segmentation" and "Parcellation"
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
        """Check if input of the anatomical pipeline are available.

        Parameters
        ----------
        layout : bids.BIDSLayout
            Instance of BIDSLayout

        gui : traits.Bool
            Boolean used to display different messages
            but not really meaningful anymore since the GUI
            components have been migrated to ``cmp.bidsappmanager``

        Returns
        -------

        valid_inputs : traits.Bool
            True if inputs are available
        """
        print("**** Check Inputs  ****")
        t1_available = False
        t1_json_available = False
        valid_inputs = False

        print("> Looking in %s for...." % self.base_directory)

        subjid = self.subject.split("-")[1]

        if self.global_conf.subject_session == "":
            T1_file = os.path.join(
                self.subject_directory, "anat", self.subject + "_T1w.nii.gz"
            )
            files = layout.get(subject=subjid, suffix="T1w", extensions=".nii.gz")
            if len(files) > 0:
                T1_file = os.path.join(files[0].dirname, files[0].filename)
                print(T1_file)
            else:
                return
        else:
            sessid = self.global_conf.subject_session.split("-")[1]
            files = layout.get(
                subject=subjid, suffix="T1w", extensions=".nii.gz", session=sessid
            )
            if len(files) > 0:
                T1_file = os.path.join(files[0].dirname, files[0].filename)
                print(T1_file)
            else:
                return

        print("... t1_file : %s" % T1_file)

        if self.global_conf.subject_session == "":
            T1_json_file = os.path.join(
                self.subject_directory, "anat", self.subject + "_T1w.json"
            )
            files = layout.get(subject=subjid, suffix="T1w", extensions=".json")
            if len(files) > 0:
                T1_json_file = os.path.join(files[0].dirname, files[0].filename)
                print(T1_json_file)
            else:
                T1_json_file = "NotFound"
        else:
            sessid = self.global_conf.subject_session.split("-")[1]
            files = layout.get(
                subject=subjid, suffix="T1w", extensions=".json", session=sessid
            )
            if len(files) > 0:
                T1_json_file = os.path.join(files[0].dirname, files[0].filename)
                print(T1_json_file)
            else:
                T1_json_file = "NotFound"

        print("... t1_json_file : %s" % T1_json_file)

        if os.path.isfile(T1_file):
            t1_available = True

        if os.path.isfile(T1_json_file):
            t1_json_available = True

        if t1_available:
            # Copy T1w data to derivatives / cmp  / subject / anat
            if self.global_conf.subject_session == "":
                out_T1_file = os.path.join(
                    self.output_directory,
                    "cmp",
                    self.subject,
                    "anat",
                    self.subject + "_desc-cmp_T1w.nii.gz",
                )
            else:
                out_T1_file = os.path.join(
                    self.output_directory,
                    "cmp",
                    self.subject,
                    self.global_conf.subject_session,
                    "anat",
                    self.subject
                    + "_"
                    + self.global_conf.subject_session
                    + "_desc-cmp_T1w.nii.gz",
                )

            if not os.path.isfile(out_T1_file):
                shutil.copy(src=T1_file, dst=out_T1_file)

            valid_inputs = True
            input_message = "Inputs check finished successfully. \nOnly anatomical data (T1) available."

            if t1_json_available:
                if self.global_conf.subject_session == "":
                    out_T1_json_file = os.path.join(
                        self.output_directory,
                        "cmp",
                        self.subject,
                        "anat",
                        self.subject + "_desc-cmp_T1w.json",
                    )
                else:
                    out_T1_json_file = os.path.join(
                        self.output_directory,
                        "cmp",
                        self.subject,
                        self.global_conf.subject_session,
                        "anat",
                        self.subject
                        + "_"
                        + self.global_conf.subject_session
                        + "_desc-cmp_T1w.json",
                    )

                if not os.path.isfile(out_T1_json_file):
                    shutil.copy(src=T1_json_file, dst=out_T1_json_file)

        else:
            if self.global_conf.subject_session == "":
                input_message = (
                    "Error during inputs check. No anatomical data available in folder "
                    + os.path.join(self.base_directory, self.subject)
                    + "/anat/!"
                )
            else:
                input_message = (
                    "Error during inputs check. No anatomical data available in folder "
                    + os.path.join(
                        self.base_directory,
                        self.subject,
                        self.global_conf.subject_session,
                    )
                    + "/anat/!"
                )

        print(input_message)

        if t1_available:
            valid_inputs = True
        else:
            print(
                "ERROR : Missing required inputs. ",
                "Please see documentation for more details."
            )

        if not t1_json_available:
            print(
                "Warning : Missing BIDS json sidecar. ",
                "Please see documentation for more details."
            )

        return valid_inputs

    def check_output(self):
        """Check if outputs of an :class:`AnatomicalPipeline` are available.

        Returns
        -------

        valid_output <Bool>
            True if all outputs are found

        error_message <string>
            Error message if an output is not found.

        """
        t1_available = False
        brain_available = False
        brainmask_available = False
        wm_available = False
        roivs_available = False
        valid_output = False

        subject = self.subject

        if self.global_conf.subject_session == "":
            anat_deriv_subject_directory = os.path.join(
                self.output_directory, "cmp", self.subject, "anat"
            )
        else:
            if self.global_conf.subject_session not in subject:
                anat_deriv_subject_directory = os.path.join(
                    self.output_directory,
                    "cmp",
                    subject,
                    self.global_conf.subject_session,
                    "anat",
                )
                subject = "_".join((subject, self.global_conf.subject_session))
            else:
                anat_deriv_subject_directory = os.path.join(
                    self.output_directory,
                    "cmp",
                    subject.split("_")[0],
                    self.global_conf.subject_session,
                    "anat",
                )

        T1_file = os.path.join(
            anat_deriv_subject_directory, subject + "_desc-head_T1w.nii.gz"
        )
        brain_file = os.path.join(
            anat_deriv_subject_directory, subject + "_desc-brain_T1w.nii.gz"
        )
        brainmask_file = os.path.join(
            anat_deriv_subject_directory, subject + "_desc-brain_mask.nii.gz"
        )
        wm_mask_file = os.path.join(
            anat_deriv_subject_directory, subject + "_label-WM_dseg.nii.gz"
        )

        if self.parcellation_scheme == "Lausanne2008":
            bids_atlas_label = "L2008"
        elif self.parcellation_scheme == "Lausanne2018":
            bids_atlas_label = "L2018"
        elif self.parcellation_scheme == "NativeFreesurfer":
            bids_atlas_label = "Desikan"

        if bids_atlas_label == "Desikan":
            roiv_files = glob.glob(
                os.path.join(
                    anat_deriv_subject_directory,
                    subject + "_atlas-" + bids_atlas_label + "_dseg.nii.gz",
                )
            )
        else:
            roiv_files = glob.glob(
                os.path.join(
                    anat_deriv_subject_directory,
                    subject + "_atlas-" + bids_atlas_label + "_res-scale*_dseg.nii.gz",
                )
            )

        error_message = ""

        if os.path.isfile(T1_file):
            t1_available = True
        else:
            error_message += (
                "  .. ERROR: Missing anatomical output T1w file %s . Please re-run the anatomical pipeline"
                % T1_file
            )

        if os.path.isfile(brain_file):
            brain_available = True
        else:
            error_message += (
                "  .. ERROR: Missing output brain masked T1w file %s . Please re-run the anatomical pipeline"
                % brain_file
            )

        if os.path.isfile(brainmask_file):
            brainmask_available = True
        else:
            error_message += (
                "  .. ERROR: Missing output brain mask file %s . Please re-run the anatomical pipeline"
                % brainmask_file
            )

        if os.path.isfile(wm_mask_file):
            wm_available = True
        else:
            error_message += (
                "  .. ERROR: Missing output white-matter mask file %s . Please re-run the anatomical pipeline"
                % wm_mask_file
            )

        cnt1 = 0
        cnt2 = 0
        for roiv_file in roiv_files:
            cnt1 = cnt1 + 1
            if os.path.isfile(roiv_file):
                cnt2 = cnt2 + 1
        if cnt1 == cnt2:
            roivs_available = True
        else:
            error_message += (
                "  .. ERROR : Missing %g/%g anatomical parcellation output files. Please re-run the anatomical pipeline"
                % (cnt1 - cnt2, cnt1)
            )

        if (
            t1_available is True
            and brain_available is True
            and brainmask_available is True
            and wm_available is True
            and roivs_available is True
        ):
            print("  .. INFO: Valid derivatives for anatomical pipeline")
            valid_output = True

        return valid_output, error_message

    def create_datagrabber_node(self, base_directory):
        """Create the appropriate Nipype DataGrabber node.`

        Parameters
        ----------
        base_directory : Directory
            Main CMP output directory of a subject
            e.g. ``/output_dir/cmp/sub-XX/(ses-YY)``

        Returns
        -------
        datasource : Output Nipype DataGrabber Node
            Output Nipype Node with :obj:`~nipype.interfaces.io.DataGrabber` interface
        """
        datasource = pe.Node(
            interface=nio.DataGrabber(outfields=["T1"]), name="anat_datasource"
        )
        datasource.inputs.base_directory = os.path.abspath(base_directory)
        datasource.inputs.template = "*"
        datasource.inputs.raise_on_empty = False
        datasource.inputs.field_template = dict(
            T1="anat/" + self.subject + "_desc-cmp_T1w.nii.gz"
        )
        datasource.inputs.sort_filelist = False

        return datasource

    def create_datasinker_node(self, base_directory):
        """Create the appropriate Nipype DataSink node depending on the `parcellation_scheme`

        Parameters
        ----------
        base_directory : Directory
            Main CMP output directory of a subject
            e.g. ``/output_dir/cmp/sub-XX/(ses-YY)``

        Returns
        -------
        sinker : Output Nipype DataSink Node
            Output Nipype Node with :obj:`~nipype.interfaces.io.DataSink` interface
        """
        sinker = pe.Node(nio.DataSink(), name="anat_datasinker")
        sinker.inputs.base_directory = os.path.abspath(base_directory)
        # sinker.inputs.parametrization = True  # Store output in parametrized structure (for MapNode)

        sinker.inputs.substitutions = [
            ("T1.nii.gz", self.subject + "_desc-head_T1w.nii.gz"),
            ("brain.nii.gz", self.subject + "_desc-brain_T1w.nii.gz"),
            ("brain_mask.nii.gz", self.subject + "_desc-brain_mask.nii.gz"),
            ("aseg.nii.gz", self.subject + "_desc-aseg_dseg.nii.gz"),
            ("csf_mask.nii.gz", self.subject + "_label-CSF_dseg.nii.gz"),
            ("fsmask_1mm.nii.gz", self.subject + "_label-WM_dseg.nii.gz"),
            ("gmmask.nii.gz", self.subject + "_label-GM_dseg.nii.gz"),
            ("T1w_class-GM.nii.gz", self.subject + "_label-GM_dseg.nii.gz"),
            ("wm_eroded.nii.gz", self.subject + "_label-WM_desc-eroded_dseg.nii.gz"),
            ("csf_eroded.nii.gz", self.subject + "_label-CSF_desc-eroded_dseg.nii.gz"),
            ("brain_eroded.nii.gz", self.subject + "_label-brain_desc-eroded_dseg.nii.gz"),
        ]
        # Dataname substitutions in order to comply with BIDS derivatives specifications
        if self.parcellation_scheme == "Lausanne2008":
            # fmt: off
            scale_mapping = {
                "scale1": "83",
                "scale2": "150",
                "scale3": "258",
                "scale4": "500",
                "scale5": "1015",
            }
            for i, scale in enumerate(['scale1', 'scale2', 'scale3', 'scale4', 'scale5']):
                sinker.inputs.substitutions.append(
                    ("aparc+aseg.native.nii.gz", self.subject + "_desc-aparcaseg_dseg.nii.gz")
                )
                sinker.inputs.substitutions.append(
                    (f'ROIv_Lausanne2008_{scale}.nii.gz', self.subject + f'_atlas-L2008_res-{scale}_dseg.nii.gz')
                )
                sinker.inputs.substitutions.append(
                    (f'ROIv_Lausanne2008_{scale}_final.nii.gz', self.subject + f'_atlas-L2008_res-{scale}_dseg.nii.gz')
                )
                sinker.inputs.substitutions.append(
                    (f'resolution{scale_mapping[scale]}.graphml', self.subject + f'_atlas-L2008_res-{scale}_dseg.graphml')
                )
                sinker.inputs.substitutions.append(
                    (f'resolution{scale_mapping[scale]}_LUT.txt', self.subject + f'_atlas-L2008_res-{scale}_FreeSurferColorLUT.txt')
                )
                sinker.inputs.substitutions.append(
                    (f'_createBIDSLabelIndexMappingFile{i}/', '')
                )
                sinker.inputs.substitutions.append(
                    (f'resolution{scale_mapping[scale]}.tsv', self.subject + f'_atlas-L2008_res-{scale}_dseg.tsv')
                )
                sinker.inputs.substitutions.append(
                    (f'roi_stats_{scale}.tsv', self.subject + f'_atlas-L2008_res-{scale}_stats.tsv')
                )
            # fmt: on
        elif self.parcellation_scheme == "Lausanne2018":
            # fmt: off
            for i, scale in enumerate(['scale1', 'scale2', 'scale3', 'scale4', 'scale5']):
                sinker.inputs.substitutions.append(
                    ("aparc+aseg.Lausanne2018.native.nii.gz", self.subject + "_desc-aparcaseg_dseg.nii.gz")
                )
                sinker.inputs.substitutions.append(
                    (f'ROIv_Lausanne2018_{scale}.nii.gz', self.subject + f'_atlas-L2018_res-{scale}_dseg.nii.gz')
                )
                sinker.inputs.substitutions.append(
                    (f'ROIv_Lausanne2018_{scale}_final.nii.gz', self.subject + f'_atlas-L2018_res-{scale}_dseg.nii.gz')
                )
                sinker.inputs.substitutions.append(
                    (f'ROIv_Lausanne2018_{scale}.graphml', self.subject + f'_atlas-L2018_res-{scale}_dseg.graphml')
                )
                sinker.inputs.substitutions.append(
                    (f'ROIv_Lausanne2018_{scale}_FreeSurferColorLUT.txt', self.subject + f'_atlas-L2018_res-{scale}_FreeSurferColorLUT.txt')
                )
                sinker.inputs.substitutions.append(
                    (f'_createBIDSLabelIndexMappingFile{i}/', '')
                )
                sinker.inputs.substitutions.append(
                    (f'ROIv_Lausanne2018_{scale}.tsv', self.subject + f'_atlas-L2018_res-{scale}_dseg.tsv')
                )
                sinker.inputs.substitutions.append(
                    (f'roi_stats_{scale}.tsv', self.subject + f'_atlas-L2018_res-{scale}_stats.tsv')
                )
            # fmt: on
        elif self.parcellation_scheme == "NativeFreesurfer":
            # fmt: off
            sinker.inputs.substitutions.append(
                ("aparc+aseg.native.nii.gz", self.subject + "_desc-aparcaseg_dseg.nii.gz")
            )
            sinker.inputs.substitutions.append(
                ("ROIv_HR_th_freesurferaparc.nii.gz", self.subject + "_atlas-Desikan_dseg.nii.gz")
            )
            sinker.inputs.substitutions.append(
                ("freesurferaparc.graphml", self.subject + "_atlas-Desikan_dseg.graphml")
            )
            sinker.inputs.substitutions.append(
                ("FreeSurferColorLUT_adapted.txt", self.subject + "_atlas-Desikan_FreeSurferColorLUT.txt")
            )
            sinker.inputs.substitutions.append(
                ("freesurferaparc.tsv", self.subject + "_atlas-Desikan_dseg.tsv")
            )
            sinker.inputs.substitutions.append(
                ("roi_stats_freesurferaparc.tsv", self.subject + "_atlas-Desikan_stats.tsv")
            )
            # fmt: on
        elif self.parcellation_scheme == "Custom":
            # TODO
            # fmt: off
            sinker.inputs.substitutions = [

            ]
            # fmt: on

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
        anat_flow : nipype.pipeline.engine.Workflow
            An instance of :class:`nipype.pipeline.engine.Workflow`
        """
        # Data grabber for inputs
        datasource = self.create_datagrabber_node(
            base_directory=cmp_deriv_subject_directory
        )

        # Data sinker for outputs
        sinker = self.create_datasinker_node(
            base_directory=cmp_deriv_subject_directory
        )

        # Clear previous outputs
        self.clear_stages_outputs()

        # Create common_flow
        anat_flow = pe.Workflow(
            name="anatomical_pipeline",
            base_dir=os.path.abspath(nipype_deriv_subject_directory),
        )
        anat_inputnode = pe.Node(
            interface=util.IdentityInterface(fields=["T1"]), name="inputnode"
        )
        anat_outputnode = pe.Node(
            interface=util.IdentityInterface(
                fields=[
                    "subjects_dir",
                    "subject_id",
                    "T1",
                    "aseg",
                    "aparc_aseg",
                    "brain",
                    "brain_mask",
                    "csf_mask_file",
                    "wm_mask_file",
                    "gm_mask_file",
                    "wm_eroded",
                    "brain_eroded",
                    "csf_eroded",
                    "roi_volumes",
                    "parcellation_scheme",
                    "atlas_info",
                    "roi_colorLUTs",
                    "roi_graphMLs",
                    "roi_TSVs",
                    "roi_volumes_stats",
                ]
            ),
            name="outputnode",
        )
        anat_flow.add_nodes([anat_inputnode, anat_outputnode])
        # fmt:off
        anat_flow.connect(
            [
                (datasource, anat_inputnode, [("T1", "T1")]),
            ]
        )
        # fmt:on

        seg_flow = self.create_stage_flow("Segmentation")
        # fmt: off
        anat_flow.connect(
            [
                (anat_inputnode, seg_flow, [("T1", "inputnode.T1")])
            ]
        )
        # fmt: on

        parc_flow = self.create_stage_flow("Parcellation")

        if self.stages["Segmentation"].config.seg_tool == "Freesurfer":

            self.stages[
                "Segmentation"
            ].config.freesurfer_subjects_dir = os.path.join(
                self.output_directory, "freesurfer"
            )
            self.stages[
                "Segmentation"
            ].config.freesurfer_subject_id = os.path.join(
                self.output_directory, "freesurfer", self.subject
            )

            # fmt: off
            anat_flow.connect(
                [
                    (seg_flow, parc_flow, [("outputnode.subjects_dir", "inputnode.subjects_dir"),
                                           ("outputnode.subject_id", "inputnode.subject_id")]),
                    (seg_flow, anat_outputnode, [("outputnode.subjects_dir", "subjects_dir"),
                                                 ("outputnode.subject_id", "subject_id")]),
                    (parc_flow, anat_outputnode, [("outputnode.wm_mask_file", "wm_mask_file"),
                                                  ("outputnode.parcellation_scheme", "parcellation_scheme"),
                                                  ("outputnode.atlas_info", "atlas_info"),
                                                  ("outputnode.roi_volumes", "roi_volumes"),
                                                  ("outputnode.roi_colorLUTs", "roi_colorLUTs"),
                                                  ("outputnode.roi_graphMLs", "roi_graphMLs"),
                                                  ("outputnode.roi_TSVs", "roi_TSVs"),
                                                  ("outputnode.roi_volumes_stats", "roi_volumes_stats"),
                                                  ("outputnode.wm_eroded", "wm_eroded"),
                                                  ("outputnode.gm_mask_file", "gm_mask_file"),
                                                  ("outputnode.csf_mask_file", "csf_mask_file"),
                                                  ("outputnode.csf_eroded", "csf_eroded"),
                                                  ("outputnode.brain_eroded", "brain_eroded"),
                                                  ("outputnode.T1", "T1"),
                                                  ("outputnode.aseg", "aseg"),
                                                  ("outputnode.aparc_aseg", "aparc_aseg"),
                                                  ("outputnode.brain_mask", "brain_mask"),
                                                  ("outputnode.brain", "brain")])
                ]
            )
            # fmt: on
        else:
            # fmt: off
            anat_flow.connect(
                [
                    (seg_flow, parc_flow, [("outputnode.custom_wm_mask", "inputnode.custom_wm_mask")]),
                    (seg_flow, anat_outputnode, [("outputnode.brain_mask", "brain_mask"),
                                                 ("outputnode.brain", "brain")]),
                    (anat_inputnode, anat_outputnode, [("T1", "T1")]),
                    (parc_flow, anat_outputnode, [("outputnode.wm_mask_file", "wm_mask_file"),
                                                  ("outputnode.parcellation_scheme", "parcellation_scheme"),
                                                  ("outputnode.atlas_info", "atlas_info"),
                                                  ("outputnode.roi_volumes", "roi_volumes"),
                                                  ("outputnode.wm_eroded", "wm_eroded"),
                                                  ("outputnode.gm_mask_file", "gm_mask_file"),
                                                  ("outputnode.csf_eroded", "csf_eroded"),
                                                  ("outputnode.brain_eroded", "brain_eroded")])
                ]
            )
            # fmt: on

        # fmt: off
        anat_flow.connect(
            [
                (anat_outputnode, sinker, [("T1", "anat.@T1")]),
                (anat_outputnode, sinker, [("aseg", "anat.@aseg")]),
                (anat_outputnode, sinker, [("aparc_aseg", "anat.@aparc_aseg")]),
                (anat_outputnode, sinker, [("brain", "anat.@brain")]),
                (anat_outputnode, sinker, [("brain_mask", "anat.@brain_mask")]),
                (anat_outputnode, sinker, [("wm_mask_file", "anat.@wm_mask")]),
                (anat_outputnode, sinker, [("gm_mask_file", "anat.@gm_mask")]),
                (anat_outputnode, sinker, [("csf_mask_file", "anat.@csf_mask")]),
                (anat_outputnode, sinker, [("roi_volumes", "anat.@roivs")]),
                (anat_outputnode, sinker, [("roi_colorLUTs", "anat.@luts")]),
                (anat_outputnode, sinker, [("roi_graphMLs", "anat.@graphmls")]),
                (anat_outputnode, sinker, [("roi_TSVs", "anat.@tsvs")]),
                (anat_outputnode, sinker, [("roi_volumes_stats", "anat.@stats")]),
                (anat_outputnode, sinker, [("brain_eroded", "anat.@brainmask_eroded")]),
                (anat_outputnode, sinker, [("wm_eroded", "anat.@wm_eroded")]),
                (anat_outputnode, sinker, [("csf_eroded", "anat.@csf_eroded")]),
            ]
        )
        # fmt: on

        self.flow = anat_flow
        return anat_flow

    def process(self):
        """Executes the anatomical pipeline workflow and returns True if successful."""
        # Enable the use of the W3C PROV data model to capture and represent provenance in Nipype
        # config.enable_provenance()

        # Process time
        self.now = datetime.datetime.now().strftime("%Y%m%d_%H%M")

        if "_" in self.subject:
            self.subject = self.subject.split("_")[0]

        if self.global_conf.subject_session == "":
            cmp_deriv_subject_directory = os.path.join(
                self.output_directory, "cmp", self.subject
            )
            nipype_deriv_subject_directory = os.path.join(
                self.output_directory, "nipype", self.subject
            )
        else:
            cmp_deriv_subject_directory = os.path.join(
                self.output_directory,
                "cmp",
                self.subject,
                self.global_conf.subject_session,
            )
            nipype_deriv_subject_directory = os.path.join(
                self.output_directory,
                "nipype",
                self.subject,
                self.global_conf.subject_session,
            )

            self.subject = "_".join((self.subject, self.global_conf.subject_session))

        if not os.path.exists(
            os.path.join(nipype_deriv_subject_directory, "anatomical_pipeline")
        ):
            try:
                os.makedirs(
                    os.path.join(nipype_deriv_subject_directory, "anatomical_pipeline")
                )
            except os.error:
                print(
                    "%s was already existing"
                    % os.path.join(
                        nipype_deriv_subject_directory, "anatomical_pipeline"
                    )
                )

        # Initialization
        if os.path.isfile(
            os.path.join(
                nipype_deriv_subject_directory, "anatomical_pipeline", "pypeline.log"
            )
        ):
            os.unlink(
                os.path.join(
                    nipype_deriv_subject_directory,
                    "anatomical_pipeline",
                    "pypeline.log",
                )
            )
        config.update_config(
            {
                "logging": {
                    "workflow_level": "DEBUG",
                    "interface_level": "DEBUG",
                    "log_directory": os.path.join(
                        nipype_deriv_subject_directory, "anatomical_pipeline"
                    ),
                    "log_to_file": True,
                },
                "execution": {
                    "remove_unnecessary_outputs": False,
                    "stop_on_first_crash": True,
                    "stop_on_first_rerun": False,
                    "try_hard_link_datasink": True,
                    "use_relative_paths": True,
                    "crashfile_format": "txt",
                },
            }
        )
        logging.update_logging(config)

        iflogger = logging.getLogger("nipype.interface")
        iflogger.info("**** Processing ****")

        anat_flow = self.create_pipeline_flow(
            cmp_deriv_subject_directory=cmp_deriv_subject_directory,
            nipype_deriv_subject_directory=nipype_deriv_subject_directory,
        )
        anat_flow.write_graph(graph2use="colored", format="svg", simple_form=True)

        if self.number_of_cores != 1:
            anat_flow.run(
                plugin="MultiProc", plugin_args={"n_procs": self.number_of_cores}
            )
        else:
            anat_flow.run()

        iflogger.info("**** Processing finished ****")

        return True
