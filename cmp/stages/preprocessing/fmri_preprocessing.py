# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""Definition of config and stage classes for pre-registration fMRI preprocessing."""

# General imports
import os
from glob import glob

from traits.api import *

import nipype.pipeline.engine as pe
import nipype.interfaces.fsl as fsl
from nipype.interfaces import afni
import nipype.interfaces.utility as util

# Own imports
from cmtklib.interfaces.afni import Despike
from cmp.stages.common import Stage
from cmtklib.functionalMRI import DiscardTP


class PreprocessingConfig(HasTraits):
    """Class used to store configuration parameters of a :class:`~cmp.stages.preprocessing.fmri_preprocessing.PreprocessingStage` object.

    Attributes
    ----------
    discard_n_volumes : traits.Int

        (Default: '5')

    despiking : traits.Bool

        (Default: True)

    slice_timing : traits.Enum
        Slice acquisition order for slice timing correction that can be:
        "bottom-top interleaved", "bottom-top interleaved", "top-bottom interleaved",
        "bottom-top", and "top-bottom"
        (Default: "none")

    repetition_time : traits.Float
        Repetition time
        (Default: 1.92)

    motion_correction : traits.Bool
        Perform motion correction
        (Default: True)

    See Also
    --------
    cmp.stages.preprocessing.fmri_preprocessing.PreprocessingStage
    """

    discard_n_volumes = Int("5")
    despiking = Bool(True)
    slice_timing = Enum(
        "none",
        [
            "none",
            "bottom-top interleaved",
            "bottom-top interleaved",
            "top-bottom interleaved",
            "bottom-top",
            "top-bottom",
        ],
    )
    repetition_time = Float(1.92)
    motion_correction = Bool(True)


