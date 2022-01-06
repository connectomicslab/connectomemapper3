# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license ModifFied BSD.

"""Definition of config and stage classes for the extra functional preprocessing stage."""

# General imports
import os

from traits.api import *


# Nipype imports
import nipype.pipeline.engine as pe
from nipype.interfaces.base import isdefined
import nipype.interfaces.utility as util
from nipype.interfaces import afni

# Own imports
from cmp.stages.common import Stage
from cmtklib.functionalMRI import Scrubbing, Detrending, NuisanceRegression


class FunctionalMRIConfig(HasTraits):
    """Class used to store configuration parameters of a :class:`~cmp.stages.functional.functional.FunctionalMRIStage` object.

    Attributes
    ----------
    global_nuisance : traits.Bool
        Perform global nuisance regression
        (Default: False)

    csf : traits.Bool
        Perform CSF nuisance regression
        (Default: True)

    wm : traits.Bool
        Perform White-Matter nuisance regression
        (Default: True)

    motion : traits.Bool
        Perform motion nuisance regression
        (Default: True)

    detrending = Bool
        Perform detrending
        (Default: True)

    detrending_mode = Enum("linear", "quadratic")
        Detrending mode
        (Default: "Linear")

    lowpass_filter = Float
        Lowpass filter frequency
        (Default: 0.01)

    highpass_filter = Float
        Highpass filter frequency
        (Default: 0.1)

    scrubbing = Bool
        Perform scrubbing
        (Default: True)

    See Also
    --------
    cmp.stages.functional.functionalMRI.FunctionalMRIStage
    """

    smoothing = Float(0.0)
    discard_n_volumes = Int(5)
    # Nuisance factors
    global_nuisance = Bool(False)
    csf = Bool(True)
    wm = Bool(True)
    motion = Bool(True)

    detrending = Bool(True)
    detrending_mode = Enum("linear", "quadratic")

    lowpass_filter = Float(0.01)
    highpass_filter = Float(0.1)

    scrubbing = Bool(True)


