# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""Definition of config and stage classes for diffusion reconstruction and tractography."""

# General imports
import os

# Nipype imports
import nipype.interfaces.fsl as fsl

# Own imports
from cmp.stages.common import Stage
from cmtklib.interfaces.misc import ExtractImageVoxelSizes
from .reconstruction import *
from .tracking import *


class DiffusionConfig(HasTraits):
    """Class used to store configuration parameters of a :class:`~cmp.stages.diffusion.diffusion.DiffusionStage` instance.

    Attributes
    ----------
    diffusion_imaging_model_editor : ['DSI', 'DTI', 'HARDI', 'multishell']
        Available diffusion imaging models

    diffusion_imaging_model : traits.Str
        Selected diffusion imaging model
        (Default: 'DTI')

    dilate_rois : traits.Bool
        Dilate parcellation regions-of-interest
        (Default: True)

    dilation_kernel : traits.Enum(['Box', 'Gauss', 'Sphere'])
        Type of dilation kernel to used

    dilation_radius : traits.Enum([1, 2, 3, 4])
        Radius of the dilation kernel

    recon_processing_tool_editor : ['Dipy', 'MRtrix']
        List of processing tools available for diffusion signal reconstruction

    tracking_processing_tool_editor : ['Dipy', 'MRtrix']
        List of processing tools available for tractography

    processing_tool_editor : ['Dipy', 'MRtrix']
        List of processing tools available for diffusion signal reconstruction and tractography

    recon_processing_tool : traits.Str
        Processing tool to use for diffusion signal modeling
        (Default: 'MRtrix')

    tracking_processing_tool : traits.Str
        Processing tool to use for tractography
        (Default: 'MRtrix')

    custom_track_file : traits.File
        Custom tractogram file to used as input to the connectome stage (obsolete)

    dipy_recon_config : Instance(HasTraits)
        Configuration instance of the Dipy reconstruction stage

    mrtrix_recon_config : Instance(HasTraits)
        Configuration instance of the MRtrix3 reconstruction stage

    dipy_tracking_config : Instance(HasTraits)
        Configuration instance of the Dipy tracking (tractography) stage

    mrtrix_tracking_config : Instance(HasTraits)
        Configuration instance of the MRtrix3 tracking (tractography) stage

    diffusion_model_editor : ['Deterministic', 'Probabilistic']
        List of types of available local tractography algorithms.

    diffusion_model : traits.Str
        Type of local tractography algorithm to use.
        (Default: 'Probabilistic')

    See Also
    --------
    cmp.stages.diffusion.reconstruction.DipyReconConfig
    cmp.stages.diffusion.reconstruction.MRtrixReconConfig
    cmp.stages.diffusion.tracking.DipyTrackingConfig
    cmp.stages.diffusion.tracking.MRtrixTrackingConfig
    cmp.stages.diffusion.diffusion.DiffusionStage
    """

    diffusion_imaging_model_editor = List(["DSI", "DTI", "HARDI", "multishell"])
    diffusion_imaging_model = Str("DTI")
    dilate_rois = Bool(True)
    dilation_kernel = Enum(["Box", "Gauss", "Sphere"])
    dilation_radius = Enum([1, 2, 3, 4])
    recon_processing_tool_editor = List(["Dipy", "MRtrix"])
    tracking_processing_tool_editor = List(["Dipy", "MRtrix"])
    processing_tool_editor = List(["Dipy", "MRtrix"])
    recon_processing_tool = Str("MRtrix")
    tracking_processing_tool = Str("MRtrix")
    custom_track_file = File
    dipy_recon_config = Instance(HasTraits)
    mrtrix_recon_config = Instance(HasTraits)
    dipy_tracking_config = Instance(HasTraits)
    mrtrix_tracking_config = Instance(HasTraits)
    diffusion_model_editor = List(["Deterministic", "Probabilistic"])
    diffusion_model = Str("Probabilistic")

    # TODO import custom DWI and tractogram (need to register anatomical data to DWI to project parcellated ROIs onto the tractogram)

    def __init__(self):
        """Constructor of an :class:`cmp.stages.diffusion.diffusion.DiffusionConfig` object."""
        self.dipy_recon_config = DipyReconConfig(
            imaging_model=self.diffusion_imaging_model,
            recon_mode=self.diffusion_model,
            tracking_processing_tool=self.tracking_processing_tool,
        )
        self.mrtrix_recon_config = MRtrixReconConfig(
            imaging_model=self.diffusion_imaging_model, recon_mode=self.diffusion_model
        )
        self.dipy_tracking_config = DipyTrackingConfig(
            imaging_model=self.diffusion_imaging_model,
            tracking_mode=self.diffusion_model,
            SD=self.mrtrix_recon_config.local_model,
        )
        self.mrtrix_tracking_config = MRtrixTrackingConfig(
            tracking_mode=self.diffusion_model, SD=self.mrtrix_recon_config.local_model
        )

        self.mrtrix_recon_config.on_trait_change(
            self.update_mrtrix_tracking_SD, "local_model"
        )
        self.dipy_recon_config.on_trait_change(
            self.update_dipy_tracking_SD, "local_model"
        )
        self.dipy_recon_config.on_trait_change(
            self.update_dipy_tracking_sh_order, "lmax_order"
        )

    def _tracking_processing_tool_changed(self, new):
        """Update ``self.mrtrix_recon_config.tracking_processing_tool`` when ``tracking_processing_tool`` is updated.

        Parameters
        ----------
        new
            New value of ``tracking_processing_tool``
        """
        if new == "MRtrix":
            self.mrtrix_recon_config.tracking_processing_tool = new
        elif new == "Dipy":
            self.dipy_recon_config.tracking_processing_tool = new

    def _diffusion_imaging_model_changed(self, new):
        """Update ``imaging_model`` of ``mrtrix_recon_config``,  ``dipy_recon_config``and ``dipy_tracking_config``.

        Function called when `diffusion_imaging_model` is updated.

        Parameters
        ----------
        new
            New value of ``diffusion_imaging_model``
        """
        self.mrtrix_recon_config.imaging_model = new
        self.dipy_recon_config.imaging_model = new
        self.dipy_tracking_config.imaging_model = new

        # Remove MRtrix from recon and tracking methods and Probabilistic from diffusion model if diffusion_imaging_model is DSI
        if new == "DSI":  # and (self.recon_processing_tool != 'Custom'):
            self.recon_processing_tool = "Dipy"
            self.recon_processing_tool_editor = ["Dipy"]
            self.tracking_processing_tool_editor = ["Dipy", "MRtrix"]
            self.diffusion_model_editor = ["Deterministic", "Probabilistic"]
        else:
            self.recon_processing_tool_editor = ["Dipy", "MRtrix"]
            self.tracking_processing_tool_editor = ["Dipy", "MRtrix"]

            if self.tracking_processing_tool == "DTK":
                self.diffusion_model_editor = ["Deterministic"]
            else:
                self.diffusion_model_editor = ["Deterministic", "Probabilistic"]

    def _recon_processing_tool_changed(self, new):
        """Update ``self.tracking_processing_tool`` and ``self.tracking_processing_tool_editor``.

        Function called when `recon_processing_tool` is updated.

        Parameters
        ----------
        new : string
            New value of ``recon_processing_tool``
        """
        if new == "Dipy" and self.diffusion_imaging_model != "DSI":
            tracking_processing_tool = self.tracking_processing_tool
            self.tracking_processing_tool_editor = ["Dipy", "MRtrix"]
            if (
                tracking_processing_tool == "Dipy"
                or tracking_processing_tool == "MRtrix"
            ):
                self.tracking_processing_tool = tracking_processing_tool
        elif new == "Dipy" and self.diffusion_imaging_model == "DSI":
            tracking_processing_tool = self.tracking_processing_tool
            self.tracking_processing_tool_editor = ["Dipy", "MRtrix"]
            if (
                tracking_processing_tool == "Dipy"
                or tracking_processing_tool == "MRtrix"
            ):
                self.tracking_processing_tool = tracking_processing_tool
        elif new == "MRtrix":
            self.tracking_processing_tool_editor = ["MRtrix"]
        # elif new == 'Custom':
        #     self.tracking_processing_tool_editor = ['Custom']

    def _tracking_processing_tool_changed(self, new):
        """Update ``self.mrtrix_recon_config.tracking_processing_tool`` when ``tracking_processing_tool`` is updated.

        Parameters
        ----------
        new
            New value of ``tracking_processing_tool``
        """
        if new == "Dipy" and self.recon_processing_tool == "Dipy":
            self.dipy_recon_config.tracking_processing_tool = "Dipy"
        elif new == "MRtrix" and self.recon_processing_tool == "Dipy":
            self.dipy_recon_config.tracking_processing_tool = "MRtrix"

    def _diffusion_model_changed(self, new):
        """Update ``tracking_mode`` of ``self.mrtrix_tracking_config`` and ``self.dipy_tracking_config``.

        Function called when `diffusion_model` is updated.

        Parameters
        ----------
        new : string
            New value of ``diffusion_model``
        """
        # Probabilistic tracking only available for Spherical Deconvoluted data
        if self.tracking_processing_tool == "MRtrix":
            self.mrtrix_tracking_config.tracking_mode = new
            if new == "Deterministic":
                self.mrtrix_tracking_config.backtrack = False
        elif self.tracking_processing_tool == "Dipy":
            self.dipy_tracking_config.tracking_mode = new

    def update_dipy_tracking_sh_order(self, new):
        """Update ``sh_order`` of ``dipy_tracking_config`` when ``lmax_order`` is updated.

        Parameters
        ----------
        new: int
            New value of ``lmax_order``
        """
        if new != "Auto":
            self.dipy_tracking_config.sh_order = new
        else:
            self.dipy_tracking_config.sh_order = 8

    def update_mrtrix_tracking_SD(self, new):
        """Update ``SD`` of ``mrtrix_tracking_config`` when ``local_model`` is updated.

        Parameters
        ----------
        new: string
            New value of ``local_model``
        """
        self.mrtrix_tracking_config.SD = new

    def update_dipy_tracking_SD(self, new):
        """Update ``SD`` of ``dipy_tracking_config`` when ``local_model`` is updated.

        Parameters
        ----------
        new : string
            New value of ``local_model``
        """
        self.dipy_tracking_config.SD = new


