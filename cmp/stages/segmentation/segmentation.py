# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""Definition of config and stage classes for segmentation."""

# General imports
import os
from glob import glob
from traits.api import *
import pkg_resources

# Nipype imports
import nipype.pipeline.engine as pe
import nipype.interfaces.freesurfer as fs
import nipype.interfaces.fsl as fsl
import nipype.interfaces.ants as ants
from nipype.interfaces.io import FreeSurferSource
import nipype.interfaces.utility as util
from nipype.interfaces.io import BIDSDataGrabber

# Own imports
from cmtklib.bids.io import __cmp_directory__, __freesurfer_directory__
from cmp.stages.common import Stage
from cmtklib.interfaces.freesurfer import copyBrainMaskToFreesurfer
from cmtklib.util import (
    isavailable,
    extract_freesurfer_subject_dir,
    extract_reconall_base_dir,
    get_freesurfer_subject_id
)
from cmtklib.bids.utils import (
    get_native_space_files,
    get_native_space_no_desc_files
)
from cmtklib.bids.io import (
    CustomBrainMaskBIDSFile,
    CustomWMMaskBIDSFile,
    CustomGMMaskBIDSFile,
    CustomCSFMaskBIDSFile,
    CustomAparcAsegBIDSFile
)


class SegmentationConfig(HasTraits):
    """Class used to store configuration parameters of a :class:`~cmp.stages.segmentation.segmentation.SegmentationStage` object.

    Attributes
    ----------
    seg_tool : traits.Enum(["Freesurfer", "Custom segmentation"])
        Choice of segmentation tool that can be
        "Freesurfer"

    make_isotropic : traits.Bool
        Resample to isotropic resolution
        (Default: False)

    isotropic_vox_size : traits.Float
        Isotropic resolution to be resampled
        (Default: 1.2, desc='')

    isotropic_interpolation : traits.Enum
        Interpolation type used for resampling that can be:
        'cubic', 'weighted', 'nearest', 'sinc', or 'interpolate',
        (Default: 'cubic')

    brain_mask_extraction_tool : traits.Enum
        Choice of brain extraction tool: "Freesurfer", "BET", or "ANTs"
        (Default: Freesurfer)

    ants_templatefile : traits.File
        Anatomical template used by ANTS brain extraction

    ants_probmaskfile : traits.File
        Brain probability mask used by ANTS brain extraction

    ants_regmaskfile : traits.File
        Mask (defined in the template space) used during registration in ANTs brain extraction.
        To limit the metric computation to a specific region.

    use_fsl_brain_mask : traits.Bool
        Use FSL BET for brain extraction
        (Default: False)

    use_existing_freesurfer_data : traits.Bool
        (Default: False)

    freesurfer_subjects_dir : traits.Str
        Freesurfer subjects directory path
        usually ``/output_dir/freesurfer``

    freesurfer_subject_id : traits.Str
        Freesurfer subject (being processed) ID in the form
        ``sub-XX(_ses-YY)``

    freesurfer_args : traits.Str
        Extra Freesurfer ``recon-all`` arguments

    custom_brainmask : traits.Instance(CustomBrainMaskBIDSFile)
        Instance of :obj:`~cmtklib.bids.io.CustomBrainMaskBIDSFile`
        that describes the custom BIDS formatted brain mask

    custom_wm_mask : traits.Instance(CustomWMMaskBIDSFile)
        Instance of :obj:`~cmtklib.bids.io.CustomWMMaskBIDSFile`
        that describes the custom BIDS formatted white-matter mask

    custom_gm_mask : traits.Instance(CustomGMMaskBIDSFile)
        Instance of :obj:`~cmtklib.bids.io.CustomGMMaskBIDSFile`
        that describes the custom BIDS formatted gray-matter mask

    custom_csf_mask : traits.Instance(CustomCSFMaskBIDSFile)
        Instance of :obj:`~cmtklib.bids.io.CustomCSFMaskBIDSFile`
        that describes the custom BIDS formatted CSF mask

    custom_aparcaseg : traits.Instance(CustomAparcAsegBIDSFile)
        Instance of :obj:`~cmtklib.bids.io.CustomAparcAsegBIDSFile`
        that describes the custom BIDS formatted Freesurfer aparc-aseg file

    number_of_threads : traits.Int
        Number of threads leveraged by OpenMP and used in
        the stage by Freesurfer and ANTs
        (Default: 1)

    See Also
    --------
    cmp.stages.segmentation.segmentation.SegmentationStage
    cmtklib.bids.io.CustomBrainMaskBIDSFile
    cmtklib.bids.io.CustomWMMaskBIDSFile
    cmtklib.bids.io.CustomGMMaskBIDSFile
    cmtklib.bids.io.CustomCSFMaskBIDSFile
    """

    seg_tool = Enum(["Freesurfer", "Custom segmentation"])
    make_isotropic = Bool(False)
    isotropic_vox_size = Float(1.2, desc="specify the size (mm)")
    isotropic_interpolation = Enum(
        "cubic",
        "weighted",
        "nearest",
        "sinc",
        "interpolate",
        desc="<interpolate|weighted|nearest|sinc|cubic> (default is cubic)",
    )
    brain_mask_extraction_tool = Enum("Freesurfer", ["Freesurfer", "BET", "ANTs"])
    ants_templatefile = File(desc="Anatomical template")
    ants_probmaskfile = File(desc="Brain probability mask")
    ants_regmaskfile = File(
        desc="Mask (defined in the template space) used during registration " +
             "for brain extraction.To limit the metric computation to a specific region."
    )

    use_fsl_brain_mask = Bool(False)

    use_existing_freesurfer_data = Bool(False)
    freesurfer_subjects_dir = Str
    freesurfer_subject_id = Str
    freesurfer_args = Str("")

    custom_brainmask = Instance(CustomBrainMaskBIDSFile , (),
                                desc="Instance of :obj:`~cmtklib.bids.io.CustomBrainMaskBIDSFile` "
                                     "that describes the custom BIDS formatted brain mask")

    custom_wm_mask = Instance(CustomWMMaskBIDSFile , (),
                              desc="Instance of :obj:`~cmtklib.bids.io.CustomWMMaskBIDSFile` "
                                   "that describes the custom BIDS formatted white-matter mask")

    custom_gm_mask = Instance(CustomGMMaskBIDSFile, (),
                              desc="Instance of :obj:`~cmtklib.bids.io.CustomGMMaskBIDSFile` "
                                   "that describes the custom BIDS formatted gray-matter mask")

    custom_csf_mask = Instance(CustomCSFMaskBIDSFile, (),
                               desc="Instance of :obj:`~cmtklib.bids.io.CustomCSFMaskBIDSFile` "
                                    "that describes the custom BIDS formatted CSF mask")

    custom_aparcaseg = Instance(CustomAparcAsegBIDSFile, (),
                                desc="Instance of :obj:`~cmtklib.bids.io.CustomAparcAsegBIDSFile`"
                                     "that describes the custom BIDS-formatted Freesurfer aparc+aseg file")

    number_of_threads = Int(1, desc="Number of threads used in the stage by Freesurfer and ANTs")


