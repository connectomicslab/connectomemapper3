# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""Tracking methods and workflows of the diffusion stage."""

from traits.api import *

from nipype.interfaces.base import traits
import nipype.pipeline.engine as pe
import nipype.interfaces.utility as util
from nipype import logging
# import matplotlib.pyplot as plt

from cmtklib.interfaces.mrtrix3 import Erode, StreamlineTrack, FilterTractogram
from cmtklib.interfaces.dipy import (
    DirectionGetterTractography,
    TensorInformedEudXTractography,
)
from cmtklib.interfaces.misc import ExtractHeaderVoxel2WorldMatrix
from cmtklib.diffusion import Tck2Trk
# from cmtklib.diffusion import filter_fibers


iflogger = logging.getLogger("nipype.interface")


class DipyTrackingConfig(HasTraits):
    """Class used to store Dipy diffusion reconstruction sub-workflow configuration parameters.

    Attributes
    ----------
    imaging_model : traits.Str
        Diffusion imaging model
        (For example 'DTI')

    tracking_mode : traits.Str
        Type of local tractography algorithm
        (Can be "Deterministic" or "Probabilistic")

    SD : traits.Bool
        If `True`, inputs are coming from Constrained Spherical Deconvolution reconstruction

    number_of_seeds : traits.Int
        Number of seeds
        (Default: 1000)

    seed_density : traits.Float
        Number of seeds to place along each direction where a density of 2 is the same as [2, 2, 2]
        and will result in a total of 8 seeds per voxel
        (Default: 1.0)

    fa_thresh : traits.Float
        Fractional Anisotropy (FA) threshold
        (Default: 0.2)

    step_size : traits.traits.Float
        Tractography algorithm step size
        (Default: 0.5)

    max_angle : traits.Float
        Maximum streamline angle allowed
        (Default: 25.0)

    sh_order : traits.Int
        Order used for Constrained Spherical Deconvolution reconstruction
        (Default: 8)

    use_act : traits.Bool
        Use FAST for partial volume estimation and Anatomically-Constrained Tractography (ACT) tissue classifier
        (Default: False)

    seed_from_gmwmi : traits.Bool
        Seed from Grey Matter / White Matter interface
        (requires Anatomically-Constrained Tractography (ACT))
        (Default: False)
    """

    imaging_model = Str
    tracking_mode = Str
    SD = Bool
    number_of_seeds = Int(1000)
    seed_density = Float(
        1.0,
        desc="Number of seeds to place along each direction. "
        "A density of 2 is the same as [2, 2, 2] and will result in a total of 8 seeds per voxel.",
    )
    fa_thresh = Float(0.2)
    step_size = traits.Float(0.5)
    max_angle = Float(25.0)
    sh_order = Int(8)

    use_act = traits.Bool(
        False,
        desc="Use FAST for partial volume estimation and Anatomically-Constrained Tractography (ACT) tissue classifier",
    )
    seed_from_gmwmi = traits.Bool(
        False,
        desc="Seed from Grey Matter / White Matter interface (requires Anatomically-Constrained Tractography (ACT))",
    )

    # fast_number_of_classes = Int(3)

    def _SD_changed(self, new):
        """Update ``curvature`` when ``SD`` is updated.

        Parameters
        ----------
        new
            New value of ``SD``
        """
        if self.tracking_mode == "Deterministic" and not new:
            self.curvature = 2.0
        elif self.tracking_mode == "Deterministic" and new:
            self.curvature = 0.0
        elif self.tracking_mode == "Probabilistic":
            self.curvature = 1.0

    def _tracking_mode_changed(self, new):
        """Update ``curvature``, ``use_act`` and ``seed_from_gmwmi`` when ``tracking_mode`` is updated.

        Parameters
        ----------
        new
            New value of ``tracking_mode``
        """
        if new == "Deterministic" and not self.SD:
            self.curvature = 2.0
            self.use_act = False
            self.seed_from_gmwmi = False
        elif new == "Deterministic" and self.SD:
            self.curvature = 0.0
            self.use_act = False
            self.seed_from_gmwmi = False
        elif new == "Probabilistic":
            self.curvature = 1.0

    def _curvature_changed(self, new):
        """Set ``curvature`` to 0 if ``curvature`` is updated to a value <= 0.000001.

        Parameters
        ----------
        new
            New value of ``curvature``
        """
        if new <= 0.000001:
            self.curvature = 0.0

    def _use_act_changed(self, new):
        """Set ``seed_from_gmwmi`` if ``use_act`` has been updated to `False`.

        Parameters
        ----------
        new
            New value of ``use_act``
        """
        if new is False:
            self.seed_from_gmwmi = False


