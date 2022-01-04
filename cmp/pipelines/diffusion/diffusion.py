# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""Diffusion pipeline Class definition."""

# Own imports
import datetime
import shutil

import nipype.interfaces.io as nio
from bids import BIDSLayout
from nipype import config, logging
from nipype.interfaces.utility import Merge

# Own imports
from cmtklib.bids.io import __cmp_directory__, __nipype_directory__
from cmp.pipelines.common import *
from cmp.stages.connectome.connectome import ConnectomeStage
from cmp.stages.diffusion.diffusion import DiffusionStage
from cmp.stages.preprocessing.preprocessing import PreprocessingStage
from cmp.stages.registration.registration import RegistrationStage


class GlobalConfiguration(HasTraits):
    """Global pipeline configurations.

    Attributes
    ----------
    process_type : 'fMRI'
        Processing pipeline type

    subjects : traits.List
       List of subjects ID (in the form ``sub-XX``)

    subject : traits.Str
       Subject to be processed (in the form ``sub-XX``)

    subject_session : traits.Str
       Subject session to be processed (in the form ``ses-YY``)

    modalities : traits.List
       List of available diffusion modalities red from
       the ``acq-<modality>`` filename keyword

    dmri_bids_acq : traits.Str
       Diffusion modality to be processed
    """

    process_type = Str("diffusion")
    diffusion_imaging_model = Str
    subjects = List(trait=Str)
    subject = Str
    subject_session = Str
    # modalities = List(trait=Str)
    dmri_bids_acq = Str