class SegmentationStage(Stage):
    """Class that represents the segmentation stage of a :class:`~cmp.pipelines.anatomical.anatomical.AnatomicalPipeline`.

    Methods
    -------
    create_workflow()
        Create the workflow of the `SegmentationStage`

    See Also
    --------
    cmp.pipelines.anatomical.anatomical.AnatomicalPipeline
    cmp.stages.segmentation.segmentation.SegmentationConfig
    """

    # General and UI members
    def __init__(self, subject, session, bids_dir, output_dir):
        """Constructor of a :class:`~cmp.stages.segmentation.segmentation.SegmentationStage` instance."""
        self.name = "segmentation_stage"
        self.bids_subject_label = subject
        self.bids_session_label = session
        self.bids_dir = bids_dir
        self.output_dir = output_dir
        self.config = SegmentationConfig()
        self.config.freesurfer_subjects_dir = os.path.join('/output_dir', f'{__freesurfer_directory__}')
        fs_subject_dir = (subject
                          if session == "" or session is None
                          else '_'.join([subject, session]))
        self.config.freesurfer_subject_id = os.path.join(
            self.config.freesurfer_subjects_dir, fs_subject_dir
        )
        self.config.ants_templatefile = pkg_resources.resource_filename(
            "cmtklib",
            os.path.join(
                "data",
                "segmentation",
                "ants_template_IXI",
                "T_template2_BrainCerebellum.nii.gz",
            ),
        )
        self.config.ants_probmaskfile = pkg_resources.resource_filename(
            "cmtklib",
            os.path.join(
                "data",
                "segmentation",
                "ants_template_IXI",
                "T_template_BrainCerebellumProbabilityMask.nii.gz",
            ),
        )
        self.config.ants_regmaskfile = pkg_resources.resource_filename(
            "cmtklib",
            os.path.join(
                "data",
                "segmentation",
                "ants_template_IXI",
                "T_template_BrainCerebellumMask.nii.gz",
            ),
        )
        self.inputs = ["T1", "brain_mask"]
        self.outputs = [
            "subjects_dir",
            "subject_id",
            "brain_mask",
            "brain",
            "custom_brain_mask",
            "custom_wm_mask",
            "custom_gm_mask",
            "custom_csf_mask",
            "custom_aparcaseg",
        ]

    def create_workflow(self, flow, inputnode, outputnode):
        """Create the stage workflow.

        Parameters
        ----------
        flow : nipype.pipeline.engine.Workflow
            The nipype.pipeline.engine.Workflow instance of the anatomical pipeline

        inputnode : nipype.interfaces.utility.IdentityInterface
            Identity interface describing the inputs of the segmentation stage

        outputnode : nipype.interfaces.utility.IdentityInterface
            Identity interface describing the outputs of the segmentation stage
        """
        if self.config.seg_tool == "Freesurfer":

            def correct_freesurfer_subjectid_path(path):
                if '/output_dir' not in path:
                    subject_id = path.split(f"{__freesurfer_directory__}/")[-1]
                    path = os.path.abspath(f'/output_dir/{__freesurfer_directory__}/{subject_id}')
                return path

            def correct_freesurfer_subjects_path(path):
                if '/output_dir' not in path:
                    path = os.path.abspath(f'/output_dir/{__freesurfer_directory__}')
                return path

            orig_dir = os.path.join(
                correct_freesurfer_subjectid_path(self.config.freesurfer_subject_id), "mri", "orig"
            )
            print(f'INFO : orig_dir = {orig_dir}')
            # Skip Freesurfer recon-all if 001.mgz exists which typically means it has been already run
            self.config.use_existing_freesurfer_data = True if os.path.exists(orig_dir) else False
            print(f'INFO : orig_dir exists? {self.config.use_existing_freesurfer_data}')

            if self.config.use_existing_freesurfer_data is False:
                # Converting to .mgz format
                fs_mriconvert = pe.Node(
                    interface=fs.MRIConvert(out_type="mgz", out_file="T1.mgz"),
                    name="mgzConvert",
                )

                if self.config.make_isotropic:
                    fs_mriconvert.inputs.vox_size = (
                        self.config.isotropic_vox_size,
                        self.config.isotropic_vox_size,
                        self.config.isotropic_vox_size,
                    )
                    fs_mriconvert.inputs.resample_type = (
                        self.config.isotropic_interpolation
                    )

                rename = pe.Node(util.Rename(), name="copyOrig")

                if not os.path.exists(orig_dir):
                    print(f'INFO : Create folder: {orig_dir}')
                    os.makedirs(orig_dir)

                rename.inputs.format_string = os.path.join(orig_dir, "001.mgz")

                if self.config.brain_mask_extraction_tool == "Freesurfer":
                    # ReconAll => named outputnode as we don't want to select a specific output....
                    fs_reconall = pe.Node(
                        interface=fs.ReconAll(
                            flags=f'-no-isrunning -parallel -openmp {self.config.number_of_threads}'
                        ),
                        name="reconall",
                    )
                    fs_reconall.inputs.directive = "all"
                    fs_reconall.inputs.args = self.config.freesurfer_args

                    # fs_reconall.inputs.subjects_dir and fs_reconall.inputs.subject_id set
                    # in cmp/pipelines/diffusion/diffusion.py
                    fs_reconall.inputs.subjects_dir = (
                        correct_freesurfer_subjects_path(self.config.freesurfer_subjects_dir)
                    )
                    # fmt: off
                    flow.connect(
                        [
                            (inputnode, fs_mriconvert, [(("T1", isavailable), "in_file")]),
                            (fs_mriconvert, rename, [("out_file", "in_file")]),
                            (rename, fs_reconall, [(("out_file", extract_reconall_base_dir), "subject_id")]),
                            (fs_reconall, outputnode, [("subjects_dir", "subjects_dir"), ("subject_id", "subject_id")]),
                        ]
                    )
                    # fmt: on
                else:
                    # ReconAll => named outputnode as we don't want to select a specific output....
                    fs_autorecon1 = pe.Node(
                        interface=fs.ReconAll(
                            flags="-no-isrunning -parallel -openmp {}".format(
                                self.config.number_of_threads
                            )
                        ),
                        name="autorecon1",
                    )
                    fs_autorecon1.inputs.directive = "autorecon1"

                    if self.config.brain_mask_extraction_tool == "ANTs":
                        fs_autorecon1.inputs.flags = (
                            "-no-isrunning -noskullstrip -parallel -openmp {}".format(
                                self.config.number_of_threads
                            )
                        )
                    fs_autorecon1.inputs.args = self.config.freesurfer_args

                    # fs_reconall.inputs.subjects_dir and fs_reconall.inputs.subject_id set
                    # in cmp/pipelines/diffusion/diffusion.py
                    fs_autorecon1.inputs.subjects_dir = (
                        correct_freesurfer_subjects_path(self.config.freesurfer_subjects_dir)
                    )
                    # fmt: off
                    flow.connect(
                        [
                            (inputnode, fs_mriconvert, [(("T1", isavailable), "in_file")]),
                            (fs_mriconvert, rename, [("out_file", "in_file")]),
                            (rename, fs_autorecon1, [(("out_file", extract_reconall_base_dir), "subject_id")]),
                        ]
                    )
                    # fmt: on

                    fs_source = pe.Node(interface=FreeSurferSource(), name="fsSource")

                    fs_mriconvert_nu = pe.Node(
                        interface=fs.MRIConvert(out_type="niigz", out_file="nu.nii.gz"),
                        name="niigzConvert",
                    )
                    # fmt: off
                    flow.connect(
                        [
                            (fs_autorecon1, fs_source, [("subjects_dir", "subjects_dir"),
                                                        ("subject_id", "subject_id")]),
                            (fs_source, fs_mriconvert_nu, [("nu", "in_file")]),
                        ]
                    )
                    # fmt: on
                    fs_mriconvert_brainmask = pe.Node(
                        interface=fs.MRIConvert(
                            out_type="mgz", out_file="brainmask.mgz"
                        ),
                        name="fsMriconvertBETbrainmask",
                    )

                    if self.config.brain_mask_extraction_tool == "BET":
                        fsl_bet = pe.Node(
                            interface=fsl.BET(
                                out_file="brain.nii.gz",
                                mask=True,
                                skull=True,
                                robust=True,
                            ),
                            name="fsl_bet",
                        )
                        # fmt: off
                        flow.connect(
                            [
                                (fs_mriconvert_nu, fsl_bet, [("out_file", "in_file")]),
                                (fsl_bet, fs_mriconvert_brainmask, [("out_file", "in_file")]),
                            ]
                        )
                        # fmt: on

                    elif self.config.brain_mask_extraction_tool == "ANTs":
                        ants_bet = pe.Node(
                            interface=ants.BrainExtraction(out_prefix="ants_bet_"),
                            name="antsBET",
                        )
                        ants_bet.inputs.brain_template = self.config.ants_templatefile
                        ants_bet.inputs.brain_probability_mask = (
                            self.config.ants_probmaskfile
                        )
                        ants_bet.inputs.extraction_registration_mask = (
                            self.config.ants_regmaskfile
                        )
                        ants_bet.inputs.num_threads = self.config.number_of_threads
                        # fmt: off
                        flow.connect(
                            [
                                (fs_mriconvert_nu, ants_bet, [("out_file", "anatomical_image")]),
                                (ants_bet, fs_mriconvert_brainmask, [("BrainExtractionBrain", "in_file")]),
                            ]
                        )
                        # fmt: on

                    copy_brainmask_to_fs = pe.Node(
                        interface=copyBrainMaskToFreesurfer(), name="copyBrainmaskTofs"
                    )
                    # fmt: off
                    flow.connect(
                        [
                            (rename, copy_brainmask_to_fs, [(("out_file", extract_reconall_base_dir), "subject_dir")]),
                            (fs_mriconvert_brainmask, copy_brainmask_to_fs, [("out_file", "in_file")]),
                        ]
                    )
                    # fmt: on

                    fs_reconall23 = pe.Node(
                        interface=fs.ReconAll(
                            flags="-no-isrunning -parallel -openmp {}".format(
                                self.config.number_of_threads
                            )
                        ),
                        name="reconall23",
                    )
                    fs_reconall23.inputs.directive = "autorecon2"
                    fs_reconall23.inputs.args = self.config.freesurfer_args
                    fs_reconall23.inputs.flags = "-autorecon3"

                    fs_reconall23.inputs.subjects_dir = (
                        correct_freesurfer_subjects_path(self.config.freesurfer_subjects_dir)
                    )
                    # fmt: off
                    flow.connect(
                        [
                            (copy_brainmask_to_fs,fs_reconall23, [(("out_brainmask_file", get_freesurfer_subject_id), "subject_id")]),
                            (fs_reconall23, outputnode, [("subjects_dir", "subjects_dir"),
                                                         ("subject_id", "subject_id")]),
                        ]
                    )
                    # fmt: on

            else:
                outputnode.inputs.subjects_dir = correct_freesurfer_subjects_path(self.config.freesurfer_subjects_dir)
                outputnode.inputs.subject_id = correct_freesurfer_subjectid_path(self.config.freesurfer_subject_id)
                print(f'INFO : Found existing {os.path.join(orig_dir, "001.mgz")} -> Skip Freesurfer recon-all')
                print(f'       - outputnode.inputs.subjects_dir: {outputnode.inputs.subjects_dir}')
                print(f'       - outputnode.inputs.subject_id: {outputnode.inputs.subject_id}')
        elif self.config.seg_tool == "Custom segmentation":
            self.create_workflow_custom(flow, inputnode, outputnode)

    def create_workflow_custom(self, flow, inputnode, outputnode):
        """Create the stage workflow when custom inputs are specified.

        Parameters
        ----------
        flow : nipype.pipeline.engine.Workflow
            The nipype.pipeline.engine.Workflow instance of the anatomical pipeline

        inputnode : nipype.interfaces.utility.IdentityInterface
            Identity interface describing the inputs of the segmentation stage

        outputnode : nipype.interfaces.utility.IdentityInterface
            Identity interface describing the outputs of the segmentation stage
        """
        # Create the dictionary of to be passed as output_query to BIDSDataGrabber
        output_query_dict = {
            "custom_brain_mask": self.config.custom_brainmask.get_query_dict(),
            "custom_wm_mask": self.config.custom_wm_mask.get_query_dict(),
            "custom_gm_mask": self.config.custom_gm_mask.get_query_dict(),
            "custom_csf_mask": self.config.custom_csf_mask.get_query_dict(),
            "custom_aparcaseg": self.config.custom_aparcaseg.get_query_dict()
        }

        # Make a list of toolbox derivatives directories where custom BIDS derivatives can be found
        toolbox_derivatives_dirnames = [
            self.config.custom_brainmask.get_toolbox_derivatives_dir(),
            self.config.custom_wm_mask.get_toolbox_derivatives_dir(),
            self.config.custom_gm_mask.get_toolbox_derivatives_dir(),
            self.config.custom_csf_mask.get_toolbox_derivatives_dir(),
            self.config.custom_aparcaseg.get_toolbox_derivatives_dir()
        ]
        toolbox_derivatives_dirnames=list(set(toolbox_derivatives_dirnames))

        toolbox_derivatives_paths = [
            os.path.join(self.bids_dir, "derivatives", toolbox_dir) for toolbox_dir in toolbox_derivatives_dirnames
        ]

        # Get input brain segmentation and mask files from custom BIDS derivatives
        # with BIDSDataGrabber
        print(f"Get custom input brain segmentation and mask files from {toolbox_derivatives_paths}...")
        print(f"    * Output query: {output_query_dict}...")
        custom_seg_grabber = pe.Node(
            interface=BIDSDataGrabber(
                base_dir=self.bids_dir,
                subject=self.bids_subject_label.split("-")[1],
                session=(self.bids_session_label.split("-")[1]
                         if self.bids_session_label is not None and self.bids_session_label != ""
                         else None),
                datatype="anat",
                extra_derivatives=toolbox_derivatives_paths,
                output_query=output_query_dict,
            ),
            name="custom_seg_grabber",
        )

        def get_first_path(paths):
            from cmtklib.bids.utils import get_native_space_files  # pylint: disable=W0404 # noqa: W0404
            paths = get_native_space_files(paths)
            return paths[0]

        apply_mask = pe.Node(interface=fsl.ApplyMask(), name="applyMask")
        if self.bids_session_label is not None and self.bids_session_label != "":
            apply_mask.inputs.out_file = f'{self.bids_subject_label}_{self.bids_session_label}_desc-brain_T1w.nii.gz'
        else:
            apply_mask.inputs.out_file = f'{self.bids_subject_label}_desc-brain_T1w.nii.gz'

        # fmt: off
        flow.connect(
            [
                (inputnode, apply_mask, [("T1", "in_file")]),
                (custom_seg_grabber, apply_mask, [(("custom_brain_mask", get_first_path), "mask_file")]),
                (apply_mask, outputnode, [("out_file", "brain")]),
                (custom_seg_grabber, outputnode, [(("custom_brain_mask", get_native_space_no_desc_files), "custom_brain_mask")]),
                (custom_seg_grabber, outputnode, [(("custom_wm_mask", get_native_space_no_desc_files), "custom_wm_mask")]),
                (custom_seg_grabber, outputnode, [(("custom_gm_mask", get_native_space_no_desc_files), "custom_gm_mask")]),
                (custom_seg_grabber, outputnode, [(("custom_csf_mask", get_native_space_no_desc_files), "custom_csf_mask")]),
                (custom_seg_grabber, outputnode, [(("custom_aparcaseg", get_native_space_files), "custom_aparcaseg")]),
            ]
        )
        # fmt: on

    def define_inspect_outputs(self, debug=False):
        """Update the `inspect_outputs` class attribute.

        It contains a dictionary of stage outputs with corresponding commands for visual inspection.

        Parameters
        ----------
        debug : bool
            If `True`, show printed output
        """
        if self.config.seg_tool == "Freesurfer":
            if self.config.use_existing_freesurfer_data is False:
                reconall_report_path = os.path.join(
                    self.stage_dir, "reconall", "_report", "report.rst"
                )
                fs_path = self.config.freesurfer_subject_id
                if os.path.exists(reconall_report_path):
                    if debug:
                        print("Read {}".format(reconall_report_path))
                    fs_path = extract_freesurfer_subject_dir(
                        reconall_report_path, self.output_dir, debug=debug
                    )
            else:
                fs_path = os.path.join(
                    self.config.freesurfer_subjects_dir,
                    self.config.freesurfer_subject_id,
                )

            if debug:
                print("fs_path : %s" % fs_path)

            self.inspect_outputs_dict["T1/brainmask"] = [
                "freeview",
                "-v",
                f'{os.path.join(fs_path, "mri", "T1.mgz")}',
                f'{os.path.join(fs_path, "mri", "brainmask.mgz")}:colormap=heat:opacity=0.2'
            ]
            self.inspect_outputs_dict["norm/aseg/surf"] = [
                "freeview",
                "-v",
                f'{os.path.join(fs_path, "mri", "norm.mgz")}',
                f'{os.path.join(fs_path, "mri", "aseg.mgz")}:colormap=lut:opacity=0.2',
                "-f",
                f'{os.path.join(fs_path, "surf", "lh.white")}:edgecolor=blue',
                f'{os.path.join(fs_path, "surf", "rh.white")}:edgecolor=blue',
                f'{os.path.join(fs_path, "surf", "lh.pial")}:edgecolor=red',
                f'{os.path.join(fs_path, "surf", "rh.pial")}:edgecolor=red',
            ]
        else:
            raw_subject_dir = os.path.join( self.bids_dir, self.bids_subject_label)
            sub_ses = self.bids_subject_label
            if self.bids_session_label is not None and self.bids_session_label != "":
                raw_subject_dir = os.path.join(raw_subject_dir, self.bids_session_label)
                sub_ses += "_" + self.bids_session_label

            # Take the first T1w found in the subject/session directory of raw data
            t1_file = glob(os.path.join(raw_subject_dir, "anat", sub_ses + "*_T1w.nii.gz"))[0]
            print(t1_file)

            brainmask_file = self.config.custom_brainmask.get_filename_path(
                base_dir=os.path.join(self.output_dir, __cmp_directory__),
                subject=self.bids_subject_label,
                session=self.bids_session_label if self.bids_session_label != "" else None
            ) + ".nii.gz"

            gm_file = self.config.custom_gm_mask.get_filename_path(
                base_dir=os.path.join(self.output_dir, __cmp_directory__),
                subject=self.bids_subject_label,
                session=self.bids_session_label if self.bids_session_label != "" else None
            ) + ".nii.gz"

            wm_file = self.config.custom_wm_mask.get_filename_path(
                base_dir=os.path.join(self.output_dir, __cmp_directory__),
                subject=self.bids_subject_label,
                session=self.bids_session_label if self.bids_session_label != "" else None
            ) + ".nii.gz"

            csf_file = self.config.custom_csf_mask.get_filename_path(
                base_dir=os.path.join(self.output_dir, __cmp_directory__),
                subject=self.bids_subject_label,
                session=self.bids_session_label if self.bids_session_label != "" else None
            ) + ".nii.gz"

            aparcaseg_file = self.config.custom_aparcaseg.get_filename_path(
                base_dir=os.path.join(self.output_dir, __cmp_directory__),
                subject=self.bids_subject_label,
                session=self.bids_session_label if self.bids_session_label != "" else None
            ) + ".nii.gz"

            self.inspect_outputs_dict["T1/brainmask"] = [
                "freeview",
                "-v",
                f'{t1_file}',
                f'{brainmask_file}:colormap=heat:opacity=0.2'
            ]
            self.inspect_outputs_dict["T1/aparcaseg"] = [
                "freeview",
                "-v",
                f'{t1_file}',
                f'{aparcaseg_file}:colormap=lut:opacity=0.2',
            ]
            self.inspect_outputs_dict["T1/WM/GM/CSF"] = [
                "freeview",
                "-v",
                f'{t1_file}',
                f'{csf_file}:opacity=0.2',
                f'{gm_file}:opacity=0.2',
                f'{wm_file}:opacity=0.2',
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
        if self.config.use_existing_freesurfer_data:
            return True
        else:
            return os.path.exists(
                os.path.join(self.stage_dir, "reconall", "result_reconall.pklz")
            )

        # TODO: Add condition when "Custom Segmentation is used"