class FunctionalMRIStage(Stage):
    """Class that represents the post-registration preprocessing stage of the `fMRIPipeline`.

    Methods
    -------
    create_workflow()
        Create the workflow of the `FunctionalMRIStage`

    See Also
    --------
    cmp.pipelines.functional.fMRI.fMRIPipeline
    cmp.stages.functional.functionalMRI.FunctionalMRIConfig
    """

    def __init__(self, bids_dir, output_dir):
        """Constructor of a :class:`~cmp.stages.functional.functionalMRI.FunctionalMRIStage` instance."""
        self.name = "functional_stage"
        self.bids_dir = bids_dir
        self.output_dir = output_dir

        self.config = FunctionalMRIConfig()
        self.inputs = [
            "preproc_file",
            "motion_par_file",
            "registered_roi_volumes",
            "registered_wm",
            "eroded_wm",
            "eroded_csf",
            "eroded_brain",
        ]
        self.outputs = ["func_file", "FD", "DVARS"]

    def create_workflow(self, flow, inputnode, outputnode):
        """Create the stage worflow.

        Parameters
        ----------
        flow : nipype.pipeline.engine.Workflow
            The nipype.pipeline.engine.Workflow instance of the fMRI pipeline

        inputnode : nipype.interfaces.utility.IdentityInterface
            Identity interface describing the inputs of the stage

        outputnode : nipype.interfaces.utility.IdentityInterface
            Identity interface describing the outputs of the stage
        """
        if self.config.scrubbing and isdefined(inputnode.inputs.motion_par_file):
            scrubbing = pe.Node(interface=Scrubbing(), name="scrubbing")
            # fmt:off
            flow.connect(
                [
                    (inputnode, scrubbing, [("preproc_file", "in_file")]),
                    (inputnode, scrubbing, [("registered_wm", "wm_mask")]),
                    (inputnode, scrubbing, [("registered_roi_volumes", "gm_file")]),
                    (inputnode, scrubbing, [("motion_par_file", "motion_parameters")]),
                    (scrubbing, outputnode, [("fd_npy", "FD")]),
                    (scrubbing, outputnode, [("dvars_npy", "DVARS")]),
                ]
            )
            # fmt:on

        detrending_output = pe.Node(
            interface=util.IdentityInterface(fields=["detrending_output"]),
            name="detrending_output",
        )
        if self.config.detrending:
            detrending = pe.Node(interface=Detrending(), name="detrending")
            detrending.inputs.mode = self.config.detrending_mode
            # fmt:off
            flow.connect(
                [
                    (inputnode, detrending, [("preproc_file", "in_file")]),
                    (inputnode, detrending, [("registered_roi_volumes", "gm_file")]),
                    (detrending, detrending_output, [("out_file", "detrending_output")],),
                ]
            )
            # fmt:on
        else:
            # fmt:off
            flow.connect(
                [
                    (inputnode, detrending_output, [("preproc_file", "detrending_output")],)
                ]
            )
            # fmt:on

        nuisance_output = pe.Node(
            interface=util.IdentityInterface(fields=["nuisance_output"]),
            name="nuisance_output",
        )
        if (
            self.config.wm
            or self.config.global_nuisance
            or self.config.csf
            or self.config.motion
        ):
            nuisance = pe.Node(
                interface=NuisanceRegression(), name="nuisance_regression"
            )
            nuisance.inputs.global_nuisance = self.config.global_nuisance
            nuisance.inputs.csf_nuisance = self.config.csf
            nuisance.inputs.wm_nuisance = self.config.wm
            nuisance.inputs.motion_nuisance = self.config.motion
            nuisance.inputs.n_discard = self.config.discard_n_volumes
            # fmt:off
            flow.connect(
                [
                    (detrending_output, nuisance, [("detrending_output", "in_file")]),
                    (inputnode, nuisance, [("eroded_brain", "brainfile")]),
                    (inputnode, nuisance, [("eroded_csf", "csf_file")]),
                    (inputnode, nuisance, [("registered_wm", "wm_file")]),
                    (inputnode, nuisance, [("motion_par_file", "motion_file")]),
                    (inputnode, nuisance, [("registered_roi_volumes", "gm_file")]),
                    (nuisance, nuisance_output, [("out_file", "nuisance_output")]),
                ]
            )
            # fmt:on
        else:
            # fmt:off
            flow.connect(
                [
                    (detrending_output, nuisance_output, [("detrending_output", "nuisance_output")],)
                ]
            )
            # fmt:on

        filter_output = pe.Node(
            interface=util.IdentityInterface(fields=["filter_output"]),
            name="filter_output",
        )
        if self.config.lowpass_filter > 0 or self.config.highpass_filter > 0:
            from cmtklib.interfaces.afni import Bandpass

            filtering = pe.Node(interface=Bandpass(), name="temporal_filter")
            # filtering = pe.Node(interface=afni.Bandpass(),name='temporal_filter')
            converter = pe.Node(
                interface=afni.AFNItoNIFTI(out_file="fMRI_bandpass.nii.gz"),
                name="converter",
            )
            # FIXME: Seems that lowpass and highpass inputs of the nipype 3DBandPass interface swaped low and high frequencies
            filtering.inputs.lowpass = self.config.highpass_filter
            filtering.inputs.highpass = self.config.lowpass_filter

            # if self.config.detrending:
            #    filtering.inputs.no_detrend = True

            filtering.inputs.no_detrend = True

            # fmt:off
            flow.connect(
                [
                    (nuisance_output, filtering, [("nuisance_output", "in_file")]),
                    # (filtering,filter_output,[("out_file","filter_output")])
                    (filtering, converter, [("out_file", "in_file")]),
                    (converter, filter_output, [("out_file", "filter_output")]),
                ]
            )
            # fmt:on
        else:
            # fmt:off
            flow.connect(
                [
                    (nuisance_output, filter_output, [("nuisance_output", "filter_output")],)
                ]
            )
            # fmt:on

        # fmt:off
        flow.connect([(filter_output, outputnode, [("filter_output", "func_file")])])
        # fmt:on

    def define_inspect_outputs(self):
        """Update the `inspect_outputs` class attribute.

        It contains a dictionary of stage outputs with corresponding commands for visual inspection.
        """
        if (
            self.config.wm
            or self.config.global_nuisance
            or self.config.csf
            or self.config.motion
        ):
            res_dir = os.path.join(self.stage_dir, "nuisance_regression")
            nuis = os.path.join(res_dir, "fMRI_nuisance.nii.gz")
            if os.path.exists(nuis):
                self.inspect_outputs_dict["Regression output"] = [
                    "fsleyes",
                    "-sdefault",
                    nuis,
                ]

        if self.config.detrending:
            res_dir = os.path.join(self.stage_dir, "detrending")
            detrend = os.path.join(res_dir, "fMRI_detrending.nii.gz")
            if os.path.exists(detrend):
                self.inspect_outputs_dict["Detrending output"] = [
                    "fsleyes",
                    "-sdefault",
                    detrend,
                    "-cm",
                    "brain_colours_blackbdy_iso",
                ]

        if self.config.lowpass_filter > 0 or self.config.highpass_filter > 0:
            res_dir = os.path.join(self.stage_dir, "converter")
            filt = os.path.join(res_dir, "fMRI_bandpass.nii.gz")
            if os.path.exists(filt):
                self.inspect_outputs_dict["Filter output"] = [
                    "fsleyes",
                    "-sdefault",
                    filt,
                    "-cm",
                    "brain_colours_blackbdy_iso",
                ]

        self.inspect_outputs = sorted(
            [key for key in list(self.inspect_outputs_dict.keys())], key=str.lower
        )

    def has_run(self):
        """Function that returns `True` if the stage has been run successfully.

        Returns
        -------
        `True` if the stage has been run successfully
        """
        if self.config.lowpass_filter > 0 or self.config.highpass_filter > 0:
            return os.path.exists(
                os.path.join(
                    self.stage_dir, "temporal_filter", "result_temporal_filter.pklz"
                )
            )
        elif self.config.detrending:
            return os.path.exists(
                os.path.join(self.stage_dir, "detrending", "result_detrending.pklz")
            )
        elif (
            self.config.wm
            or self.config.global_nuisance
            or self.config.csf
            or self.config.motion
        ):
            return os.path.exists(
                os.path.join(
                    self.stage_dir,
                    "nuisance_regression",
                    "result_nuisance_regression.pklz",
                )
            )
        elif self.config.smoothing > 0.0:
            return os.path.exists(
                os.path.join(self.stage_dir, "smoothing", "result_smoothing.pklz")
            )
        else:
            return True
