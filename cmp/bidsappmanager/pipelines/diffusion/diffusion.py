# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""Diffusion pipeline UI Class definition."""

import os
import shutil

from traitsui.api import *
from traits.api import *
from traitsui.qt4.extra.qt_view import QtView
from pyface.api import ImageResource

from bids import BIDSLayout

# Own imports
from cmtklib.bids.io import __cmp_directory__, __nipype_directory__
from cmtklib.util import return_button_style_sheet
from cmp.bidsappmanager.stages.preprocessing.preprocessing import PreprocessingStageUI
from cmp.bidsappmanager.stages.diffusion.diffusion import DiffusionStageUI
from cmp.bidsappmanager.stages.registration.registration import RegistrationStageUI
from cmp.bidsappmanager.stages.connectome.connectome import ConnectomeStageUI
from cmp.pipelines.diffusion.diffusion import DiffusionPipeline


class DiffusionPipelineUI(DiffusionPipeline):
    """Class that extends the :class:`~cmp.pipelines.diffusion.diffusion.DiffusionPipeline` with graphical components.

    Attributes
    ----------
    preprocessing : traits.ui.Button
        Button to open the window for configuration or quality inspection
        of the preprocessing stage depending on the ``view_mode``

    registration : traits.ui.Button
        Button to open the window for configuration or quality inspection
        of the registration stage depending on the ``view_mode``

    diffusion : traits.ui.Button
        Button to open the window for configuration or quality inspection
        of the diffusion reconstruction and tractography stage depending
        on the ``view_mode``

    connectome : traits.ui.Button
        Button to open the window for configuration or quality inspection
        of the connectome stage depending on the ``view_mode``

    view_mode : ['config_view', 'inspect_outputs_view']
        Variable used to control the display of either (1) the configuration
        or (2) the quality inspection of stage of the pipeline

    pipeline_group : traitsUI panel
        Panel defining the layout of the buttons of the stages with corresponding images

    traits_view : QtView
        QtView that includes the ``pipeline_group`` panel

    See also
    ---------
    cmp.pipelines.diffusion.diffusion.DiffusionPipeline
    """

    view_mode = Enum("config_view", ["config_view", "inspect_outputs_view"])

    preprocessing = Button("Preprocessing")
    # preprocessing.setIcon(QIcon(QPixmap("preprocessing.png")))

    diffusion = Button("Diffusion")
    # diffusion.setIcon(QIcon(QPixmap("diffusion.png")))

    registration = Button("Registration")
    # registration.setIcon(QIcon(QPixmap("registration.png")))

    connectome = Button("Connectome")
    # connectome.setIcon(QIcon(QPixmap("connectome.png")))

    pipeline_group = VGroup(
        HGroup(
            spring,
            UItem(
                "preprocessing",
                style="custom",
                width=222,
                height=129,
                resizable=False,
                style_sheet=return_button_style_sheet(
                    ImageResource("preprocessing").absolute_path
                ),
            ),
            spring,
            show_labels=False,
            label="",
            padding=0,
        ),
        HGroup(
            spring,
            UItem(
                "registration",
                style="custom",
                width=222,
                height=129,
                resizable=False,
                style_sheet=return_button_style_sheet(
                    ImageResource("registration").absolute_path
                ),
            ),
            spring,
            show_labels=False,
            label="",
            padding=0,
        ),
        HGroup(
            spring,
            UItem(
                "diffusion",
                style="custom",
                width=222,
                height=244,
                resizable=False,
                style_sheet=return_button_style_sheet(
                    ImageResource("diffusion").absolute_path
                ),
            ),
            spring,
            show_labels=False,
            label="",
            padding=0,
        ),
        HGroup(
            spring,
            UItem(
                "connectome",
                style="custom",
                width=222,
                height=129,
                resizable=False,
                style_sheet=return_button_style_sheet(
                    ImageResource("connectome").absolute_path
                ),
            ),
            spring,
            show_labels=False,
            label="",
            padding=0,
        ),
        padding=0,
        # layout='split',
        # springy=True
    )

    traits_view = QtView(Include("pipeline_group"))

    def __init__(self, project_info):
        """Constructor of the DiffusionPipelineUI class.

        Parameters
        -----------
        project_info : cmp.project.ProjectInfo
            CMP_Project_Info object that stores general information
            such as the BIDS root and output directories (see
            :class_`cmp.project.CMP_Project_Info` for more details)

        See Also
        ---------
        cmp.pipelines.diffusion.DiffusionPipeline.__init__
        """
        DiffusionPipeline.__init__(self, project_info)

        self.stages = {
            "Preprocessing": PreprocessingStageUI(
                bids_dir=project_info.base_directory,
                output_dir=project_info.output_directory,
            ),
            "Registration": RegistrationStageUI(
                pipeline_mode="Diffusion",
                fs_subjects_dir=project_info.freesurfer_subjects_dir,
                fs_subject_id=os.path.basename(project_info.freesurfer_subject_id),
                bids_dir=project_info.base_directory,
                output_dir=self.output_directory,
            ),
            "Diffusion": DiffusionStageUI(
                bids_dir=project_info.base_directory,
                output_dir=project_info.output_directory,
            ),
            "Connectome": ConnectomeStageUI(
                bids_dir=project_info.base_directory,
                output_dir=project_info.output_directory,
            ),
        }

        for stage in list(self.stages.keys()):
            if project_info.subject_session != "":
                self.stages[stage].stage_dir = os.path.join(
                    self.base_directory,
                    "derivatives",
                    __nipype_directory__,
                    self.subject,
                    project_info.subject_session,
                    self.pipeline_name,
                    self.stages[stage].name,
                )
            else:
                self.stages[stage].stage_dir = os.path.join(
                    self.base_directory,
                    "derivatives",
                    __nipype_directory__,
                    self.subject,
                    self.pipeline_name,
                    self.stages[stage].name,
                )

    def _preprocessing_fired(self, info):
        """Method that displays the window for the preprocessing stage.

        The window changed accordingly to the value of ``view_mode`` to be
        in configuration or quality inspection mode.

        Parameters
        -----------
        info : traits.ui.Button
            The preprocessing button object
        """
        self.stages["Preprocessing"].configure_traits(view=self.view_mode)

    def _diffusion_fired(self, info):
        """Method that displays the window for the diffusion stage.

        The window changed accordingly to the value of ``view_mode`` to be
        in configuration or quality inspection mode.

        Parameters
        -----------
        info : traits.ui.Button
            The diffusion button object
        """
        self.stages["Diffusion"].configure_traits(view=self.view_mode)

    def _registration_fired(self, info):
        """Method that displays the window for the registration stage.

        The window changed accordingly to the value of ``view_mode`` to be
        in configuration or quality inspection mode.

        Parameters
        -----------
        info : traits.ui.Button
            The registration button object
        """
        self.stages["Registration"].configure_traits(view=self.view_mode)

    def _connectome_fired(self, info):
        """Method that displays the window for the connectome stage.

        The window changed accordingly to the value of ``view_mode`` to be
        in configuration or quality inspection mode.

        Parameters
        -----------
        info : traits.ui.Button
            The connectome button object
        """
        self.stages["Connectome"].configure_traits(view=self.view_mode)

    def check_input(self, layout, gui=True):
        """Method that checks if inputs of the diffusion pipeline are available in the datasets.

        Parameters
        -----------
        layout : bids.BIDSLayout
            BIDSLayout object used to query

        gui : bool
            If True, display message in GUI

        Returns
        -------
        valid_inputs : bool
            True in all inputs of the anatomical pipeline are available
        """
        print("**** Check Inputs  ****")
        diffusion_available = False
        bvecs_available = False
        bvals_available = False
        valid_inputs = False

        if self.global_conf.subject_session == "":
            subject = self.subject
        else:
            subject = "_".join((self.subject, self.global_conf.subject_session))

        dwi_file = os.path.join(self.subject_directory, "dwi", subject + "_dwi.nii.gz")
        bval_file = os.path.join(self.subject_directory, "dwi", subject + "_dwi.bval")
        bvec_file = os.path.join(self.subject_directory, "dwi", subject + "_dwi.bvec")

        subjid = self.subject.split("-")[1]

        try:
            layout = BIDSLayout(self.base_directory)
            print("Valid BIDS dataset with %s subjects" % len(layout.get_subjects()))
            for subj in layout.get_subjects():
                self.global_conf.subjects.append("sub-" + str(subj))
            # self.global_conf.subjects = ['sub-'+str(subj) for subj in layout.get_subjects()]
            # self.global_conf.modalities = [
            #     str(mod) for mod in layout.get_modalities()]
            # mods = layout.get_modalities()
            types = layout.get_modalities()
            # print "Available modalities :"
            # for mod in mods:
            #     print "-%s" % mod

            if self.global_conf.subject_session == "":

                files = layout.get(subject=subjid, suffix="dwi", extensions=".nii.gz")
                if len(files) > 0:
                    dwi_file = os.path.join(files[0].dirname, files[0].filename)
                    print(dwi_file)
                else:
                    error(
                        message="Diffusion image not found for subject %s." % subjid,
                        title="Error",
                        buttons=["OK", "Cancel"],
                        parent=None,
                    )
                    return

                files = layout.get(subject=subjid, suffix="dwi", extensions=".bval")
                if len(files) > 0:
                    bval_file = os.path.join(files[0].dirname, files[0].filename)
                    print(bval_file)
                else:
                    error(
                        message="Diffusion bval image not found for subject %s."
                        % subjid,
                        title="Error",
                        buttons=["OK", "Cancel"],
                        parent=None,
                    )
                    return

                files = layout.get(subject=subjid, suffix="dwi", extensions=".bvec")
                if len(files) > 0:
                    bvec_file = os.path.join(files[0].dirname, files[0].filename)
                    print(bvec_file)
                else:
                    error(
                        message="Diffusion bvec image not found for subject %s."
                        % subjid,
                        title="Error",
                        buttons=["OK", "Cancel"],
                        parent=None,
                    )
                    return
            else:
                sessid = self.global_conf.subject_session.split("-")[1]

                files = layout.get(
                    subject=subjid, suffix="dwi", extensions=".nii.gz", session=sessid
                )
                if len(files) > 0:
                    dwi_file = os.path.join(files[0].dirname, files[0].filename)
                    print(dwi_file)
                else:
                    error(
                        message="Diffusion image not found for subject %s, session %s."
                        % (subjid, self.global_conf.subject_session),
                        title="Error",
                        buttons=["OK", "Cancel"],
                        parent=None,
                    )
                    return

                files = layout.get(
                    subject=subjid, suffix="dwi", extensions=".bval", session=sessid
                )
                if len(files) > 0:
                    bval_file = os.path.join(files[0].dirname, files[0].filename)
                    print(bval_file)
                else:
                    error(
                        message="Diffusion bval image not found for subject %s, session %s."
                        % (subjid, self.global_conf.subject_session),
                        title="Error",
                        buttons=["OK", "Cancel"],
                        parent=None,
                    )
                    return

                files = layout.get(
                    subject=subjid, suffix="dwi", extensions=".bvec", session=sessid
                )
                if len(files) > 0:
                    bvec_file = os.path.join(files[0].dirname, files[0].filename)
                    print(bvec_file)
                else:
                    error(
                        message="Diffusion bvec image not found for subject %s, session %s."
                        % (subjid, self.global_conf.subject_session),
                        title="Error",
                        buttons=["OK", "Cancel"],
                        parent=None,
                    )
                    return

            print("Looking for....")
            print("dwi_file : %s" % dwi_file)
            print("bvecs_file : %s" % bvec_file)
            print("bvals_file : %s" % bval_file)

            if os.path.isfile(dwi_file):
                print("DWI available")
                diffusion_available = True

        except Exception:
            error(
                message="Invalid BIDS dataset. Please see documentation for more details.",
                title="Error",
                buttons=["OK", "Cancel"],
                parent=None,
            )
            return

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
                        self.derivatives_directory,
                        __cmp_directory__,
                        self.subject,
                        "dwi",
                        subject + "_dwi.nii.gz",
                    )
                    out_bval_file = os.path.join(
                        self.derivatives_directory,
                        __cmp_directory__,
                        self.subject,
                        "dwi",
                        subject + "_dwi.bval",
                    )
                    out_bvec_file = os.path.join(
                        self.derivatives_directory,
                        __cmp_directory__,
                        self.subject,
                        "dwi",
                        subject + "_dwi.bvec",
                    )
                else:
                    out_dwi_file = os.path.join(
                        self.derivatives_directory,
                        __cmp_directory__,
                        self.subject,
                        self.global_conf.subject_session,
                        "dwi",
                        subject + "_dwi.nii.gz",
                    )
                    out_bval_file = os.path.join(
                        self.derivatives_directory,
                        __cmp_directory__,
                        self.subject,
                        self.global_conf.subject_session,
                        "dwi",
                        subject + "_dwi.bval",
                    )
                    out_bvec_file = os.path.join(
                        self.derivatives_directory,
                        __cmp_directory__,
                        self.subject,
                        self.global_conf.subject_session,
                        "dwi",
                        subject + "_dwi.bvec",
                    )

                if not os.path.isfile(out_dwi_file):
                    shutil.copy(src=dwi_file, dst=out_dwi_file)
                if not os.path.isfile(out_bvec_file):
                    shutil.copy(src=bvec_file, dst=out_bvec_file)
                if not os.path.isfile(out_bval_file):
                    shutil.copy(src=bval_file, dst=out_bval_file)

                valid_inputs = True
                input_message = "Inputs check finished successfully.\nDiffusion and morphological data available."
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
            # input_notification = Check_Input_Notification(message=input_message,
            #                                               diffusion_imaging_model_options=diffusion_imaging_model,
            #                                               diffusion_imaging_model=diffusion_imaging_model)
            # input_notification.configure_traits()
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
            print("Missing required inputs.")
            error(
                message="Missing diffusion inputs. Please see documentation for more details.",
                title="Error",
                buttons=["OK", "Cancel"],
                parent=None,
            )

        # for stage in self.stages.values():
        #     if stage.enabled:
        #         print stage.name
        #         print stage.stage_dir

        # self.fill_stages_outputs()

        return valid_inputs