def strip_suffix(file_input, prefix):
    """Extract path of ``file_input`` and add `prefix` to generate a prefix path for outputs.

    Parameters
    ----------
    file_input: os.path.abspath
        Absolute path to an input file
    prefix: os.path
        Prefix to used in the generation of the output prefix path.
    Returns
    -------
    out_prefix_path: os.path
        The generated prefix path
    """
    import os
    from nipype.utils.filemanip import split_filename

    path, _, _ = split_filename(file_input)
    out_prefix_path = os.path.join(path, prefix + "_")
    return out_prefix_path


class DiffusionStage(Stage):
    """Class that represents the diffusion stage of a :class:`~cmp.pipelines.diffusion.diffusion.DiffusionPipeline`.

    The diffusion stage workflow is composed of two sub-workflows:
    1. `recon_flow` that estimates tensors or fiber orientation distribution functions from dMRI,
    2. `track_flow` that runs tractography from the output of `recon_flow`.

    Methods
    -------
    create_workflow()
        Create the workflow of the `DiffusionStage`

    See Also
    --------
    cmp.pipelines.diffusion.diffusion.DiffusionPipeline
    cmp.stages.diffusion.diffusion.DiffusionConfig
    cmp.stages.diffusion.reconstruction.DipyReconConfig
    cmp.stages.diffusion.reconstruction.MRtrixReconConfig
    cmp.stages.diffusion.tracking.DipyTrackingConfig
    cmp.stages.diffusion.tracking.MRtrixTrackingConfig
    cmp.stages.diffusion.reconstruction.create_dipy_recon_flow
    cmp.stages.diffusion.reconstruction.create_mrtrix_recon_flow
    cmp.stages.diffusion.tracking.create_dipy_tracking_flow
    cmp.stages.diffusion.tracking.create_mrtrix_tracking_flow
    """

    def __init__(self, bids_dir, output_dir):
        """Constructor of a :class:`~cmp.stages.diffusion.diffusion.DiffusionStage` instance."""
        self.name = "diffusion_stage"
        self.bids_dir = bids_dir
        self.output_dir = output_dir
        self.config = DiffusionConfig()
        self.inputs = [
            "diffusion",
            "partial_volumes",
            "wm_mask_registered",
            "brain_mask_registered",
            "act_5tt_registered",
            "gmwmi_registered",
            "roi_volumes",
            "grad",
            "bvals",
            "bvecs",
        ]
        self.outputs = [
            "diffusion_model",
            "track_file",
            "fod_file",
            "FA",
            "ADC",
            "RD",
            "AD",
            "skewness",
            "kurtosis",
            "P0",
            "roi_volumes",
            "shore_maps",
            "mapmri_maps",
        ]

    def create_workflow(self, flow, inputnode, outputnode):
        """Create the stage worflow.

        Parameters
        ----------
        flow : nipype.pipeline.engine.Workflow
            The nipype.pipeline.engine.Workflow instance of the Diffusion pipeline

        inputnode : nipype.interfaces.utility.IdentityInterface
            Identity interface describing the inputs of the stage

        outputnode : nipype.interfaces.utility.IdentityInterface
            Identity interface describing the outputs of the stage

        See Also
        --------
        cmp.stages.diffusion.reconstruction.create_dipy_recon_flow
        cmp.stages.diffusion.reconstruction.create_mrtrix_recon_flow
        cmp.stages.diffusion.tracking.create_dipy_tracking_flow
        cmp.stages.diffusion.tracking.create_mrtrix_tracking_flow
        """
        if self.config.dilate_rois:

            dilate_rois = pe.MapNode(
                interface=fsl.DilateImage(), iterfield=["in_file"], name="dilate_rois"
            )
            dilate_rois.inputs.operation = "modal"

            if self.config.dilation_kernel == "Box":
                kernel_size = 2 * self.config.dilation_radius + 1
                dilate_rois.inputs.kernel_shape = "boxv"
                dilate_rois.inputs.kernel_size = kernel_size
            else:
                extract_sizes = pe.Node(
                    interface=ExtractImageVoxelSizes(), name="extract_sizes"
                )
                flow.connect([(inputnode, extract_sizes, [("diffusion", "in_file")])])
                extract_sizes.run()
                print("Voxel sizes : ", extract_sizes.outputs.voxel_sizes)

                min_size = 100
                for voxel_size in extract_sizes.outputs.voxel_sizes:
                    if voxel_size < min_size:
                        min_size = voxel_size

                print("voxel size (min): %g" % min_size)
                if self.config.dilation_kernel == "Gauss":
                    kernel_size = 2 * extract_sizes.outputs.voxel_sizes + 1
                    # FWHM criteria, i.e. sigma = FWHM / 2(sqrt(2ln(2)))
                    sigma = kernel_size / 2.355
                    dilate_rois.inputs.kernel_shape = "gauss"
                    dilate_rois.inputs.kernel_size = sigma
                elif self.config.dilation_kernel == "Sphere":
                    radius = 0.5 * min_size + self.config.dilation_radius * min_size
                    dilate_rois.inputs.kernel_shape = "sphere"
                    dilate_rois.inputs.kernel_size = radius
            # fmt: off
            flow.connect(
                [
                    (inputnode, dilate_rois, [("roi_volumes", "in_file")]),
                    (dilate_rois, outputnode, [("out_file", "roi_volumes")]),
                ]
            )
            # fmt: on
        else:
            # fmt: off
            flow.connect([(inputnode, outputnode, [("roi_volumes", "roi_volumes")])])
            # fmt: on

        if self.config.recon_processing_tool == "Dipy":
            recon_flow = create_dipy_recon_flow(self.config.dipy_recon_config)
            # fmt: off
            flow.connect(
                [
                    (inputnode, recon_flow, [("diffusion", "inputnode.diffusion")]),
                    (inputnode, recon_flow, [("bvals", "inputnode.bvals")]),
                    (inputnode, recon_flow, [("bvecs", "inputnode.bvecs")]),
                    (inputnode, recon_flow, [("diffusion", "inputnode.diffusion_resampled")],),
                    (inputnode, recon_flow, [("wm_mask_registered", "inputnode.wm_mask_resampled")],),
                    (inputnode, recon_flow, [("brain_mask_registered", "inputnode.brain_mask_resampled")],),
                    (recon_flow, outputnode, [("outputnode.FA", "FA")]),
                    (recon_flow, outputnode, [("outputnode.MD", "ADC")]),
                    (recon_flow, outputnode, [("outputnode.AD", "AD")]),
                    (recon_flow, outputnode, [("outputnode.RD", "RD")]),
                    (recon_flow, outputnode, [("outputnode.shore_maps", "shore_maps")]),
                    (recon_flow, outputnode, [("outputnode.mapmri_maps", "mapmri_maps")],),
                ]
            )
            # fmt: on

        elif self.config.recon_processing_tool == "MRtrix":
            # TODO modify nipype tensormetric interface to get AD and RD maps
            recon_flow = create_mrtrix_recon_flow(self.config.mrtrix_recon_config)
            # fmt: off
            flow.connect(
                [
                    (inputnode, recon_flow, [("diffusion", "inputnode.diffusion")]),
                    (inputnode, recon_flow, [("grad", "inputnode.grad")]),
                    (inputnode, recon_flow, [("diffusion", "inputnode.diffusion_resampled")],),
                    (inputnode, recon_flow, [("brain_mask_registered", "inputnode.wm_mask_resampled")],),
                    (recon_flow, outputnode, [("outputnode.FA", "FA")]),
                    (recon_flow, outputnode, [("outputnode.ADC", "ADC")]),
                    (recon_flow, outputnode, [("outputnode.tensor", "tensor")]),
                    # (recon_flow,outputnode,[("outputnode.AD","AD")]),
                    # (recon_flow,outputnode,[("outputnode.RD","RD")]),
                ]
            )
            # fmt: on

        if self.config.tracking_processing_tool == "Dipy":
            track_flow = create_dipy_tracking_flow(self.config.dipy_tracking_config)

            if self.config.diffusion_imaging_model != "DSI":
                # fmt: off
                flow.connect(
                    [
                        (recon_flow, outputnode, [("outputnode.DWI", "fod_file")]),
                        (recon_flow, track_flow, [("outputnode.model", "inputnode.model")],),
                        (inputnode, track_flow, [("bvals", "inputnode.bvals")]),
                        (recon_flow, track_flow, [("outputnode.bvecs", "inputnode.bvecs")],),
                        # Diffusion resampled
                        (inputnode, track_flow, [("diffusion", "inputnode.DWI")]),
                        (inputnode, track_flow, [("partial_volumes", "inputnode.partial_volumes")],),
                        (inputnode, track_flow, [("wm_mask_registered", "inputnode.wm_mask_resampled")],),
                        # (inputnode, track_flow,[('diffusion','inputnode.DWI')]),
                        (recon_flow, track_flow, [("outputnode.FA", "inputnode.FA")]),
                        (dilate_rois, track_flow, [("out_file", "inputnode.gm_registered")],)
                        # (recon_flow, track_flow,[('outputnode.SD','inputnode.SD')]),
                    ]
                )
                # fmt: on
            else:
                # fmt: off
                flow.connect(
                    [
                        (recon_flow, outputnode, [("outputnode.fod", "fod_file")]),
                        (recon_flow, track_flow, [("outputnode.fod", "inputnode.fod_file")],),
                        (recon_flow, track_flow, [("outputnode.model", "inputnode.model")],),
                        (inputnode, track_flow, [("bvals", "inputnode.bvals")]),
                        (recon_flow, track_flow, [("outputnode.bvecs", "inputnode.bvecs")],),
                        # Diffusion resampled
                        (inputnode, track_flow, [("diffusion", "inputnode.DWI")]),
                        (inputnode, track_flow, [("partial_volumes", "inputnode.partial_volumes")],),
                        (inputnode, track_flow, [("wm_mask_registered", "inputnode.wm_mask_resampled")],),
                        # (inputnode, track_flow,[('diffusion','inputnode.DWI')]),
                        (recon_flow, track_flow, [("outputnode.FA", "inputnode.FA")]),
                        (dilate_rois, track_flow, [("out_file", "inputnode.gm_registered")],)
                        # (recon_flow, track_flow,[('outputnode.SD','inputnode.SD')]),
                    ]
                )
                # fmt: on

            if (
                self.config.dipy_tracking_config.use_act
                and self.config.dipy_tracking_config.seed_from_gmwmi
            ):
                # fmt: off
                flow.connect(
                    [
                        (inputnode, track_flow, [("gmwmi_registered", "inputnode.gmwmi_file")],),
                    ]
                )
                # fmt: on

            # fmt: off
            flow.connect(
                [(track_flow, outputnode, [("outputnode.track_file", "track_file")])]
            )
            # fmt: on

        elif (
            self.config.tracking_processing_tool == "MRtrix"
            and self.config.recon_processing_tool == "MRtrix"
        ):
            track_flow = create_mrtrix_tracking_flow(self.config.mrtrix_tracking_config)
            # fmt: off
            flow.connect(
                [
                    (inputnode, track_flow, [("wm_mask_registered", "inputnode.wm_mask_resampled")]),
                    (recon_flow, outputnode, [("outputnode.DWI", "fod_file")]),
                    (recon_flow, track_flow, [("outputnode.DWI", "inputnode.DWI"), ("outputnode.grad", "inputnode.grad")]),
                    # (recon_flow, track_flow,[('outputnode.SD','inputnode.SD')]),
                ]
            )
            # fmt: on

            if self.config.dilate_rois:
                # fmt: off
                flow.connect(
                    [
                        (dilate_rois, track_flow, [("out_file", "inputnode.gm_registered")])
                    ]
                )
                # fmt: on
            else:
                # fmt: off
                flow.connect(
                    [
                        (inputnode, track_flow, [("roi_volumes", "inputnode.gm_registered")])
                    ]
                )
                # fmt: on

            # fmt: off
            flow.connect(
                [
                    (inputnode, track_flow, [("act_5tt_registered", "inputnode.act_5tt_registered")],),
                    (inputnode, track_flow, [("gmwmi_registered", "inputnode.gmwmi_registered")],),
                ]
            )
            # fmt: on

            # fmt: off
            flow.connect(
                [(track_flow, outputnode, [("outputnode.track_file", "track_file")])]
            )
            # fmt: on

        elif (
            self.config.tracking_processing_tool == "MRtrix"
            and self.config.recon_processing_tool == "Dipy"
        ):

            track_flow = create_mrtrix_tracking_flow(self.config.mrtrix_tracking_config)

            if self.config.diffusion_imaging_model != "DSI":
                # fmt: off
                flow.connect(
                    [
                        (inputnode, track_flow, [("wm_mask_registered", "inputnode.wm_mask_resampled"), ("grad", "inputnode.grad"),],),
                        (recon_flow, outputnode, [("outputnode.DWI", "fod_file")]),
                        (recon_flow, track_flow, [("outputnode.DWI", "inputnode.DWI")]),
                        # (recon_flow, track_flow,[('outputnode.SD','inputnode.SD')]),
                    ]
                )
                # fmt: on
            else:
                # fmt: off
                flow.connect(
                    [
                        (inputnode, track_flow, [("wm_mask_registered", "inputnode.wm_mask_resampled"), ("grad", "inputnode.grad"),],),
                        (recon_flow, outputnode, [("outputnode.fod", "fod_file")]),
                        (recon_flow, track_flow, [("outputnode.fod", "inputnode.DWI")]),
                        # (recon_flow, track_flow,[('outputnode.SD','inputnode.SD')]),
                    ]
                )
                # fmt: on

            if self.config.dilate_rois:
                # fmt: off
                flow.connect(
                    [
                        (dilate_rois, track_flow, [("out_file", "inputnode.gm_registered")],)
                    ]
                )
                # fmt: on
            else:
                # fmt: off
                flow.connect(
                    [
                        (inputnode, track_flow, [("roi_volumes", "inputnode.gm_registered")],)
                    ]
                )
                # fmt: on

            # fmt: off
            flow.connect(
                [
                    (inputnode, track_flow, [("act_5tt_registered", "inputnode.act_5tt_registered")],),
                    (inputnode, track_flow, [("gmwmi_registered", "inputnode.gmwmi_registered")],),
                ]
            )
            # fmt: on

            # fmt: off
            flow.connect(
                [(track_flow, outputnode, [("outputnode.track_file", "track_file")])]
            )
            # fmt: on

        temp_node = pe.Node(
            interface=util.IdentityInterface(fields=["diffusion_model"]),
            name="diffusion_model",
        )
        temp_node.inputs.diffusion_model = self.config.diffusion_model
        # fmt: off
        flow.connect(
            [(temp_node, outputnode, [("diffusion_model", "diffusion_model")])]
        )
        # fmt: on

        # if self.config.tracking_processing_tool == 'Custom':
        #     # FIXME make sure header of TRK / TCK are consistent with DWI
        #     custom_node = pe.Node(interface=util.IdentityInterface(fields=["custom_track_file"]),
        #                           name='read_custom_track')
        #     custom_node.inputs.custom_track_file = self.config.custom_track_file
        #     if nib.streamlines.detect_format(self.config.custom_track_file) is nib.streamlines.TrkFile:
        #         print("> load TRK tractography file")
        #         flow.connect([
        #             (custom_node, outputnode, [
        #              ("custom_track_file", "track_file")])
        #         ])
        #     elif nib.streamlines.detect_format(self.config.custom_track_file) is nib.streamlines.TckFile:
        #         print("> load TCK tractography file and convert to TRK format")
        #         converter = pe.Node(interface=Tck2Trk(), name='trackvis')
        #         converter.inputs.out_tracks = 'converted.trk'

        #         flow.connect([
        #             (custom_node, converter, [
        #              ('custom_track_file', 'in_tracks')]),
        #             (inputnode, converter, [
        #              ('wm_mask_registered', 'in_image')]),
        #             (converter, outputnode, [('out_tracks', 'track_file')])
        #         ])
        #     else:
        #         print(
        #             "Invalid tractography input format. Valid formats are .tck (MRtrix) and .trk (DTK/Trackvis)")

    def define_inspect_outputs(self):
        """Update the `inspect_outputs` class attribute.

        It contains a dictionary of stage outputs with corresponding commands for visual inspection.
        """
        self.inspect_outputs_dict = {}

        # RECON outputs
        # Dipy
        if self.config.recon_processing_tool == "Dipy":
            if (
                self.config.dipy_recon_config.local_model
                or self.config.diffusion_imaging_model == "DSI"
            ):  # SHORE or CSD models

                if self.config.diffusion_imaging_model == "DSI":

                    recon_dir = os.path.join(
                        self.stage_dir, "reconstruction", "dipy_SHORE"
                    )

                    gfa_res = os.path.join(recon_dir, "shore_gfa.nii.gz")
                    if os.path.exists(gfa_res):
                        self.inspect_outputs_dict[
                            self.config.recon_processing_tool + " gFA image"
                        ] = ["mrview", gfa_res]
                    msd_res = os.path.join(recon_dir, "shore_msd.nii.gz")
                    if os.path.exists(msd_res):
                        self.inspect_outputs_dict[
                            self.config.recon_processing_tool + " MSD image"
                        ] = ["mrview", msd_res]
                    rtop_res = os.path.join(recon_dir, "shore_rtop_signal.nii.gz")
                    if os.path.exists(rtop_res):
                        self.inspect_outputs_dict[
                            self.config.recon_processing_tool + " RTOP image"
                        ] = ["mrview", rtop_res]
                    dodf_res = os.path.join(recon_dir, "shore_dodf.nii.gz")
                    if os.path.exists(dodf_res):
                        self.inspect_outputs_dict[
                            self.config.recon_processing_tool
                            + " Diffusion ODF (SHORE) image"
                        ] = ["mrview", gfa_res, "-odf.load_sh", dodf_res]
                    shm_coeff_res = os.path.join(recon_dir, "shore_fodf.nii.gz")
                    if os.path.exists(shm_coeff_res):
                        self.inspect_outputs_dict[
                            self.config.recon_processing_tool
                            + " Fiber ODF (SHORE) image"
                        ] = ["mrview", gfa_res, "-odf.load_sh", shm_coeff_res]
                else:
                    recon_tensor_dir = os.path.join(
                        self.stage_dir, "reconstruction", "dipy_tensor"
                    )

                    fa_res = os.path.join(
                        recon_tensor_dir, "diffusion_preproc_resampled_fa.nii.gz"
                    )
                    if os.path.exists(fa_res):
                        self.inspect_outputs_dict[
                            self.config.recon_processing_tool + " FA image"
                        ] = ["mrview", fa_res]

                    recon_dir = os.path.join(
                        self.stage_dir, "reconstruction", "dipy_CSD"
                    )
                    shm_coeff_res = os.path.join(
                        recon_dir, "diffusion_shm_coeff.nii.gz"
                    )
                    if os.path.exists(shm_coeff_res):
                        if os.path.exists(fa_res):
                            self.inspect_outputs_dict[
                                self.config.recon_processing_tool + " ODF (CSD) image"
                            ] = ["mrview", fa_res, "-odf.load_sh", shm_coeff_res]
                        else:
                            self.inspect_outputs_dict[
                                self.config.recon_processing_tool + " ODF (CSD) image"
                            ] = ["mrview", shm_coeff_res, "-odf.load_sh", shm_coeff_res]

        # TODO: add Tensor image in case of DTI+Tensor modeling
        # MRtrix
        if self.config.recon_processing_tool == "MRtrix":
            metrics_dir = os.path.join(
                self.stage_dir, "reconstruction", "mrtrix_tensor_metrics"
            )

            fa_res = os.path.join(metrics_dir, "FA.mif")
            if os.path.exists(fa_res):
                self.inspect_outputs_dict[
                    self.config.recon_processing_tool + " FA image"
                ] = ["mrview", fa_res]

            adc_res = os.path.join(metrics_dir, "ADC.mif")
            if os.path.exists(adc_res):
                self.inspect_outputs_dict[
                    self.config.recon_processing_tool + " ADC image"
                ] = ["mrview", adc_res]

            # Tensor model (DTI)
            if not self.config.mrtrix_recon_config.local_model:
                recon_dir = os.path.join(
                    self.stage_dir, "reconstruction", "mrtrix_make_tensor"
                )

                tensor_res = os.path.join(
                    recon_dir, "diffusion_preproc_resampled_tensor.mif"
                )
                if os.path.exists(fa_res) and os.path.exists(tensor_res):
                    self.inspect_outputs_dict[
                        self.config.recon_processing_tool + " SH image"
                    ] = ["mrview", fa_res, "-odf.load_tensor", tensor_res]
            else:  # CSD model
                RF_dir = os.path.join(self.stage_dir, "reconstruction", "mrtrix_rf")
                RF_resp = os.path.join(RF_dir, "diffusion_preproc_resampled_ER.mif")
                if os.path.exists(RF_resp):
                    self.inspect_outputs_dict["MRTRIX Response function"] = [
                        "shview",
                        "-response",
                        RF_resp,
                    ]

                recon_dir = os.path.join(self.stage_dir, "reconstruction", "mrtrix_CSD")
                shm_coeff_res = os.path.join(
                    recon_dir, "diffusion_preproc_resampled_CSD.mif"
                )
                if os.path.exists(fa_res) and os.path.exists(shm_coeff_res):
                    self.inspect_outputs_dict[
                        self.config.recon_processing_tool + " SH image"
                    ] = ["mrview", fa_res, "-odf.load_sh", shm_coeff_res]

        # Tracking outputs
        # Dipy
        if self.config.tracking_processing_tool == "Dipy":
            if (
                self.config.dipy_recon_config.local_model
                or self.config.diffusion_imaging_model == "DSI"
            ):
                if self.config.diffusion_model == "Deterministic":
                    diff_dir = os.path.join(
                        self.stage_dir, "tracking", "dipy_deterministic_tracking"
                    )
                    streamline_res = os.path.join(diff_dir, "tract.trk")
                else:
                    diff_dir = os.path.join(
                        self.stage_dir, "tracking", "dipy_probabilistic_tracking"
                    )
                    streamline_res = os.path.join(diff_dir, "tract.trk")

                if os.path.exists(streamline_res):
                    self.inspect_outputs_dict[
                        self.config.tracking_processing_tool
                        + " "
                        + self.config.diffusion_model
                        + " streamline"
                    ] = ["trackvis", streamline_res]
            else:
                diff_dir = os.path.join(
                    self.stage_dir, "tracking", "dipy_dtieudx_tracking"
                )
                streamline_res = os.path.join(diff_dir, "tract.trk")
                if os.path.exists(streamline_res):
                    self.inspect_outputs_dict[
                        self.config.tracking_processing_tool
                        + " Tensor-based EuDX streamline"
                    ] = ["trackvis", streamline_res]

        # MRtrix
        if self.config.tracking_processing_tool == "MRtrix":

            diff_dir = os.path.join(self.stage_dir, "tracking", "trackvis")
            streamline_res = os.path.join(diff_dir, "tract.trk")

            if os.path.exists(streamline_res):
                self.inspect_outputs_dict[
                    self.config.tracking_processing_tool
                    + " "
                    + self.config.diffusion_model
                    + " streamline"
                ] = ["trackvis", streamline_res]

        self.inspect_outputs = sorted(
            [key for key in list(self.inspect_outputs_dict.keys())], key=str.lower
        )

    def has_run(self):
        """Function that returns `True` if the stage has been run successfully.

        Returns
        -------
        `True` if the stage has been run successfully
        """
        if self.config.tracking_processing_tool == "Dipy":
            if self.config.diffusion_model == "Deterministic":
                return os.path.exists(
                    os.path.join(
                        self.stage_dir,
                        "tracking",
                        "dipy_deterministic_tracking",
                        "result_dipy_deterministic_tracking.pklz",
                    )
                )
            elif self.config.diffusion_model == "Probabilistic":
                return os.path.exists(
                    os.path.join(
                        self.stage_dir,
                        "tracking",
                        "dipy_probabilistic_tracking",
                        "result_dipy_probabilistic_tracking.pklz",
                    )
                )
        elif self.config.tracking_processing_tool == "MRtrix":
            return os.path.exists(
                os.path.join(
                    self.stage_dir, "tracking", "trackvis", "result_trackvis.pklz"
                )
            )
