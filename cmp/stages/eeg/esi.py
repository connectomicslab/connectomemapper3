# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""Definition of config and stage classes for computing brain parcellation."""

# General imports
import os
from traits.api import (
    HasTraits, Enum, Instance, Bool, Float
)

# Nipype imports
import nipype.pipeline.engine as pe

# Own imports
from cmp.stages.common import Stage
from cmtklib.bids.io import (
    CustomEEGMNETransformBIDSFile, CustomEEGCartoolSpiBIDSFile,
    CustomEEGCartoolInvSolBIDSFile, __freesurfer_directory__
)
from cmtklib.interfaces.pycartool import (
    CreateSpiRoisMapping, CartoolInverseSolutionROIExtraction
)
from cmtklib.interfaces.mne import (
    CreateBEM, CreateSrc,
    CreateCov, CreateFwd,
    MNEInverseSolutionROI
)


class EEGSourceImagingConfig(HasTraits):
    """Class used to store configuration parameters of a :class:`~cmp.stages.eeg.esi.EEGSourceImagingStage` instance.

    Attributes
    ----------
    esi_tool : Enum
        Select the tool used for EEG source imaging (inverse solution)

    mne_apply_electrode_transform : Bool
        If `True`, apply the transform specified below to electrode positions

    mne_electrode_transform_file : CustomEEGMNETransformBIDSFile
        Instance of :obj:`~cmtklib.bids.io.CustomEEGCartoolMNETransformBIDSFile`
        that describes the input BIDS-formatted MNE transform file in fif format

    cartool_spi_file : CustomEEGCartoolSpiBIDSFile
        Instance of :obj:`~cmtklib.bids.io.CustomEEGCartoolSpiBIDSFile`
        that describes the input BIDS-formatted EEG Solution Points Irregularly spaced
        file created by Cartool

    cartool_invsol_file : CustomEEGCartoolInvSolBIDSFile
        Instance of :obj:`~cmtklib.bids.io.CustomEEGCartoolInvSolBIDSFile`
        that describes the input BIDS-formatted EEG Inverse Solution
        file created by Cartool

    cartool_esi_method : Enum(['LAURA', 'LORETA'])
        Cartool Source Imaging method

    parcellation_scheme : Enum(["NativeFreeSurfer", "Lausanne2018"])
        Parcellation used to create the ROI source time-series

    lausanne2018_parcellation_res : Enum(["scale1", "scale2", "scale3", "scale4", "scale5"])
        Resolution of the parcellation if Lausanne2018 parcellation scheme is used

    cartool_esi_lamb : Float
        Regularization weight of inverse solutions computed with Cartool
        (Default: 6)

    cartool_svd_toi_begin : Float
        Start TOI for SVD projection
        (Default: 0.0)

    cartool_svd_toi_end : Float
        End TOI for SVD projection
        (Default: 0.25)

    mne_esi_method : Enum(["sLORETA", "eLORETA", "MNE", "dSPM"])
        MNE Source Imaging method

    mne_esi_method_snr : Float
        SNR value such as the regularization weight lambda2 of MNE ESI method'
        is set to  `1.0 / mne_esi_method_snr ** 2`
        (Default: 3.0)

    See Also
    --------
    cmp.stages.eeg.esi.EEGSourceImagingStage
    """
    esi_tool = Enum(
        "MNE", "Cartool",
        desc="Select the tool used for EEG source imaging (inverse solution)"
    )

    mne_apply_electrode_transform = Bool(
        False,
        desc="If `True`, apply the transform specified below to electrode positions"
    )
    mne_electrode_transform_file = Instance(
        CustomEEGMNETransformBIDSFile, (),
        desc="Instance of :obj:`~cmtklib.bids.io.CustomEEGCartoolMNETransformBIDSFile`"
             "that describes the input BIDS-formatted MNE transform file in fif format"
    )

    cartool_spi_file = Instance(
        CustomEEGCartoolSpiBIDSFile, (),
        desc="Instance of :obj:`~cmtklib.bids.io.CustomEEGCartoolSpiBIDSFile`"
             "that describes the input BIDS-formatted EEG Solution Points Irregularly spaced "
             "file created by Cartool"
    )
    cartool_invsol_file = Instance(
        CustomEEGCartoolInvSolBIDSFile, (),
        desc="Instance of :obj:`~cmtklib.bids.io.CustomEEGCartoolInvSolBIDSFile`"
             "that describes the input BIDS-formatted EEG Inverse Solution "
             "file created by Cartool"
    )
    cartool_esi_method = Enum(['LAURA', 'LORETA'], desc="Cartool Source Imaging method")

    parcellation_scheme = Enum(
        "NativeFreeSurfer", "Lausanne2018",
        desc="Parcellation used to create the ROI source time-series"
    )
    lausanne2018_parcellation_res = Enum(
        "scale1", "scale2", "scale3", "scale4", "scale5",
        desc="Resolution of the parcellation if Lausanne2018 "
             "parcellation scheme is used "
    )

    cartool_esi_lamb = Float(6, desc='Regularization weight')
    cartool_svd_toi_begin = Float(0, desc='Start TOI for SVD projection')
    cartool_svd_toi_end = Float(0.25, desc='End TOI for SVD projection')

    mne_esi_method = Enum(["sLORETA", "eLORETA", "MNE", "dSPM"], desc="MNE Source Imaging method" )
    mne_esi_method_snr = Float(
        3.0, desc='SNR value such as the ESI method regularization weight lambda2 '
                  'is set to  `1.0 / mne_esi_method_snr ** 2`'
    )

    def _cartool_esi_method_changed(self, new):
        self.cartool_invsol_file.esi_method = new

    def __str__(self):
        str_repr = '\tEEGSourceImagingConfig:\n'
        str_repr += f'\t\t* esi_tool: {self.esi_tool}\n'
        str_repr += f'\t\t* mne_apply_electrode_transform: {self.mne_apply_electrode_transform}\n'
        str_repr += f'\t\t* mne_electrode_transform_file: {self.mne_electrode_transform_file}\n'
        str_repr += f'\t\t* cartool_spi_file: {self.cartool_spi_file}\n'
        str_repr += f'\t\t* cartool_invsol_file: {self.cartool_invsol_file}\n'
        str_repr += f'\t\t* cartool_esi_method: {self.cartool_esi_method}\n'
        str_repr += f'\t\t* parcellation_scheme: {self.parcellation_scheme}\n'
        str_repr += f'\t\t* lausanne2018_parcellation_res: {self.lausanne2018_parcellation_res}\n'
        str_repr += f'\t\t* cartool_esi_lamb: {self.cartool_esi_lamb}\n'
        str_repr += f'\t\t* cartool_svd_toi_begin: {self.cartool_svd_toi_begin}\n'
        str_repr += f'\t\t* cartool_svd_toi_end: {self.cartool_svd_toi_end}\n'
        str_repr += f'\t\t* mne_esi_method: {self.mne_esi_method}\n'
        str_repr += f'\t\t* mne_esi_method_snr: {self.mne_esi_method_snr}\n'
        return str_repr