class MRtrixTrackingConfig(HasTraits):
    """Class used to store Dipy diffusion reconstruction sub-workflow configuration parameters.

    Attributes
    ----------
    tracking_mode : traits.Str
        Type of local tractography algorithm
        (Can be "Deterministic" or "Probabilistic")

    SD : traits.Bool
        If `True`, inputs are coming from Constrained Spherical Deconvolution reconstruction

    desired_number_of_tracks : traits.Int
        Desired number of output streamlines in the tractogram
        (Default: 1M)

    curvature = Float
        Maximum streamline curvature
        (Default: 2.0)

    min_length = Float
        Minimal streamline length
        (Default: 5)

    max_length = Float
        Maximal streamline length
        (Default: 500)

    angle : traits.Float
        Maximum streamline angle allowed
        (Default: 45.0)

    cutoff_value : traits.Float
        Cut-off value to terminate streamline
        (Default: 0.05)

    use_act : traits.Bool
        Use `5ttgen` for brain tissue types estimation and Anatomically-Constrained Tractography (ACT) tissue classifier
        (Default: False)

    seed_from_gmwmi : traits.Bool
        Seed from Grey Matter / White Matter interface
        (requires Anatomically-Constrained Tractography (ACT))
        (Default: False)

    crop_at_gmwmi : traits.Bool
        Crop streamline endpoints more precisely as they cross the GM-WM interface
        (requires Anatomically-Constrained Tractography (ACT))
        (Default: True)

    backtrack : traits.Bool
        Allow tracks to be truncated (requires Anatomically-Constrained Tractography (ACT))
        (Default: True)

    sift : traits.Bool
        Filter tractogram using mrtrix3 SIFT
        (Default: True)
    """

    tracking_mode = Str
    SD = Bool
    desired_number_of_tracks = Int(1000000)
    # max_number_of_seeds = Int(1000000000)
    curvature = Float(2.0)
    step_size = Float(0.5)
    min_length = Float(5)
    max_length = Float(500)
    angle = Float(45)
    cutoff_value = Float(0.05)

    use_act = traits.Bool(
        True,
        desc="Anatomically-Constrained Tractography (ACT) based on Freesurfer parcellation",
    )
    seed_from_gmwmi = traits.Bool(
        False,
        desc="Seed from Grey Matter / White Matter interface (requires Anatomically-Constrained Tractography (ACT))",
    )
    crop_at_gmwmi = traits.Bool(
        True,
        desc="Crop streamline endpoints more precisely as they cross the GM-WM interface "
        "(requires Anatomically-Constrained Tractography (ACT))",
    )
    backtrack = traits.Bool(
        True,
        desc="Allow tracks to be truncated (requires Anatomically-Constrained Tractography (ACT))",
    )

    sift = traits.Bool(True, desc="Filter tractogram using mrtrix3 SIFT")

    def _SD_changed(self, new):
        """Update ``curvature`` when ``SD`` is updated.

        Parameters
        ----------
        new
            New value of ``SD``
        """
        if self.tracking_mode == "Deterministic" and not new:
            self.curvature = 2.0
        elif self.tracking_mode == "Deterministic" and new:
            self.curvature = 0.0
        elif self.tracking_mode == "Probabilistic":
            self.curvature = 1.0

    def _use_act_changed(self, new):
        if new is False:
            self.crop_at_gmwmi = False
            self.seed_from_gmwmi = False
            self.backtrack = False

    def _tracking_mode_changed(self, new):
        """Update ``curvature`` when ``tracking_mode`` is updated.

        Parameters
        ----------
        new
            New value of ``tracking_mode``
        """
        if new == "Deterministic" and not self.SD:
            self.curvature = 2.0
        elif new == "Deterministic" and self.SD:
            self.curvature = 0.0
        elif new == "Probabilistic":
            self.curvature = 1.0

    def _curvature_changed(self, new):
        """Set ``curvature`` to 0 if ``curvature`` is updated to a value <= 0.000001.

        Parameters
        ----------
        new
            New value of ``curvature``
        """
        if new <= 0.000001:
            self.curvature = 0.0