class PreprocessingStage(Stage):
    """Class that represents the pre-registration preprocessing stage of a :class:`~cmp.pipelines.functional.fMRI.fMRIPipeline` instance.

    Methods
    -------
    create_workflow()
        Create the workflow of the `PreprocessingStage`

    See Also
    --------
    cmp.pipelines.functional.fMRI.fMRIPipeline
    cmp.stages.preprocessing.fmri_preprocessing.PreprocessingConfig
    """

    def __init__(self, bids_dir, output_dir):
        """Constructor of a :class:`~cmp.stages.preprocessing.fmri_preprocessing.PreprocessingStage` instance."""
        self.name = "preprocessing_stage"
        self.bids_dir = bids_dir
        self.output_dir = output_dir

        self.config = PreprocessingConfig()
        self.inputs = ["functional"]
        self.outputs = ["functional_preproc", "par_file", "mean_vol"]

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
        discard_output = pe.Node(
            interface=util.IdentityInterface(fields=["discard_output"]),
            name="discard_output",
        )
        if self.config.discard_n_volumes > 0:
            discard = pe.Node(
                interface=DiscardTP(n_discard=self.config.discard_n_volumes),
                name="discard_volumes",
            )
            # fmt:off
            flow.connect(
                [
                    (inputnode, discard, [("functional", "in_file")]),
                    (discard, discard_output, [("out_file", "discard_output")]),
                ]
            )
            # fmt:on
        else:
            # fmt:off
            flow.connect(
                [(inputnode, discard_output, [("functional", "discard_output")])]
            )
            # fmt:on

        despiking_output = pe.Node(
            interface=util.IdentityInterface(fields=["despiking_output"]),
            name="despkiking_output",
        )
        if self.config.despiking:
            despike = pe.Node(interface=Despike(), name="afni_despike")
            converter = pe.Node(
                interface=afni.AFNItoNIFTI(out_file="fMRI_despike.nii.gz"),
                name="converter",
            )
            # fmt:off
            flow.connect(
                [
                    (discard_output, despike, [("discard_output", "in_file")]),
                    (despike, converter, [("out_file", "in_file")]),
                    (converter, despiking_output, [("out_file", "despiking_output")]),
                ]
            )
            # fmt:on
        else:
            # fmt:off
            flow.connect(
                [
                    (discard_output, despiking_output, [("discard_output", "despiking_output")],)
                ]
            )
            # fmt:on

        if self.config.slice_timing != "none":
            slc_timing = pe.Node(interface=fsl.SliceTimer(), name="slice_timing")
            slc_timing.inputs.time_repetition = self.config.repetition_time
            if self.config.slice_timing == "bottom-top interleaved":
                slc_timing.inputs.interleaved = True
                slc_timing.inputs.index_dir = False
            elif self.config.slice_timing == "top-bottom interleaved":
                slc_timing.inputs.interleaved = True
                slc_timing.inputs.index_dir = True
            elif self.config.slice_timing == "bottom-top":
                slc_timing.inputs.interleaved = False
                slc_timing.inputs.index_dir = False
            elif self.config.slice_timing == "top-bottom":
                slc_timing.inputs.interleaved = False
                slc_timing.inputs.index_dir = True

        # def add_header_and_convert_to_tsv(in_file):

        #     try:

        if self.config.motion_correction:
            mo_corr = pe.Node(
                interface=fsl.MCFLIRT(
                    stats_imgs=True, save_mats=False, save_plots=True, mean_vol=True
                ),
                name="motion_correction",
            )

        if self.config.slice_timing != "none":
            # fmt:off
            flow.connect(
                [(despiking_output, slc_timing, [("despiking_output", "in_file")])]
            )
            # fmt:on
            if self.config.motion_correction:
                # fmt:off
                flow.connect(
                    [
                        (slc_timing, mo_corr, [("slice_time_corrected_file", "in_file")],),
                        (mo_corr, outputnode, [("out_file", "functional_preproc")]),
                        (mo_corr, outputnode, [("par_file", "par_file")]),
                        (mo_corr, outputnode, [("mean_img", "mean_vol")]),
                    ]
                )
                # fmt:on
            else:
                mean = pe.Node(interface=fsl.MeanImage(), name="mean")
                # fmt:off
                flow.connect(
                    [
                        (slc_timing, outputnode, [("slice_time_corrected_file", "functional_preproc")],),
                        (slc_timing, mean, [("slice_time_corrected_file", "in_file")]),
                        (mean, outputnode, [("out_file", "mean_vol")]),
                    ]
                )
                # fmt:on
        else:
            if self.config.motion_correction:
                # fmt:off
                flow.connect(
                    [
                        (despiking_output, mo_corr, [("despiking_output", "in_file")]),
                        (mo_corr, outputnode, [("out_file", "functional_preproc"),
                                               ("par_file", "par_file"),
                                               ("mean_img", "mean_vol")]),
                    ]
                )
                # fmt:on
            else:
                mean = pe.Node(interface=fsl.MeanImage(), name="mean")
                # fmt:off
                flow.connect(
                    [
                        (despiking_output, outputnode, [("despiking_output", "functional_preproc")]),
                        (despiking_output, mean, [("despiking_output", "in_file")]),
                        (mean, outputnode, [("out_file", "mean_vol")]),
                    ]
                )
                # fmt:on

    def define_inspect_outputs(self):
        """Update the `inspect_outputs` class attribute.

        It contains a dictionary of stage outputs with corresponding commands for visual inspection.
        """
        # print('Stage (inspect_outputs): '.format(self.stage_dir))
        if self.config.despiking:
            despike_dir = os.path.join(self.stage_dir, "converter")
            despike = os.path.join(despike_dir, "fMRI_despike.nii.gz")
            if os.path.exists(despike):
                self.inspect_outputs_dict["Spike corrected image"] = [
                    "fsleyes",
                    "-ad",
                    despike,
                    "-cm",
                    "brain_colours_blackbdy_iso",
                ]
        if self.config.slice_timing:
            slc_timing_dir = os.path.join(self.stage_dir, "slice_timing")
            files = glob(os.path.join(slc_timing_dir, "*_st.nii.gz"))
            if len(files) > 0:
                tcorr = files[0]
                if os.path.exists(tcorr):
                    self.inspect_outputs_dict["Slice time corrected image"] = [
                        "fsleyes",
                        "-ad",
                        tcorr,
                        "-cm",
                        "brain_colours_blackbdy_iso",
                    ]
        if self.config.motion_correction:
            motion_results_dir = os.path.join(self.stage_dir, "motion_correction")
            files = glob(os.path.join(motion_results_dir, "*_mcf.nii.gz"))
            if len(files) > 0:
                mcorr = files[0]
                if os.path.exists(mcorr):
                    self.inspect_outputs_dict[
                        "Slice time and motion corrected image"
                    ] = ["fsleyes", "-ad", mcorr, "-cm", "brain_colours_blackbdy_iso"]

        self.inspect_outputs = sorted(
            [key for key in list(self.inspect_outputs_dict.keys())], key=str.lower
        )

    def has_run(self):
        """Function that returns `True` if the stage has been run successfully.

        Returns
        -------
        `True` if the stage has been run successfully
        """
        if self.config.motion_correction:
            return os.path.exists(
                os.path.join(
                    self.stage_dir, "motion_correction", "result_motion_correction.pklz"
                )
            )
        elif self.config.slice_timing:
            return os.path.exists(
                os.path.join(self.stage_dir, "slice_timing", "result_slice_timing.pklz")
            )
        elif self.config.despiking:
            return os.path.exists(
                os.path.join(self.stage_dir, "converter", "result_converter.pklz")
            )
        else:
            return True