class EEGSourceImagingStage(Stage):
    """Class that represents the reconstruction of the inverse solutions stage of a :class:`~cmp.pipelines.functional.eeg.EEGPipeline`.

    If MNE is selected for ESI reconstruction, this stage consists of five processing interfaces:

        - :class:`~cmtklib.interfaces.mne.CreateBem`: Create the Boundary Element Model that consists of surfaces obtained with Freesurfer.
        - :class:`~cmtklib.interfaces.mne.CreateSrc`: Create a bilateral hemisphere surface-based source space file with subsampling.
        - :class:`~cmtklib.interfaces.mne.CreateFwd`: Create the forward solution (leadfield) from the BEM and the source space.
        - :class:`~cmtklib.interfaces.mne.CreateCov`: Create the noise covariance matrix from the data.
        - :class:`~cmtklib.interfaces.mne.MNEInverseSolutionROI`: Create and apply the actual inverse operator to generate
          the ROI time courses.

    If you decide to use ESI reconstruction outputs precomputed with Cartool,
    then this stage consists of two processing interfaces:

        - :class:`~cmtklib.interfaces.eeg.CreateSpiRoisMapping`: Create Cartool-reconstructed sources / parcellation ROI mapping file.
        - :class:`~cmtklib.interfaces.pycartool.CartoolInverseSolutionROIExtraction`: Use Pycartool to load inverse solutions
          estimated by Cartool and generate the ROI time courses.


    Methods
    -------
    create_workflow()
        Create the main workflow of the `EEGSourceImagingStage`

    create_cartool_workflow()
        Create the Cartool workflow of the `EEGSourceImagingStage`

    create_mne_workflow()
        Create the MNE workflow of the `EEGSourceImagingStage`

    See Also
    --------
    cmp.pipelines.functional.eeg.EEGPipeline
    cmp.stages.eeg.esi.EEGSourceImagingConfig
    """

    def __init__(self, subject, session, bids_dir, output_dir):
        """Constructor of a :class:`~cmp.stages.eeg.esi.EEGSourceImagingStage` instance."""
        self.name = "eeg_source_imaging_stage"
        self.bids_subject_label = subject
        self.bids_session_label = session
        self.bids_dir = bids_dir
        self.output_dir = output_dir
        self.fs_subjects_dir = os.path.join(
            bids_dir, 'derivatives', f'{__freesurfer_directory__}'
        )
        self.fs_subject = (subject
                           if session == "" or session is None
                           else '_'.join([subject, session]))
        self.config = EEGSourceImagingConfig()
        self.inputs = [
            "epochs_file",
            "spi_file",
            "invsol_file",
            "trans_file",
            "roi_volume_file",
        ]
        self.outputs = [
            "bem_file",
            "noise_cov_file",
            "fwd_file",
            "src_file",
            "inv_file",
            "roi_ts_file",
            "mapping_spi_rois_file"
        ]

    def create_workflow(self, flow, inputnode, outputnode):
        """Create the stage workflow.

        Parameters
        ----------
        flow : nipype.pipeline.engine.Workflow
            The nipype.pipeline.engine.Workflow instance of the Diffusion pipeline

        inputnode : nipype.interfaces.utility.IdentityInterface
            Identity interface describing the inputs of the stage

        outputnode : nipype.interfaces.utility.IdentityInterface
            Identity interface describing the outputs of the stage
        """
        if self.config.esi_tool == "Cartool":
            self.create_cartool_workflow(flow, inputnode, outputnode)
        else:
            self.create_mne_workflow(flow, inputnode, outputnode)

    def create_cartool_workflow(self, flow, inputnode, outputnode):
        """Create the stage workflow.

        Parameters
        ----------
        flow : nipype.pipeline.engine.Workflow
            The nipype.pipeline.engine.Workflow instance of the Diffusion pipeline

        inputnode : nipype.interfaces.utility.IdentityInterface
            Identity interface describing the inputs of the stage

        outputnode : nipype.interfaces.utility.IdentityInterface
            Identity interface describing the outputs of the stage
        """
        mapping_spi_rois_node = pe.Node(
            CreateSpiRoisMapping(out_mapping_spi_rois_fname="eeg.pickle.rois"),
            name="cartool_createrois"
        )
        # fmt: off
        invsol_node = pe.Node(
            interface=CartoolInverseSolutionROIExtraction(
                out_roi_ts_fname="timeseries.npy",
                lam=self.config.eeg_cartool_esi_lamb,
                svd_toi_begin=self.config.eeg_cartool_svd_toi_begin,
                svd_toi_end=self.config.eeg_cartool_svd_toi_end
            ),
            name="cartool_invsol"
        )
        # Connect stage nodes
        # fmt: off
        flow.connect(
            [
                (inputnode, mapping_spi_rois_node, [('spi_file', 'spi_file'),
                                                    ('roi_volume_file', 'roi_volume_file')]),
                (inputnode, invsol_node, [("epochs_file", "epochs_file"),
                                          ("invsol_file", "invsol_file")]),
                (mapping_spi_rois_node, invsol_node, [("mapping_spi_rois_file", "mapping_spi_rois_file")])
            ]
        )
        # Connect outputs to stage outputnode
        # fmt: off
        flow.connect(
            [
                (mapping_spi_rois_node, outputnode, [("mapping_spi_rois_file", "mapping_spi_rois_file")]),
                (invsol_node, outputnode, [("roi_ts_file", "roi_ts_file")])
            ]
        )
        # fmt: on

    def create_mne_workflow(self, flow, inputnode, outputnode):
        """Create the stage workflow.

        Parameters
        ----------
        flow : nipype.pipeline.engine.Workflow
            The nipype.pipeline.engine.Workflow instance of the Diffusion pipeline

        inputnode : nipype.interfaces.utility.IdentityInterface
            Identity interface describing the inputs of the stage

        outputnode : nipype.interfaces.utility.IdentityInterface
            Identity interface describing the outputs of the stage
        """
        # Compute the BEM
        bem_node = pe.Node(
            interface=CreateBEM(
                fs_subject=self.fs_subject,
                fs_subjects_dir=self.fs_subjects_dir,
                out_bem_fname='bem.fif'
            ),
            name="mne_createbem"
        )
        # Compute the source space
        src_node = pe.Node(
            interface=CreateSrc(
                fs_subject=self.fs_subject,
                fs_subjects_dir=self.fs_subjects_dir,
                out_src_fname='src.fif'
            ),
            name="mne_createsrc"
        )
        # Compute the noise covariance
        covmat_node = pe.Node(
            interface=CreateCov(
                out_noise_cov_fname='noisecov.fif'
            ),
            name="mne_createcov"
        )
        # Compute the forward solution
        fwd_node = pe.Node(
            interface=CreateFwd(
                out_fwd_fname='fwd.fif'
            ),
            name="mne_createfwd"
        )
        # Compute the inverse solutions and extract the ROI time courses
        invsol_node = pe.Node(
            interface=MNEInverseSolutionROI(
                fs_subject=self.fs_subject,
                fs_subjects_dir=self.fs_subjects_dir,
                out_roi_ts_fname="timeseries.pickle",
                out_inv_fname="inv.fif",
                parc_annot=(f'lausanne2018.{self.config.lausanne2018_parcellation_res}'
                            if self.config.parcellation_scheme == "Lausanne2018"
                            else 'aparc'),
                esi_method=self.config.mne_esi_method,
                esi_method_snr=self.config.mne_esi_method_snr
            ),
            name="mne_invsol"
        )

        # Connect stage nodes
        # fmt: off
        flow.connect(
            [
                (inputnode, covmat_node, [("epochs_file", "epochs_file")]),
                (inputnode, fwd_node, [("trans_file", "trans_file"),
                                       ("epochs_file", "epochs_file")]),
                (bem_node, fwd_node, [("bem_file", "bem_file")]),
                (src_node, fwd_node, [("src_file", "src_file")]),
                (inputnode, invsol_node, [("epochs_file", "epochs_file")]),
                (bem_node, invsol_node, [("bem_file", "bem_file")]),
                (src_node, invsol_node, [("src_file", "src_file")]),
                (fwd_node, invsol_node, [("fwd_file", "fwd_file")]),
                (covmat_node, invsol_node, [("noise_cov_file", "noise_cov_file")]),
            ]
        )
        # fmt: on

        # Connect outputs to stage outputnode
        # fmt: off
        flow.connect(
            [
                (bem_node, outputnode, [("bem_file", "bem_file")]),
                (src_node, outputnode, [("src_file", "src_file")]),
                (covmat_node, outputnode, [("noise_cov_file", "noise_cov_file")]),
                (fwd_node, outputnode, [("fwd_file", "fwd_file")]),
                (invsol_node, outputnode, [("roi_ts_file", "roi_ts_file"),
                                           ("inv_file", "inv_file")])
            ]
        )
        # fmt: on

    def define_inspect_outputs(self):
        raise NotImplementedError

    def has_run(self):
        """Function that returns `True` if the stage has been run successfully.

        Returns
        -------
        `True` if the stage has been run successfully
        """
        return True
        # if self.config.eeg_format == ".set":
        #     if self.config.invsol_format.split("-")[0] == "Cartool":
        #         return os.path.exists(self.config.roi_ts_file)