def create_dipy_tracking_flow(config):
    """Create the tractography sub-workflow of the `DiffusionStage` using Dipy.

    Parameters
    ----------
    config : DipyTrackingConfig
        Sub-workflow configuration object

    Returns
    -------
    flow : nipype.pipeline.engine.Workflow
        Built tractography sub-workflow
    """
    flow = pe.Workflow(name="tracking")
    # inputnode
    inputnode = pe.Node(
        interface=util.IdentityInterface(
            fields=[
                "DWI",
                "fod_file",
                "FA",
                "T1",
                "partial_volumes",
                "wm_mask_resampled",
                "gmwmi_file",
                "gm_registered",
                "bvals",
                "bvecs",
                "model",
            ]
        ),
        name="inputnode",
    )

    # outputnode
    outputnode = pe.Node(
        interface=util.IdentityInterface(fields=["track_file"]), name="outputnode"
    )

    if not config.SD and config.imaging_model != "DSI":  # If tensor fitting was used
        dipy_tracking = pe.Node(
            interface=TensorInformedEudXTractography(), name="dipy_dtieudx_tracking"
        )
        dipy_tracking.inputs.num_seeds = config.number_of_seeds
        dipy_tracking.inputs.fa_thresh = config.fa_thresh
        dipy_tracking.inputs.max_angle = config.max_angle
        dipy_tracking.inputs.step_size = config.step_size

        # fmt:off
        flow.connect(
            [
                (inputnode, dipy_tracking, [("wm_mask_resampled", "seed_mask")]),
                (inputnode, dipy_tracking, [("DWI", "in_file")]),
                (inputnode, dipy_tracking, [("model", "in_model")]),
                (inputnode, dipy_tracking, [("FA", "in_fa")]),
                (inputnode, dipy_tracking, [("wm_mask_resampled", "tracking_mask")]),
                (dipy_tracking, outputnode, [("tracks", "track_file")]),
            ]
        )
        # fmt:on

    else:  # If CSD was used
        if config.tracking_mode == "Deterministic":

            dipy_tracking = pe.Node(
                interface=DirectionGetterTractography(),
                name="dipy_deterministic_tracking",
            )
            dipy_tracking.inputs.algo = "deterministic"
            dipy_tracking.inputs.num_seeds = config.number_of_seeds
            dipy_tracking.inputs.fa_thresh = config.fa_thresh
            dipy_tracking.inputs.max_angle = config.max_angle
            dipy_tracking.inputs.step_size = config.step_size
            dipy_tracking.inputs.use_act = config.use_act
            dipy_tracking.inputs.use_act = config.seed_from_gmwmi
            dipy_tracking.inputs.seed_density = config.seed_density
            # dipy_tracking.inputs.fast_number_of_classes = config.fast_number_of_classes

            if config.imaging_model == "DSI":
                dipy_tracking.inputs.recon_model = "SHORE"
            else:
                dipy_tracking.inputs.recon_model = "CSD"
                dipy_tracking.inputs.recon_order = config.sh_order

            if config.imaging_model == "DSI":
                # fmt:off
                flow.connect(
                    [
                        (inputnode, dipy_tracking, [("fod_file", "fod_file")]),
                    ]
                )
                # fmt:on
            # fmt:off
            flow.connect(
                [
                    (inputnode, dipy_tracking, [("DWI", "in_file")]),
                    (inputnode, dipy_tracking, [("partial_volumes", "in_partial_volume_files")],),
                    (inputnode, dipy_tracking, [("model", "in_model")]),
                    (inputnode, dipy_tracking, [("FA", "in_fa")]),
                    (inputnode, dipy_tracking, [("wm_mask_resampled", "seed_mask")]),
                    (inputnode, dipy_tracking, [("gmwmi_file", "gmwmi_file")]),
                    (inputnode, dipy_tracking, [("wm_mask_resampled", "tracking_mask")],),
                    (dipy_tracking, outputnode, [("tracks", "track_file")]),
                ]
            )
            # fmt:on

        elif config.tracking_mode == "Probabilistic":

            dipy_tracking = pe.Node(
                interface=DirectionGetterTractography(),
                name="dipy_probabilistic_tracking",
            )
            dipy_tracking.inputs.algo = "probabilistic"
            dipy_tracking.inputs.num_seeds = config.number_of_seeds
            dipy_tracking.inputs.fa_thresh = config.fa_thresh
            dipy_tracking.inputs.max_angle = config.max_angle
            dipy_tracking.inputs.step_size = config.step_size
            dipy_tracking.inputs.use_act = config.use_act
            dipy_tracking.inputs.seed_from_gmwmi = config.seed_from_gmwmi
            dipy_tracking.inputs.seed_density = config.seed_density
            # dipy_tracking.inputs.fast_number_of_classes = config.fast_number_of_classes

            if config.imaging_model == "DSI":
                dipy_tracking.inputs.recon_model = "SHORE"
            else:
                dipy_tracking.inputs.recon_model = "CSD"
                dipy_tracking.inputs.recon_order = config.sh_order

            if config.imaging_model == "DSI":
                # fmt:off
                flow.connect(
                    [
                        (inputnode, dipy_tracking, [("fod_file", "fod_file")]),
                    ]
                )
                # fmt:on
            # fmt:off
            flow.connect(
                [
                    (inputnode, dipy_tracking, [("DWI", "in_file")]),
                    (inputnode, dipy_tracking, [("partial_volumes", "in_partial_volume_files")]),
                    (inputnode, dipy_tracking, [("model", "in_model")]),
                    (inputnode, dipy_tracking, [("FA", "in_fa")]),
                    (inputnode, dipy_tracking, [("wm_mask_resampled", "seed_mask")]),
                    (inputnode, dipy_tracking, [("gmwmi_file", "gmwmi_file")]),
                    (inputnode, dipy_tracking, [("wm_mask_resampled", "tracking_mask")]),
                    (dipy_tracking, outputnode, [("tracks", "track_file")]),
                ]
            )
            # fmt:on

    return flow