class DiffusionPipeline(Pipeline):
    """Class that extends a :class:`Pipeline` and represents the processing pipeline for diffusion MRI.

    It is composed of the preprocessing stage that preprocesses dMRI,
    the registration stage that co-registers T1w to the diffusion B0 and
    projects the parcellations to the native diffusion space, the diffusion
    stage that estimates tensors or fiber orientation distributions functions
    from the diffusion signal and reconstructs fiber using tractography, and
    finally the connectome stage that combines the output tractogram with
    the parcellations to create the structural connectivity matrices.

    See Also
    --------
    cmp.stages.preprocessing.preprocessing.PreprocessingStage
    cmp.stages.registration.registration.RegistrationStage
    cmp.stages.diffusion.diffusion.DiffusionStage
    cmp.stages.connectome.connectome.ConnectomeStage
    """

    now = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    pipeline_name = Str("diffusion_pipeline")
    input_folders = ["anat", "dwi"]
    process_type = Str
    diffusion_imaging_model = Str
    subject = Str
    subject_directory = Directory
    derivatives_directory = Directory
    ordered_stage_list = ["Preprocessing", "Registration", "Diffusion", "Connectome"]
    parcellation_scheme = Str
    custom_atlas_name = Str
    custom_atlas_res = Str
    atlas_info = Dict()
    global_conf = GlobalConfiguration()
    config_file = Str

    def __init__(self, project_info):
        """Constructor of a `DiffusionPipeline` object.

        Parameters
        ----------
        project_info : cmp.project.ProjectInfo
            Instance of `CMP_Project_Info` object.

        See Also
        --------
        cmp.project.CMP_Project_Info
        """
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
        self.output_directory = os.path.abspath(project_info.output_directory)

        self.stages = {
            "Preprocessing": PreprocessingStage(
                bids_dir=project_info.base_directory, output_dir=self.output_directory
            ),
            "Registration": RegistrationStage(
                pipeline_mode="Diffusion",
                fs_subjects_dir=project_info.freesurfer_subjects_dir,
                fs_subject_id=os.path.basename(project_info.freesurfer_subject_id),
                bids_dir=project_info.base_directory,
                output_dir=self.output_directory,
            ),
            "Diffusion": DiffusionStage(
                bids_dir=project_info.base_directory, output_dir=self.output_directory
            ),
            "Connectome": ConnectomeStage(
                bids_dir=project_info.base_directory, output_dir=self.output_directory
            ),
        }

        Pipeline.__init__(self, project_info)

        self.subject = project_info.subject
        self.diffusion_imaging_model = project_info.diffusion_imaging_model

        self.stages["Preprocessing"].config.tracking_tool = self.stages["Diffusion"].config.tracking_processing_tool
        self.stages["Preprocessing"].config.act_tracking = self.stages["Diffusion"].config.mrtrix_tracking_config.use_act
        self.stages["Preprocessing"].config.gmwmi_seeding = self.stages["Diffusion"].config.mrtrix_tracking_config.seed_from_gmwmi
        self.stages["Registration"].config.tracking_tool = self.stages["Diffusion"].config.tracking_processing_tool
        self.stages["Registration"].config.act_tracking = self.stages["Diffusion"].config.mrtrix_tracking_config.use_act
        self.stages["Registration"].config.gmwmi_seeding = self.stages["Diffusion"].config.mrtrix_tracking_config.seed_from_gmwmi

        self.stages["Connectome"].config.on_trait_change(
            self.update_vizualization_layout, "circular_layout"
        )
        self.stages["Connectome"].config.on_trait_change(
            self.update_vizualization_logscale, "log_visualization"
        )
        self.stages["Diffusion"].config.on_trait_change(
            self.update_outputs_recon, "recon_processing_tool"
        )
        self.stages["Diffusion"].config.on_trait_change(
            self.update_tracking_tool, "tracking_processing_tool"
        )
        self.stages["Diffusion"].config.mrtrix_tracking_config.on_trait_change(
            self.update_preprocessing_act, "use_act"
        )
        self.stages["Diffusion"].config.mrtrix_tracking_config.on_trait_change(
            self.update_preprocessing_gmwmi, "seed_from_gmwmi"
        )
        self.stages["Diffusion"].config.dipy_tracking_config.on_trait_change(
            self.update_preprocessing_act, "use_act"
        )
        self.stages["Diffusion"].config.on_trait_change(
            self.update_outputs_recon, "recon_processing_tool"
        )
        # self.anat_flow = anat_flow

    def update_outputs_recon(self, new):
        """Update list of of outputs of the diffusion stage when ``recon_processing_tool`` is updated.

        Parameters
        ----------
        new : string
            New value.
        """
        self.stages["Diffusion"].define_inspect_outputs()

    def update_outputs_tracking(self, new):
        """Update list of of outputs of the diffusion stage when ``tracking_processing_tool`` is updated.

        Parameters
        ----------
        new : string
            New value.
        """
        self.stages["Diffusion"].define_inspect_outputs()

    def update_vizualization_layout(self, new):
        """Update list of of outputs of the connectome stage when ``circular_layout`` is updated.

        Parameters
        ----------
        new : string
            New value.
        """
        self.stages["Connectome"].define_inspect_outputs()
        self.stages["Connectome"].config.subject = self.subject

    def update_vizualization_logscale(self, new):
        """Update list of of outputs of the connectome stage when ``log_visualization`` is updated.

        Parameters
        ----------
        new : bool
            New value.
        """
        self.stages["Connectome"].define_inspect_outputs()
        self.stages["Connectome"].config.subject = self.subject

    def update_tracking_tool(self, new):
        """Update ``self.stages["Preprocessing"].config.tracking_tool`` when ``tracking_processing_tool`` is updated.

        Parameters
        ----------
        new : string
            New value.
        """
        self.stages["Preprocessing"].config.tracking_tool = new
        self.stages["Registration"].config.tracking_tool = new

    def update_preprocessing_act(self, new):
        """Update ``self.stages["Preprocessing"].config.act_tracking`` when ``use_act`` is updated.

        Parameters
        ----------
        new : string
            New value.
        """
        self.stages["Preprocessing"].config.act_tracking = new
        self.stages["Registration"].config.act_tracking = new
        if not new:
            self.stages["Preprocessing"].config.gmwmi_seeding = False
            self.stages["Registration"].config.gmwmi_seeding = False

    def update_preprocessing_gmwmi(self, new):
        """Update ``self.stages["Preprocessing"].config.gmwmi_seeding`` when ``seed_from_gmwmi`` is updated.

        Parameters
        ----------
        new : string
            New value.
        """
        self.stages["Preprocessing"].config.gmwmi_seeding = new
        self.stages["Registration"].config.gmwmi_seeding = new

    def _subject_changed(self, new):
        """Update subject in the connectome stage configuration when ``subject`` is updated.

        Parameters
        ----------
        new : string
            New value.
        """
        self.stages["Connectome"].config.subject = new

    def _diffusion_imaging_model_changed(self, new):
        """Update ``self.stages['Diffusion'].config.diffusion_imaging_model`` when ``diffusion_imaging_model`` is updated.

        Parameters
        ----------
        new : string
            New value.
        """
        # print "diffusion model changed"
        self.stages["Diffusion"].config.diffusion_imaging_model = new

    def check_config(self):
        """Check if the list output formats in the configuration of the connectome stage is not empty.

        Returns
        -------
        message : string
            String that is empty if success, otherwise it contains the error message
        """
        message = ""
        if not self.stages["Connectome"].config.output_types:
            message = (
                "\n\tNo output type selected for the connectivity matrices.\t\n\t"
                "Please select at least one output type in the connectome configuration window.\t\n"
            )
        return message

    def define_custom_mapping(self, custom_last_stage):
        """Define the pipeline to be executed until a specific stages.

        Not used yet by CMP3.

        Parameters
        ----------
        custom_last_stage : string
            Last stage to execute. Valid values are: "Preprocessing",
            "Registration", "Diffusion" and "Connectome".
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

    def _atlas_info_changed(self, new):
        pass

    def get_file(self, layout, subject, suffix, extensions, session=None):
        """Query files with PyBIDS and take the first file in the returned list or get a specific dmri file if BIDS acq- keyword is used in filename.

        Parameters
        ----------
        layout : Instance(BIDSLayout)
            Instance of pybids BIDSLayout

        subject : str
            BIDS subject/participant label i.e. XX in sub-XX

        suffix : str
            BIDS file suffix i.e. "T1w", "dwi", ...

        extensions : str
            File extension i.e. ".nii.gz", ".json", ".bval", ...

        session : str
           BIDS session label i.e. YY in ses-YY if the dataset has multiple sessions

        Returns
        -------
        out_file : str
            The output filepath or None if no file was found
        """
        if session is None:
            files = layout.get(subject=subject, suffix=suffix, extension=extensions)
        else:
            files = layout.get(subject=subject, suffix=suffix, extension=extensions, session=session)

        if len(files) > 0:
            out_file = os.path.join(files[0].dirname, files[0].filename)

            if self.global_conf.dmri_bids_acq != "":
                for file in files:
                    if self.global_conf.dmri_bids_acq in file.filename:
                        out_file = os.path.join(file.dirname, file.filename)
                        break

            # TODO: Better parsing of multiple runs
        else:
            out_file = None

        return out_file

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
        print("**** Check Inputs  ****")
        diffusion_available = False
        diffusion_json_available = False
        bvecs_available = False
        bvals_available = False
        valid_inputs = False

        if self.global_conf.subject_session == "":
            subject = self.subject
        else:
            subject = "_".join((self.subject, self.global_conf.subject_session))

        subjid = self.subject.split("-")[1]

        try:
            layout = BIDSLayout(self.base_directory)
            for subj in layout.get_subjects():
                self.global_conf.subjects.append("sub-" + str(subj))

            print("> Looking for....")

            if self.global_conf.subject_session == "":

                dwi_file = self.get_file(layout, subject=subjid, suffix="dwi", extensions=".nii.gz")
                if dwi_file is None:
                    print("ERROR : Diffusion image not found for subject %s." % subjid)
                    return

                json_file = self.get_file(layout, subject=subjid, suffix="dwi", extensions=".json")
                if json_file is None:
                    json_file = "NotFound"
                    print(
                        "WARNING : Diffusion json sidecar not found for subject %s."
                        % subjid
                    )

                bval_file = self.get_file(layout, subject=subjid, suffix="dwi", extensions=".bval")
                if bval_file is None:
                    print(
                        "ERROR : Diffusion bval image not found for subject %s."
                        % subjid
                    )
                    return

                bvec_file = self.get_file(layout, subject=subjid, suffix="dwi", extensions=".bvec")
                if bvec_file is None:
                    print(
                        "ERROR : Diffusion bvec image not found for subject %s."
                        % subjid
                    )
                    return
            else:
                sessid = self.global_conf.subject_session.split("-")[1]

                dwi_file = self.get_file(layout, subject=subjid, suffix="dwi", extensions=".nii.gz", session=sessid)
                if dwi_file is None:
                    print(
                        "ERROR : Diffusion image not found for subject %s, session %s."
                        % (subjid, sessid)
                    )
                    return

                json_file = self.get_file(
                    layout, subject=subjid, suffix="dwi", extensions=".json", session=sessid
                )
                if json_file is None:
                    json_file = "NotFound"
                    print(
                        "WARNING : Diffusion json sidecar not found for subject %s, session %s."
                        % (subjid, self.global_conf.subject_session)
                    )

                bval_file = self.get_file(
                    layout, subject=subjid, suffix="dwi", extensions=".bval", session=sessid
                )
                if bval_file is None:
                    print(
                        "ERROR : Diffusion bval image not found for subject %s, session %s."
                        % (subjid, self.global_conf.subject_session)
                    )
                    return

                bvec_file = self.get_file(
                    layout, subject=subjid, suffix="dwi", extensions=".bvec", session=sessid
                )
                if bvec_file is None:
                    print(
                        "ERROR : Diffusion bvec image not found for subject %s, session %s."
                        % (subjid, self.global_conf.subject_session)
                    )
                    return

            print("... dwi_file : %s" % dwi_file)
            print("... json_file : %s" % json_file)
            print("... bvecs_file : %s" % bvec_file)
            print("... bvals_file : %s" % bval_file)

            if os.path.isfile(dwi_file):
                diffusion_available = True

        except Exception as e:
            print(f"Invalid BIDS dataset.\n\n\t{e}\n\nPlease see documentation for more details.")
            return

        if os.path.isfile(json_file):
            diffusion_json_available = True
        if os.path.isfile(bval_file):
            bvals_available = True
        if os.path.isfile(bvec_file):
            bvecs_available = True

        if diffusion_available:
            if bvals_available and bvecs_available:
                self.stages[
                    "Diffusion"
                ].config.diffusion_imaging_model_choices = self.diffusion_imaging_model

                # Copy diffusion data to derivatives / cmp  / subject / dwi
                if self.global_conf.subject_session == "":
                    out_dwi_file = os.path.join(
                        self.output_directory,
                        __cmp_directory__,
                        self.subject,
                        "dwi",
                        subject + "_desc-cmp_dwi.nii.gz",
                    )
                    out_bval_file = os.path.join(
                        self.output_directory,
                        __cmp_directory__,
                        self.subject,
                        "dwi",
                        subject + "_desc-cmp_dwi.bval",
                    )
                    out_bvec_file = os.path.join(
                        self.output_directory,
                        __cmp_directory__,
                        self.subject,
                        "dwi",
                        subject + "_desc-cmp_dwi.bvec",
                    )
                else:
                    out_dwi_file = os.path.join(
                        self.output_directory,
                        __cmp_directory__,
                        self.subject,
                        self.global_conf.subject_session,
                        "dwi",
                        subject + "_desc-cmp_dwi.nii.gz",
                    )
                    out_bval_file = os.path.join(
                        self.output_directory,
                        __cmp_directory__,
                        self.subject,
                        self.global_conf.subject_session,
                        "dwi",
                        subject + "_desc-cmp_dwi.bval",
                    )
                    out_bvec_file = os.path.join(
                        self.output_directory,
                        __cmp_directory__,
                        self.subject,
                        self.global_conf.subject_session,
                        "dwi",
                        subject + "_desc-cmp_dwi.bvec",
                    )

                if not os.path.isfile(out_dwi_file):
                    shutil.copy(src=dwi_file, dst=out_dwi_file)
                if not os.path.isfile(out_bvec_file):
                    shutil.copy(src=bvec_file, dst=out_bvec_file)
                if not os.path.isfile(out_bval_file):
                    shutil.copy(src=bval_file, dst=out_bval_file)

                valid_inputs = True
                input_message = "Inputs check finished successfully.\n" +\
                                "Diffusion and morphological data available."

                if diffusion_json_available:
                    if self.global_conf.subject_session == "":
                        out_json_file = os.path.join(
                            self.output_directory,
                            __cmp_directory__,
                            self.subject,
                            "dwi",
                            self.subject + "_desc-cmp_dwi.json",
                        )
                    else:
                        out_json_file = os.path.join(
                            self.output_directory,
                            __cmp_directory__,
                            self.subject,
                            self.global_conf.subject_session,
                            "dwi",
                            self.subject
                            + "_"
                            + self.global_conf.subject_session
                            + "_desc-cmp_dwi.json",
                        )

                    if not os.path.isfile(out_json_file):
                        shutil.copy(src=json_file, dst=out_json_file)
            else:
                input_message = "Error during inputs check.\nDiffusion bvec or bval files not available."
        else:
            if self.global_conf.subject_session == "":
                input_message = (
                    "Error during inputs check. No diffusion data available in folder "
                    + os.path.join(self.base_directory, self.subject, "dwi")
                    + "!"
                )
            else:
                input_message = (
                    "Error during inputs check. No diffusion data available in folder "
                    + os.path.join(
                        self.base_directory,
                        self.subject,
                        self.global_conf.subject_session,
                        "dwi",
                    )
                    + "!"
                )

        if gui:
            print(input_message)
            self.global_conf.diffusion_imaging_model = self.diffusion_imaging_model

            self.stages[
                "Registration"
            ].config.diffusion_imaging_model = self.diffusion_imaging_model
            self.stages[
                "Diffusion"
            ].config.diffusion_imaging_model = self.diffusion_imaging_model
        else:
            print(input_message)
            self.global_conf.diffusion_imaging_model = self.diffusion_imaging_model

            self.stages[
                "Registration"
            ].config.diffusion_imaging_model = self.diffusion_imaging_model
            self.stages[
                "Diffusion"
            ].config.diffusion_imaging_model = self.diffusion_imaging_model

        if diffusion_available:
            valid_inputs = True
        else:
            print(
                "ERROR : Missing required inputs.Please see documentation for more details."
            )

        return valid_inputs

    def create_field_template_dict(self, bids_atlas_label):
        """Create the dictionary of input field template given to Nipype DataGrabber`

        Parameters
        ----------
        bids_atlas_label : string
            Parcellation atlas label

        Returns
        -------
        field_template : dict
            Output dictionary of template input formats given to Nipype DataGrabber
        """
        if self.parcellation_scheme == "NativeFreesurfer":
            # fmt:off
            field_template = dict(
                diffusion="dwi/" + self.subject + "_desc-cmp_dwi.nii.gz",
                bvecs="dwi/" + self.subject + "_desc-cmp_dwi.bvec",
                bvals="dwi/" + self.subject + "_desc-cmp_dwi.bval",
                T1="anat/" + self.subject + "_desc-head_T1w.nii.gz",
                aseg="anat/" + self.subject + "_desc-aseg_dseg.nii.gz",
                aparc_aseg="anat/" + self.subject + "_desc-aparcaseg_dseg.nii.gz",
                brain="anat/" + self.subject + "_desc-brain_T1w.nii.gz",
                brain_mask="anat/" + self.subject + "_desc-brain_mask.nii.gz",
                wm_mask_file="anat/" + self.subject + "_label-WM_dseg.nii.gz",
                wm_eroded="anat/" + self.subject + "_label-WM_dseg.nii.gz",
                brain_eroded="anat/" + self.subject + "_desc-brain_mask.nii.gz",
                csf_eroded="anat/" + self.subject + "_label-CSF_dseg.nii.gz",
                roi_volume_s1="anat/" + self.subject + "_atlas-" + bids_atlas_label + "_dseg.nii.gz",
                roi_graphml_s1="anat/" + self.subject + "_atlas-" + bids_atlas_label + "_dseg.graphml",
                roi_volume_s2="anat/irrelevant.nii.gz",
                roi_graphml_s2="anat/irrelevant.graphml",
                roi_volume_s3="anat/irrelevant.nii.gz",
                roi_graphml_s3="anat/irrelevant.graphml",
                roi_volume_s4="anat/irrelevant.nii.gz",
                roi_graphml_s4="anat/irrelevant.graphml",
                roi_volume_s5="anat/irrelevant.nii.gz",
                roi_graphml_s5="anat/irrelevant.graphml",
            )
            # fmt:on
        elif self.parcellation_scheme == "Custom":
            # fmt:off
            field_template = dict(
                diffusion="dwi/" + self.subject + "_desc-cmp_dwi.nii.gz",
                bvecs="dwi/" + self.subject + "_desc-cmp_dwi.bvec",
                bvals="dwi/" + self.subject + "_desc-cmp_dwi.bval",
                T1="anat/" + self.subject + "_desc-head_T1w.nii.gz",
                aseg="anat/" + self.subject + "_desc-aseg_dseg.nii.gz",
                aparc_aseg="anat/" + self.subject + "_desc-aparcaseg_dseg.nii.gz",
                brain="anat/" + self.subject + "_desc-brain_T1w.nii.gz",
                brain_mask="anat/" + self.subject + "_desc-brain_mask.nii.gz",
                wm_mask_file="anat/" + self.subject + "_label-WM_dseg.nii.gz",
                wm_eroded="anat/" + self.subject + "_label-WM_dseg.nii.gz",
                brain_eroded="anat/" + self.subject + "_desc-brain_mask.nii.gz",
                csf_eroded="anat/" + self.subject + "_label-CSF_dseg.nii.gz",
                roi_volume_s1="anat/" + self.subject + "_atlas-" + bids_atlas_label + "_dseg.nii.gz",
                roi_graphml_s1="anat/" + self.subject + "_atlas-" + bids_atlas_label + "_dseg.graphml",
                roi_volume_s2="anat/irrelevant.nii.gz",
                roi_graphml_s2="anat/irrelevant.graphml",
                roi_volume_s3="anat/irrelevant.nii.gz",
                roi_graphml_s3="anat/irrelevant.graphml",
                roi_volume_s4="anat/irrelevant.nii.gz",
                roi_graphml_s4="anat/irrelevant.graphml",
                roi_volume_s5="anat/irrelevant.nii.gz",
                roi_graphml_s5="anat/irrelevant.graphml",
            )
            # fmt:on
        else:
            # fmt:off
            field_template = dict(
                diffusion="dwi/" + self.subject + "_desc-cmp_dwi.nii.gz",
                bvecs="dwi/" + self.subject + "_desc-cmp_dwi.bvec",
                bvals="dwi/" + self.subject + "_desc-cmp_dwi.bval",
                T1="anat/" + self.subject + "_desc-head_T1w.nii.gz",
                aseg="anat/" + self.subject + "_desc-aseg_dseg.nii.gz",
                aparc_aseg="anat/" + self.subject + "_desc-aparcaseg_dseg.nii.gz",
                brain="anat/" + self.subject + "_desc-brain_T1w.nii.gz",
                brain_mask="anat/" + self.subject + "_desc-brain_mask.nii.gz",
                wm_mask_file="anat/" + self.subject + "_label-WM_dseg.nii.gz",
                wm_eroded="anat/" + self.subject + "_label-WM_dseg.nii.gz",
                brain_eroded="anat/" + self.subject + "_desc-brain_mask.nii.gz",
                csf_eroded="anat/" + self.subject + "_label-CSF_dseg.nii.gz",
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
        print(f' .. DEBUG : Field template : {field_template}')
        return field_template

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
                    "diffusion",
                    "bvecs",
                    "bvals",
                    "T1",
                    "aparc_aseg",
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
            name="dwi_datasource",
        )
        datasource.inputs.base_directory = base_directory
        datasource.inputs.template = "*"
        datasource.inputs.raise_on_empty = False
        datasource.inputs.field_template = self.create_field_template_dict(bids_atlas_label=bids_atlas_label)
        datasource.inputs.sort_filelist = True

        return datasource

    def create_datasinker_node(self, base_directory, bids_atlas_label, recon_model, tracking_model):
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
        sinker = pe.Node(nio.DataSink(), name="dwi_datasinker")
        sinker.inputs.base_directory = os.path.abspath(base_directory)

        # Dataname substitutions in order to comply with BIDS derivatives specifications
        # fmt:off
        sinker.inputs.substitutions = [  # ('T1', self.subject+'_T1w_head'),
            ("brain_mask.nii.gz", self.subject + "_desc-brain_mask.nii.gz"),
            ("brain.nii.gz", self.subject + "_desc-brain_T1w.nii.gz"),
            ("T1_warped", self.subject + "_space-DWI_desc-head_T1w"),
            ("T1-TO-TARGET", self.subject + "_space-DWI_desc-head_T1w"),
            ("anat_resampled_warped", self.subject + "_space-DWI_desc-head_T1w"),
            ("brain_warped", self.subject + "_space-DWI_desc-brain_T1w"),
            ("anat_masked_resampled_warped", self.subject + "_space-DWI_desc-brain_T1w"),
            ("brain_mask_registered_temp_crop", self.subject + "_space-DWI_desc-brain_mask"),
            ("brain_mask_resampled_warped.nii.gz", self.subject + "_space-DWI_desc-brain_mask"),
            ("wm_mask_warped", self.subject + "_space-DWI_label-WM_dseg"),
            ("wm_mask_registered", self.subject + "_space-DWI_label-WM_dseg"),
            ("wm_mask_resampled_warped", self.subject + "_space-DWI_label-WM_dseg"),
            (
                f'{self.subject}_atlas-Desikan_dseg_out_warped.nii.gz',
                f'{self.subject}_space-DWI_atlas-Desikan_dseg.nii.gz'
            ),
            ("fast__pve_0_out_warped.nii.gz", self.subject + "_space-DWI_label-CSF_probseg.nii.gz"),
            ("fast__pve_1_out_warped.nii.gz", self.subject + "_space-DWI_label-GM_probseg.nii.gz"),
            ("fast__pve_2_out_warped.nii.gz", self.subject + "_space-DWI_label-WM_probseg.nii.gz"),
            ("pve_0_out_warped.nii.gz", self.subject + "_space-DWI_label-CSF_probseg.nii.gz"),
            ("pve_1_out_warped.nii.gz", self.subject + "_space-DWI_label-GM_probseg.nii.gz"),
            ("pve_2_out_warped.nii.gz", self.subject + "_space-DWI_label-WM_probseg.nii.gz"),
            ("act_5tt_resampled_warped.nii.gz", self.subject + "_space-DWI_label-5TT_probseg.nii.gz"),
            ("gmwmi_resampled_warped.nii.gz", self.subject + "_space-DWI_label-GMWMI_probseg.nii.gz"),
            ("5tt_warped.nii.gz", self.subject + "_space-DWI_label-5TT_probseg.nii.gz"),
            ("gmwmi_warped.nii.gz", self.subject + "_space-DWI_label-GMWMI_probseg.nii.gz"),
            ("connectome_freesurferaparc", self.subject + "_label-Desikan_conndata-network_connectivity"),
            ("dwi.nii.gz", self.subject + "_dwi.nii.gz"),
            ("dwi.bval", self.subject + "_dwi.bval"),
            ("eddy_corrected.nii.gz.eddy_rotated_bvecs", self.subject + "_desc-eddyrotated.bvec"),
            ("eddy_corrected.nii.gz", self.subject + "_desc-eddycorrected_dwi.nii.gz"),
            ("dwi_brain_mask_resampled.nii.gz", self.subject + "_desc-brain_mask.nii.gz"),
            ("brain_mask_resampled.nii.gz", self.subject + "_desc-brain_mask.nii.gz"),
            ("ADC", self.subject + "_model-DTI_MD"),
            ("FA", self.subject + "_model-DTI_FA"),
            ("diffusion_preproc_resampled_fa", self.subject + "_model-DTI_FA"),
            ("diffusion_preproc_resampled_ad", self.subject + "_model-DTI_AD"),
            ("diffusion_preproc_resampled_md", self.subject + "_model-DTI_MD"),
            ("diffusion_preproc_resampled_rd", self.subject + "_model-DTI_RD"),
            ("shore_gfa.nii.gz", "{}_model-SHORE_GFA.nii.gz".format(self.subject)),
            ("shore_msd.nii.gz", "{}_model-SHORE_MSD.nii.gz".format(self.subject)),
            ("shore_rtop_signal.nii.gz", "{}_model-SHORE_RTOP.nii.gz".format(self.subject),),
            ("shore_fodf.nii.gz", "{}_model-SHORE_FOD.nii.gz".format(self.subject)),
            ("diffusion_resampled_CSD.mif", self.subject + "_model-CSD_diffmodel.mif",),
            ("diffusion_shm_coeff.nii.gz", "{}_model-CSD_diffmodel.nii.gz".format(self.subject),),
            ("spherical_harmonics_image.nii.gz", "{}_model-CSD_diffmodel.nii.gz".format(self.subject),),
            ("shm_coeff.nii.gz", "{}_model-CSD_diffmodel.nii.gz".format(self.subject),),
            ("dwi_tensor.nii.gz", "{}_desc-WLS_model-DTI_diffmodel.nii.gz".format(self.subject),),
            ("grad.txt", self.subject + "_desc-grad_dwi.txt"),
            ("target_epicorrected", self.subject + "_desc-preproc_dwi"),
            ("diffusion_preproc_resampled.nii.gz", self.subject + "_desc-preproc_dwi.nii.gz",),
            ("streamline_final", "{}_model-{}_desc-{}_tractogram".format(self.subject, recon_model, tracking_model),)
        ]
        # fmt:on

        if self.parcellation_scheme != "Custom":
            for scale in ['scale1', 'scale2', 'scale3', 'scale4', 'scale5']:
                # fmt:off
                sinker.inputs.substitutions += [
                    (
                        f'ROIv_HR_th_{scale}_out_warped.nii.gz',
                        f'{self.subject}_space-DWI_atlas-{bids_atlas_label}_res-{scale}_dseg.nii.gz'
                    ),
                    (
                        f'{self.subject}_atlas-{bids_atlas_label}_res-{scale}_dseg_out_warped.nii.gz',
                        f'{self.subject}_space-DWI_atlas-{bids_atlas_label}_res-{scale}_dseg.nii.gz'
                    ),
                    (
                        f'{self.subject}_atlas-{bids_atlas_label}_res-{scale}_dseg_out_flirt.nii.gz',
                        f'{self.subject}_space-DWI_atlas-{bids_atlas_label}_res-{scale}_dseg.nii.gz'
                    ),
                    (
                        f'connectome_{scale}',
                        f'{self.subject}_atlas-{bids_atlas_label}_res-{scale}_conndata-network_connectivity'),
                ]
                # fmt:on
        else:
            # fmt:off
            bids_atlas_name = bids_atlas_label if "res" not in bids_atlas_label else bids_atlas_label.split('_')[0]
            sinker.inputs.substitutions += [
                (
                    f'{self.subject}_atlas-{bids_atlas_label}_dseg_out_warped.nii.gz',
                    f'{self.subject}_space-DWI_atlas-{bids_atlas_label}_dseg.nii.gz'
                ),
                (
                    f'{self.subject}_atlas-{bids_atlas_label}_dseg_out_flirt.nii.gz',
                    f'{self.subject}_space-DWI_atlas-{bids_atlas_label}_dseg.nii.gz'
                ),
                (
                    f'connectome_{bids_atlas_name}',
                    f'{self.subject}_atlas-{bids_atlas_label}_conndata-network_connectivity'),
            ]
            # fmt:on

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
        diffusion_flow : nipype.pipeline.engine.Workflow
            An instance of :class:`nipype.pipeline.engine.Workflow`
        """
        acquisition_model = self.stages["Diffusion"].config.diffusion_imaging_model
        recon_tool = self.stages["Diffusion"].config.recon_processing_tool

        recon_model = "DTI"

        if acquisition_model == "DSI":
            recon_model = "SHORE"
        else:
            if recon_tool == "Dipy" and self.stages["Diffusion"].config.dipy_recon_config.local_model:
                recon_model = "CSD"
            elif recon_tool == "MRtrix" and self.stages["Diffusion"].config.mrtrix_recon_config.local_model:
                recon_model = "CSD"

        tracking_model = self.stages["Diffusion"].config.diffusion_model

        if tracking_model == "Deterministic":
            tracking_model = "DET"
        elif tracking_model == "Probabilistic":
            tracking_model = "PROB"

        if self.parcellation_scheme == "Lausanne2018":
            bids_atlas_label = "L2018"
        elif self.parcellation_scheme == "NativeFreesurfer":
            bids_atlas_label = "Desikan"
        elif self.parcellation_scheme == "Custom":
            bids_atlas_label = self.custom_atlas_name
            if self.custom_atlas_res is not None and self.custom_atlas_res != "":
                bids_atlas_label += f'_res-{self.custom_atlas_res}'

        # Clear previous outputs
        self.clear_stages_outputs()

        # Create diffusion workflow with input and output Identityinterface nodes
        diffusion_flow = pe.Workflow(
            name="diffusion_pipeline",
            base_dir=os.path.abspath(nipype_deriv_subject_directory),
        )

        diffusion_inputnode = pe.Node(
            interface=util.IdentityInterface(
                fields=[
                    "diffusion",
                    "bvecs",
                    "bvals",
                    "T1",
                    "aseg",
                    "aparc_aseg",
                    "brain",
                    "T2",
                    "brain_mask",
                    "wm_mask_file",
                    "roi_volumes",
                    "roi_graphMLs",
                    "subjects_dir",
                    "subject_id",
                    "parcellation_scheme",
                ]
            ),
            name="inputnode",
        )
        diffusion_inputnode.inputs.parcellation_scheme = self.parcellation_scheme
        diffusion_inputnode.inputs.atlas_info = self.atlas_info

        diffusion_outputnode = pe.Node(
            interface=util.IdentityInterface(fields=["connectivity_matrices"]),
            name="outputnode",
        )

        diffusion_flow.add_nodes([diffusion_inputnode, diffusion_outputnode])

        # Data import
        datasource = self.create_datagrabber_node(
            base_directory=cmp_deriv_subject_directory,
            bids_atlas_label=bids_atlas_label
        )

        # Data sinker for output
        sinker = self.create_datasinker_node(
            base_directory=cmp_deriv_subject_directory,
            bids_atlas_label=bids_atlas_label,
            recon_model=recon_model,
            tracking_model=tracking_model
        )

        # fmt:off
        diffusion_flow.connect(
            [
                (datasource, diffusion_inputnode, [("diffusion", "diffusion"),
                                                   ("bvecs", "bvecs"),
                                                   ("bvals", "bvals"),
                                                   ("T1", "T1"),
                                                   ("aseg", "aseg"),
                                                   ("aparc_aseg", "aparc_aseg"),
                                                   ("brain", "brain"),
                                                   ("brain_mask", "brain_mask"),
                                                   ("wm_mask_file", "wm_mask_file")]),
            ]
        )
        # fmt:on

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
        diffusion_flow.connect(
            [
                (datasource, merge_roi_volumes, [("roi_volume_s1", "in1"),
                                                 ("roi_volume_s2", "in2"),
                                                 ("roi_volume_s3", "in3"),
                                                 ("roi_volume_s4", "in4"),
                                                 ("roi_volume_s5", "in5")]),
                (datasource, merge_roi_graphmls, [("roi_graphml_s1", "in1"),
                                                  ("roi_graphml_s2", "in2"),
                                                  ("roi_graphml_s3", "in3"),
                                                  ("roi_graphml_s4", "in4"),
                                                  ("roi_graphml_s5", "in5")]),
                (merge_roi_volumes, diffusion_inputnode, [(("out", remove_non_existing_scales), "roi_volumes")],),
                (merge_roi_graphmls, diffusion_inputnode, [(("out", remove_non_existing_scales), "roi_graphMLs")],),
            ]
        )
        # fmt:on

        if self.stages["Preprocessing"].enabled:
            preproc_flow = self.create_stage_flow("Preprocessing")
            # fmt:off
            diffusion_flow.connect(
                [
                    (diffusion_inputnode, preproc_flow, [("diffusion", "inputnode.diffusion"),
                                                         ("brain", "inputnode.brain"),
                                                         ("aseg", "inputnode.aseg"),
                                                         ("aparc_aseg", "inputnode.aparc_aseg"),
                                                         ("brain_mask", "inputnode.brain_mask"),
                                                         ("wm_mask_file", "inputnode.wm_mask_file"),
                                                         ("roi_volumes", "inputnode.roi_volumes"),
                                                         ("bvecs", "inputnode.bvecs"),
                                                         ("bvals", "inputnode.bvals"),
                                                         ("T1", "inputnode.T1")]),
                ]
            )
            # fmt:on

        if self.stages["Registration"].enabled:
            reg_flow = self.create_stage_flow("Registration")
            # fmt:off
            diffusion_flow.connect(
                [
                    # (diffusion_inputnode,reg_flow,[('T2','inputnode.T2')]),
                    (preproc_flow, reg_flow, [("outputnode.T1", "inputnode.T1"),
                                              ("outputnode.act_5TT", "inputnode.act_5TT"),
                                              ("outputnode.gmwmi", "inputnode.gmwmi"),
                                              ("outputnode.bvecs_rot", "inputnode.bvecs"),
                                              ("outputnode.bvals", "inputnode.bvals"),
                                              ("outputnode.wm_mask_file", "inputnode.wm_mask"),
                                              ("outputnode.partial_volume_files", "inputnode.partial_volume_files",),
                                              ("outputnode.roi_volumes", "inputnode.roi_volumes"),
                                              ("outputnode.brain", "inputnode.brain"),
                                              ("outputnode.brain_mask", "inputnode.brain_mask"),
                                              ("outputnode.brain_mask_full", "inputnode.brain_mask_full"),
                                              ("outputnode.diffusion_preproc", "inputnode.target"),
                                              ("outputnode.dwi_brain_mask", "inputnode.target_mask")]),
                    (preproc_flow, sinker, [("outputnode.bvecs_rot", "dwi.@bvecs_rot"),
                                            ("outputnode.diffusion_preproc", "dwi.@diffusion_preproc"),
                                            ("outputnode.dwi_brain_mask", "dwi.@diffusion_brainmask")]),
                ]
            )
            # fmt:on
            if self.stages["Registration"].config.registration_mode == "BBregister (FS)":
                # fmt:off
                diffusion_flow.connect(
                    [
                        (diffusion_inputnode, reg_flow, [("subjects_dir", "inputnode.subjects_dir"), ("subject_id", "inputnode.subject_id")]),
                    ]
                )
                # fmt:on

        if self.stages["Diffusion"].enabled:
            diff_flow = self.create_stage_flow("Diffusion")
            # fmt:off
            diffusion_flow.connect(
                [
                    (preproc_flow, diff_flow, [("outputnode.diffusion_preproc", "inputnode.diffusion")]),
                    (reg_flow, diff_flow, [("outputnode.wm_mask_registered_crop", "inputnode.wm_mask_registered",),
                                           ("outputnode.brain_mask_registered_crop", "inputnode.brain_mask_registered",),
                                           ("outputnode.partial_volumes_registered_crop", "inputnode.partial_volumes",),
                                           ("outputnode.roi_volumes_registered_crop", "inputnode.roi_volumes",),
                                           ("outputnode.act_5tt_registered_crop", "inputnode.act_5tt_registered",),
                                           ("outputnode.gmwmi_registered_crop", "inputnode.gmwmi_registered",),
                                           ("outputnode.grad", "inputnode.grad"),
                                           ("outputnode.bvals", "inputnode.bvals"),
                                           ("outputnode.bvecs", "inputnode.bvecs")]),
                    (reg_flow, sinker, [("outputnode.target_epicorrected", "dwi.@bdiffusion_reg_crop",),
                                        ("outputnode.grad", "dwi.@diffusion_grad"),
                                        ("outputnode.affine_transform", "xfm.@affine_transform"),
                                        ("outputnode.warp_field", "xfm.@warp_field"),
                                        ("outputnode.T1_registered_crop", "anat.@T1_reg_crop"),
                                        ("outputnode.act_5tt_registered_crop", "anat.@act_5tt_reg_crop",),
                                        ("outputnode.gmwmi_registered_crop", "anat.@gmwmi_reg_crop"),
                                        ("outputnode.brain_registered_crop", "anat.@brain_reg_crop"),
                                        ("outputnode.brain_mask_registered_crop", "anat.@brain_mask_reg_crop",),
                                        ("outputnode.wm_mask_registered_crop", "anat.@wm_mask_reg_crop",),
                                        ("outputnode.roi_volumes_registered_crop", "anat.@roivs_reg_crop",),
                                        ("outputnode.partial_volumes_registered_crop", "anat.@pves_reg_crop",)],),
                ]
            )
            # fmt:on

        if self.stages["Connectome"].enabled:
            self.stages["Connectome"].config.probtrackx = False
            self.stages["Connectome"].config.subject = self.global_conf.subject
            con_flow = self.create_stage_flow("Connectome")
            # fmt:off
            diffusion_flow.connect(
                [
                    (diffusion_inputnode, con_flow, [("parcellation_scheme", "inputnode.parcellation_scheme"),
                                                     ("atlas_info", "inputnode.atlas_info"),
                                                     ("roi_graphMLs", "inputnode.roi_graphMLs")]),
                    (diff_flow, con_flow, [("outputnode.track_file", "inputnode.track_file"),
                                           ("outputnode.FA", "inputnode.FA"),
                                           ("outputnode.ADC", "inputnode.ADC"),
                                           ("outputnode.AD", "inputnode.AD"),
                                           ("outputnode.RD", "inputnode.RD"),
                                           ("outputnode.roi_volumes", "inputnode.roi_volumes_registered",),
                                           ("outputnode.skewness", "inputnode.skewness"),
                                           ("outputnode.kurtosis", "inputnode.kurtosis"),
                                           ("outputnode.P0", "inputnode.P0"),
                                           ("outputnode.mapmri_maps", "inputnode.mapmri_maps"),
                                           ("outputnode.shore_maps", "inputnode.shore_maps")]),
                    (con_flow, diffusion_outputnode, [("outputnode.connectivity_matrices", "connectivity_matrices")]),
                    (diff_flow, sinker, [("outputnode.fod_file", "dwi.@fod_file"),
                                         ("outputnode.FA", "dwi.@FA"),
                                         ("outputnode.ADC", "dwi.@ADC"),
                                         ("outputnode.AD", "dwi.@AD"),
                                         ("outputnode.RD", "dwi.@RD"),
                                         ("outputnode.skewness", "dwi.@skewness"),
                                         ("outputnode.kurtosis", "dwi.@kurtosis"),
                                         ("outputnode.P0", "dwi.@P0"),
                                         ("outputnode.mapmri_maps", "dwi.@mapmri_maps"),
                                         ("outputnode.shore_maps", "dwi.@shore_maps")]),
                    (con_flow, sinker, [("outputnode.streamline_final_file", "dwi.@streamline_final_file"),
                                        ("outputnode.connectivity_matrices", "dwi.@connectivity_matrices")]),
                ]
            )
        # fmt:on

        return diffusion_flow

    def process(self):
        """Executes the diffusion pipeline workflow and returns True if successful."""
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
            os.path.join(nipype_deriv_subject_directory, "diffusion_pipeline")
        ):
            try:
                os.makedirs(
                    os.path.join(nipype_deriv_subject_directory, "diffusion_pipeline")
                )
            except os.error:
                print(
                    "%s was already existing"
                    % os.path.join(nipype_deriv_subject_directory, "diffusion_pipeline")
                )

        # Initialization
        log_file = os.path.join(nipype_deriv_subject_directory, "diffusion_pipeline", "pypeline.log")

        if os.path.isfile(log_file):
            os.unlink(log_file)

        config.update_config(
            {
                "logging": {
                    "workflow_level": "DEBUG",
                    "interface_level": "DEBUG",
                    "log_directory": os.path.join(
                        nipype_deriv_subject_directory, "diffusion_pipeline"
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

        flow = self.create_pipeline_flow(
            cmp_deriv_subject_directory=cmp_deriv_subject_directory,
            nipype_deriv_subject_directory=nipype_deriv_subject_directory,
        )
        flow.write_graph(graph2use="colored", format="svg", simple_form=True)

        if self.number_of_cores != 1:
            flow.run(plugin="MultiProc", plugin_args={"n_procs": self.number_of_cores})
        else:
            flow.run()

        iflogger.info("**** Processing finished ****")

        return True