def get_freesurfer_parcellation(roi_files):
    """Return the first file in the list of parcellation files

    Parameters
    ----------
    roi_files : list of traits.File
        List of parcellation files
    """
    print("%s" % roi_files[0])
    return roi_files[0]


def create_mrtrix_tracking_flow(config):
    """Create the tractography sub-workflow of the `DiffusionStage` using MRtrix3.

    Parameters
    ----------
    config : MRtrixTrackingConfig
        Sub-workflow configuration object

    Returns
    -------
    flow : nipype.pipeline.engine.Workflow
        Built tractography sub-workflow
    """
    flow = pe.Workflow(name="tracking")
    # inputnode
    inputnode = pe.Node(
        interface=util.IdentityInterface(
            fields=[
                "DWI",
                "wm_mask_resampled",
                "gm_registered",
                "act_5tt_registered",
                "gmwmi_registered",
                "grad",
            ]
        ),
        name="inputnode",
    )

    # outputnode
    outputnode = pe.Node(
        interface=util.IdentityInterface(fields=["track_file"]), name="outputnode"
    )

    # Compute single fiber voxel mask
    wm_erode = pe.Node(
        interface=Erode(out_filename="wm_mask_resampled.nii.gz"), name="wm_erode"
    )
    wm_erode.inputs.number_of_passes = 3
    wm_erode.inputs.filtertype = "erode"

    flow.connect([(inputnode, wm_erode, [("wm_mask_resampled", "in_file")])])

    if config.tracking_mode == "Deterministic":
        mrtrix_tracking = pe.Node(
            interface=StreamlineTrack(), name="mrtrix_deterministic_tracking"
        )
        mrtrix_tracking.inputs.desired_number_of_tracks = (
            config.desired_number_of_tracks
        )
        # mrtrix_tracking.inputs.maximum_number_of_seeds = config.max_number_of_seeds
        mrtrix_tracking.inputs.maximum_tract_length = config.max_length
        mrtrix_tracking.inputs.minimum_tract_length = config.min_length
        mrtrix_tracking.inputs.step_size = config.step_size
        mrtrix_tracking.inputs.angle = config.angle
        mrtrix_tracking.inputs.cutoff_value = config.cutoff_value

        # mrtrix_tracking.inputs.args = '2>/dev/null'
        if config.curvature >= 0.000001:
            mrtrix_tracking.inputs.rk4 = True
            mrtrix_tracking.inputs.inputmodel = "SD_Stream"
        else:
            mrtrix_tracking.inputs.inputmodel = "SD_Stream"
        # fmt:off
        flow.connect(
            [(inputnode, mrtrix_tracking, [("grad", "gradient_encoding_file")])]
        )
        # fmt:on

        voxel2WorldMatrixExtracter = pe.Node(
            interface=ExtractHeaderVoxel2WorldMatrix(),
            name="voxel2WorldMatrixExtracter",
        )

        # fmt:off
        flow.connect(
            [
                (inputnode, voxel2WorldMatrixExtracter, [("wm_mask_resampled", "in_file")],)
            ]
        )
        # fmt:on

        if config.use_act:
            # fmt:off
            flow.connect(
                [
                    (inputnode, mrtrix_tracking, [("act_5tt_registered", "act_file")]),
                ]
            )
            # fmt:on
            mrtrix_tracking.inputs.backtrack = config.backtrack
            mrtrix_tracking.inputs.crop_at_gmwmi = config.crop_at_gmwmi
        else:
            # fmt:off
            flow.connect(
                [
                    (inputnode, mrtrix_tracking, [("wm_mask_resampled", "mask_file")]),
                ]
            )
            # fmt:on

        if config.seed_from_gmwmi:
            # fmt:off
            flow.connect(
                [
                    (inputnode, mrtrix_tracking, [("gmwmi_registered", "seed_gmwmi")]),
                ]
            )
            # fmt:on
        else:
            # fmt:off
            flow.connect(
                [
                    (inputnode, mrtrix_tracking, [("wm_mask_resampled", "seed_file")]),
                ]
            )
            # fmt:on

        # converter = pe.Node(interface=mrtrix.MRTrix2TrackVis(),name="trackvis")
        converter = pe.Node(interface=Tck2Trk(), name="trackvis")
        converter.inputs.out_tracks = "converted.trk"

        if config.sift:

            filter_tractogram = pe.Node(interface=FilterTractogram(), name="sift_node")
            filter_tractogram.inputs.out_file = "sift-filtered_tractogram.tck"
            # fmt:off
            flow.connect(
                [
                    (mrtrix_tracking, filter_tractogram, [("tracked", "in_tracks")]),
                    (inputnode, filter_tractogram, [("DWI", "in_fod")]),
                ]
            )
            # fmt:on
            if config.use_act:
                # fmt:off
                flow.connect(
                    [
                        (inputnode, filter_tractogram, [("act_5tt_registered", "act_file")],),
                    ]
                )
                # fmt:on
            # fmt:off
            flow.connect(
                [(filter_tractogram, converter, [("out_tracks", "in_tracks")])]
            )
            # fmt:on
        else:
            # fmt:off
            flow.connect(
                [
                    (mrtrix_tracking, converter, [("tracked", "in_tracks")]),
                ]
            )
            # fmt:on
        # fmt:off
        flow.connect(
            [
                (inputnode, mrtrix_tracking, [("DWI", "in_file")]),
                (inputnode, converter, [("wm_mask_resampled", "in_image")]),
                (converter, outputnode, [("out_tracks", "track_file")]),
            ]
        )
        # fmt:on

    elif config.tracking_mode == "Probabilistic":
        mrtrix_tracking = pe.Node(
            interface=StreamlineTrack(), name="mrtrix_probabilistic_tracking"
        )
        mrtrix_tracking.inputs.desired_number_of_tracks = (
            config.desired_number_of_tracks
        )
        # mrtrix_tracking.inputs.maximum_number_of_seeds = config.max_number_of_seeds
        mrtrix_tracking.inputs.maximum_tract_length = config.max_length
        mrtrix_tracking.inputs.minimum_tract_length = config.min_length
        mrtrix_tracking.inputs.step_size = config.step_size
        mrtrix_tracking.inputs.angle = config.angle
        mrtrix_tracking.inputs.cutoff_value = config.cutoff_value
        # mrtrix_tracking.inputs.args = '2>/dev/null'
        # if config.curvature >= 0.000001:
        #    mrtrix_tracking.inputs.rk4 = True
        if config.SD:
            mrtrix_tracking.inputs.inputmodel = "iFOD2"
        else:
            mrtrix_tracking.inputs.inputmodel = "Tensor_Prob"

        converter = pe.Node(interface=Tck2Trk(), name="trackvis")
        converter.inputs.out_tracks = "converted.trk"

        if config.use_act:
            # fmt:off
            flow.connect(
                [
                    (inputnode, mrtrix_tracking, [("act_5tt_registered", "act_file")]),
                ]
            )
            # fmt:on
            mrtrix_tracking.inputs.backtrack = config.backtrack
            mrtrix_tracking.inputs.crop_at_gmwmi = config.crop_at_gmwmi
        else:
            # fmt:off
            flow.connect(
                [
                    (inputnode, mrtrix_tracking, [("wm_mask_resampled", "mask_file")]),
                ]
            )
            # fmt:on

        if config.seed_from_gmwmi:
            # fmt:off
            flow.connect(
                [
                    (inputnode, mrtrix_tracking, [("gmwmi_registered", "seed_gmwmi")]),
                ]
            )
            # fmt:on
        else:
            # fmt:off
            flow.connect(
                [
                    (inputnode, mrtrix_tracking, [("wm_mask_resampled", "seed_file")]),
                ]
            )
            # fmt:on

        if config.sift:

            filter_tractogram = pe.Node(interface=FilterTractogram(), name="sift_node")
            filter_tractogram.inputs.out_file = "sift-filtered_tractogram.tck"
            # fmt:off
            flow.connect(
                [
                    (mrtrix_tracking, filter_tractogram, [("tracked", "in_tracks")]),
                    (inputnode, filter_tractogram, [("DWI", "in_fod")]),
                ]
            )
            # fmt:on
            if config.use_act:
                # fmt:off
                flow.connect(
                    [
                        (inputnode, filter_tractogram, [("act_5tt_registered", "act_file")],),
                    ]
                )
                # fmt:on
            # fmt:off
            flow.connect(
                [(filter_tractogram, converter, [("out_tracks", "in_tracks")])]
            )
            # fmt:on
        else:
            # fmt:off
            flow.connect(
                [
                    (mrtrix_tracking, converter, [("tracked", "in_tracks")]),
                ]
            )
            # fmt:on

        # fmt:off
        flow.connect(
            [
                (inputnode, mrtrix_tracking, [("DWI", "in_file")]),
                (inputnode, converter, [("wm_mask_resampled", "in_image")]),
                (converter, outputnode, [("out_tracks", "track_file")]),
            ]
        )
        # fmt:on

    return flow
