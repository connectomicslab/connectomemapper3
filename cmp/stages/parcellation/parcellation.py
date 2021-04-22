# Copyright (C) 2009-2021, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""Definition of config and stage classes for computing brain parcellation."""

# General imports
import os
from traits.api import *
import pkg_resources

# Nipype imports
import nipype.pipeline.engine as pe
import nipype.interfaces.utility as util

# Own imports
from cmp.stages.common import Stage
from cmtklib.parcellation import (
    Parcellate,
    ParcellateBrainstemStructures,
    ParcellateHippocampalSubfields,
    ParcellateThalamus,
    CombineParcellations,
    ComputeParcellationRoiVolumes,
)
from cmtklib.util import get_pipeline_dictionary_outputs, get_basename


class ParcellationConfig(HasTraits):
    """Class used to store configuration parameters of a :class:`~cmp.stages.parcellation.parcellation.ParcellationStage` object.

    Attributes
    ----------
    pipeline_mode : traits.Enum(["Diffusion", "fMRI"])
        Distinguish if a parcellation is run in a "Diffusion" or
        in a fMRI pipeline

    parcellation_scheme : traits.Str
        Parcellation scheme used
        (Default: 'Lausanne2008')

    parcellation_scheme_editor : traits.List(['NativeFreesurfer', 'Lausanne2008', 'Lausanne2018', 'Custom'])
        Choice of parcellation schemes

    include_thalamic_nuclei_parcellation : traits.Bool
        Perform and include thalamic nuclei segmentation in
        'Lausanne2018' parcellation
        (Default: True)

    ants_precision_type : traits.Enum(['double', 'float'])
        Specify ANTs used by thalamic nuclei segmentation to adopt
        single / double precision float representation to reduce
        memory usage.
        (Default: 'double')

    segment_hippocampal_subfields : traits.Bool
        Perform and include FreeSurfer hippocampal subfields segmentation in
        'Lausanne2018' parcellation
        (Default: True)

    segment_brainstem : traits.Bool
        Perform and include FreeSurfer brainstem segmentation in
        'Lausanne2018' parcellation
        (Default: True)

    atlas_info : traits.Dict
        Dictionary storing information of atlases in the form
        >>> atlas_info = {atlas_name: {'number_of_regions': number_of_regions,
        >>>               'node_information_graphml': graphml_file}} # doctest: +SKIP

    custom_bids_derivatives_dir : traits.Directory
        Specify a custom BIDS derivatives directory
        where parcellation and csf segmentation files
        can be found

    custom_bids_derivatives_json : traits.File
        Path to a JSON file specifying the BIDS format of
        parcellation atlas nifti and graphml files, and
        csf file to query

    See Also
    --------
    cmp.stages.parcellation.parcellation.ParcellationStage
    """

    pipeline_mode = Enum(["Diffusion", "fMRI"])
    parcellation_scheme = Str("Lausanne2008")
    parcellation_scheme_editor = List(
        ["NativeFreesurfer", "Lausanne2008", "Lausanne2018"]
    )
    include_thalamic_nuclei_parcellation = Bool(True)
    ants_precision_type = Enum(["double", "float"])
    segment_hippocampal_subfields = Bool(True)
    segment_brainstem = Bool(True)
    pre_custom = Str("Lausanne2008")
    custom_bids_derivatives_dir = Directory(
        desc="Specify a custom BIDS derivatives directory "
        + "where parcellation and csf segmentation files "
        + "can be found"
    )
    custom_bids_derivatives_json = File(
        desc="Path to a JSON file specifying the BIDS format of "
        + "parcellation atlas nifti and graphml files, and "
        + "csf file to query"
    )
    number_of_regions = Int()
    atlas_nifti_file = File(exists=True)
    csf_file = File(exists=True)
    brain_file = File(exists=True)
    graphml_file = File(exists=True)
    atlas_info = Dict()

    def update_atlas_info(self):
        """Update `atlas_info` class attribute."""
        atlas_name = os.path.basename(self.atlas_nifti_file)
        atlas_name = os.path.splitext(os.path.splitext(atlas_name)[0])[0].encode(
            "ascii"
        )
        self.atlas_info = {
            atlas_name: {
                "number_of_regions": self.number_of_regions,
                "node_information_graphml": self.graphml_file,
            }
        }

    def _atlas_nifti_file_changed(self, new):
        """Calls `update_atlas_info()` when ``atlas_nifti_file`` is changed.

        Parameters
        ----------
        new : string
            New value of ``atlas_nifti_file``
        """
        self.update_atlas_info()

    def _number_of_regions_changed(self, new):
        """Calls `update_atlas_info()` when ``number_of_regions`` is changed.

        Parameters
        ----------
        new : string
            New value of ``number_of_regions``
        """
        self.update_atlas_info()

    def _graphml_file_changed(self, new):
        """Calls `update_atlas_info()` when ``graphml_file`` is changed.

        Parameters
        ----------
        new : string
            New value of ``graphml_file``
        """
        self.update_atlas_info()


class ParcellationStage(Stage):
    """Class that represents the parcellation stage of a :class:`~cmp.pipelines.anatomical.anatomical.AnatomicalPipeline`.

    Methods
    -------
    create_workflow()
        Create the workflow of the `ParcellationStage`

    See Also
    --------
    cmp.pipelines.anatomical.anatomical.AnatomicalPipeline
    cmp.stages.parcellation.parcellation.ParcellationConfig
    """

    def __init__(self, pipeline_mode, subject, session, bids_dir, output_dir):
        """Constructor of a :class:`~cmp.stages.parcellation.parcellation.ParcellationStage` instance."""
        self.name = "parcellation_stage"
        self.bids_subject_label = subject
        self.bids_session_label = session
        self.bids_dir = bids_dir
        self.output_dir = output_dir
        self.config = ParcellationConfig()
        self.config.pipeline_mode = pipeline_mode
        self.inputs = ["subjects_dir", "subject_id", "custom_wm_mask"]
        self.outputs = [
            "T1",
            "brain",
            "aseg",
            "aparc_aseg",
            "brain_mask",
            "wm_mask_file",
            "gm_mask_file",
            "csf_mask_file",
            "wm_eroded",
            "csf_eroded",
            "brain_eroded",
            "roi_volumes",
            "roi_colorLUTs",
            "roi_graphMLs",
            "roi_volumes_stats",
            "parcellation_scheme",
            "atlas_info",
        ]

    def create_workflow(self, flow, inputnode, outputnode):
        """Create the stage workflow.

        Parameters
        ----------
        flow : nipype.pipeline.engine.Workflow
            The nipype.pipeline.engine.Workflow instance of the anatomical pipeline

        inputnode : nipype.interfaces.utility.IdentityInterface
            Identity interface describing the inputs of the stage

        outputnode : nipype.interfaces.utility.IdentityInterface
            Identity interface describing the outputs of the stage
        """
        # from nipype.interfaces.fsl.maths import MathsCommand

        outputnode.inputs.parcellation_scheme = self.config.parcellation_scheme

        if self.config.parcellation_scheme != "Custom":

            parc_node = pe.Node(
                interface=Parcellate(),
                name="%s_parcellation" % self.config.parcellation_scheme,
            )
            parc_node.inputs.parcellation_scheme = self.config.parcellation_scheme
            parc_node.inputs.erode_masks = True

            flow.connect(
                [
                    (
                        inputnode,
                        parc_node,
                        [
                            ("subjects_dir", "subjects_dir"),
                            (("subject_id", get_basename), "subject_id"),
                        ],
                    ),
                    (
                        parc_node,
                        outputnode,
                        [
                            ("white_matter_mask_file", "wm_mask_file"),
                            ("csf_mask_file", "csf_mask_file"),
                            ("wm_eroded", "wm_eroded"),
                            ("csf_eroded", "csf_eroded"),
                            ("brain_eroded", "brain_eroded"),
                            ("T1", "T1"),
                            ("brain", "brain"),
                            ("brain_mask", "brain_mask"),
                        ],
                    ),
                ]
            )

            flow.connect(
                [
                    (parc_node, outputnode, [("aseg", "aseg")]),
                ]
            )

            # threshold_roi = pe.Node(
            #     interface=fsl.MathsCommand(
            #         out_file='T1w_class-GM.nii.gz'
            #     ),
            #     name='make_gm_mask'
            # )
            # flow.connect([
            #             (threshold_roi, outputnode, [("out_file","gm_mask_file")]),
            #             ])

            if self.config.parcellation_scheme == "Lausanne2018":
                parcCombiner = pe.Node(
                    interface=CombineParcellations(), name="parcCombiner"
                )
                parcCombiner.inputs.create_colorLUT = True
                parcCombiner.inputs.create_graphml = True

                flow.connect(
                    [
                        (
                            inputnode,
                            parcCombiner,
                            [
                                ("subjects_dir", "subjects_dir"),
                                (("subject_id", get_basename), "subject_id"),
                            ],
                        ),
                        (
                            parc_node,
                            parcCombiner,
                            [("roi_files_in_structural_space", "input_rois")],
                        ),
                    ]
                )

                if self.config.segment_brainstem:
                    parcBrainStem = pe.Node(
                        interface=ParcellateBrainstemStructures(), name="parcBrainStem"
                    )

                    flow.connect(
                        [
                            (
                                inputnode,
                                parcBrainStem,
                                [
                                    ("subjects_dir", "subjects_dir"),
                                    (("subject_id", get_basename), "subject_id"),
                                ],
                            ),
                            (
                                parcBrainStem,
                                parcCombiner,
                                [("brainstem_structures", "brainstem_structures")],
                            ),
                        ]
                    )

                if self.config.segment_hippocampal_subfields:
                    parcHippo = pe.Node(
                        interface=ParcellateHippocampalSubfields(), name="parcHippo"
                    )

                    flow.connect(
                        [
                            (
                                inputnode,
                                parcHippo,
                                [
                                    ("subjects_dir", "subjects_dir"),
                                    (("subject_id", get_basename), "subject_id"),
                                ],
                            ),
                            (
                                parcHippo,
                                parcCombiner,
                                [("lh_hipposubfields", "lh_hippocampal_subfields")],
                            ),
                            (
                                parcHippo,
                                parcCombiner,
                                [("rh_hipposubfields", "rh_hippocampal_subfields")],
                            ),
                        ]
                    )

                if self.config.include_thalamic_nuclei_parcellation:
                    parcThal = pe.Node(interface=ParcellateThalamus(), name="parcThal")
                    parcThal.inputs.template_image = os.path.abspath(
                        pkg_resources.resource_filename(
                            "cmtklib",
                            os.path.join(
                                "data",
                                "segmentation",
                                "thalamus2018",
                                "mni_icbm152_t1_tal_nlin_sym_09b_hires_1.nii.gz",
                            ),
                        )
                    )
                    parcThal.inputs.thalamic_nuclei_maps = os.path.abspath(
                        pkg_resources.resource_filename(
                            "cmtklib",
                            os.path.join(
                                "data",
                                "segmentation",
                                "thalamus2018",
                                "Thalamus_Nuclei-HCP-4DSPAMs.nii.gz",
                            ),
                        )
                    )
                    parcThal.inputs.ants_precision_type = (
                        self.config.ants_precision_type
                    )

                    flow.connect(
                        [
                            (
                                inputnode,
                                parcThal,
                                [
                                    ("subjects_dir", "subjects_dir"),
                                    (("subject_id", get_basename), "subject_id"),
                                ],
                            ),
                            (parc_node, parcThal, [("T1", "T1w_image")]),
                            (
                                parcThal,
                                parcCombiner,
                                [("max_prob_registered", "thalamus_nuclei")],
                            ),
                        ]
                    )

                flow.connect(
                    [
                        (
                            parc_node,
                            outputnode,
                            [("gray_matter_mask_file", "gm_mask_file")],
                        ),
                        (parcCombiner, outputnode, [("aparc_aseg", "aparc_aseg")]),
                        (parcCombiner, outputnode, [("output_rois", "roi_volumes")]),
                        (
                            parcCombiner,
                            outputnode,
                            [("colorLUT_files", "roi_colorLUTs")],
                        ),
                        (parcCombiner, outputnode, [("graphML_files", "roi_graphMLs")]),
                    ]
                )

                computeROIVolumetry = pe.Node(
                    interface=ComputeParcellationRoiVolumes(),
                    name="computeROIVolumetry",
                )
                computeROIVolumetry.inputs.parcellation_scheme = (
                    self.config.parcellation_scheme
                )

                flow.connect(
                    [
                        (
                            parcCombiner,
                            computeROIVolumetry,
                            [("output_rois", "roi_volumes")],
                        ),
                        (
                            parcCombiner,
                            computeROIVolumetry,
                            [("graphML_files", "roi_graphMLs")],
                        ),
                        (
                            computeROIVolumetry,
                            outputnode,
                            [("roi_volumes_stats", "roi_volumes_stats")],
                        ),
                    ]
                )

                # create_atlas_info = pe.Node(interface=CreateLausanne2018AtlasInfo(),name="create_atlas_info")
                # flow.connect([
                #             (parcCombiner,create_atlas_info,[("output_rois","roi_volumes")]),
                #             (parcCombiner,create_atlas_info,[("graphML_files","roi_graphMLs")]),
                #             (create_atlas_info,outputnode,[("atlas_info","atlas_info")]),
                #         ])
            elif self.config.parcellation_scheme == "Lausanne2008":

                roi_colorLUTs = [
                    os.path.join(
                        pkg_resources.resource_filename(
                            "cmtklib",
                            os.path.join(
                                "data",
                                "parcellation",
                                "lausanne2008",
                                "resolution83",
                                "resolution83_LUT.txt",
                            ),
                        )
                    ),
                    os.path.join(
                        pkg_resources.resource_filename(
                            "cmtklib",
                            os.path.join(
                                "data",
                                "parcellation",
                                "lausanne2008",
                                "resolution150",
                                "resolution150_LUT.txt",
                            ),
                        )
                    ),
                    os.path.join(
                        pkg_resources.resource_filename(
                            "cmtklib",
                            os.path.join(
                                "data",
                                "parcellation",
                                "lausanne2008",
                                "resolution258",
                                "resolution258_LUT.txt",
                            ),
                        )
                    ),
                    os.path.join(
                        pkg_resources.resource_filename(
                            "cmtklib",
                            os.path.join(
                                "data",
                                "parcellation",
                                "lausanne2008",
                                "resolution500",
                                "resolution500_LUT.txt",
                            ),
                        )
                    ),
                    os.path.join(
                        pkg_resources.resource_filename(
                            "cmtklib",
                            os.path.join(
                                "data",
                                "parcellation",
                                "lausanne2008",
                                "resolution1015",
                                "resolution1015_LUT.txt",
                            ),
                        )
                    ),
                ]

                roi_graphMLs = [
                    os.path.join(
                        pkg_resources.resource_filename(
                            "cmtklib",
                            os.path.join(
                                "data",
                                "parcellation",
                                "lausanne2008",
                                "resolution83",
                                "resolution83.graphml",
                            ),
                        )
                    ),
                    os.path.join(
                        pkg_resources.resource_filename(
                            "cmtklib",
                            os.path.join(
                                "data",
                                "parcellation",
                                "lausanne2008",
                                "resolution150",
                                "resolution150.graphml",
                            ),
                        )
                    ),
                    os.path.join(
                        pkg_resources.resource_filename(
                            "cmtklib",
                            os.path.join(
                                "data",
                                "parcellation",
                                "lausanne2008",
                                "resolution258",
                                "resolution258.graphml",
                            ),
                        )
                    ),
                    os.path.join(
                        pkg_resources.resource_filename(
                            "cmtklib",
                            os.path.join(
                                "data",
                                "parcellation",
                                "lausanne2008",
                                "resolution500",
                                "resolution500.graphml",
                            ),
                        )
                    ),
                    os.path.join(
                        pkg_resources.resource_filename(
                            "cmtklib",
                            os.path.join(
                                "data",
                                "parcellation",
                                "lausanne2008",
                                "resolution1015",
                                "resolution1015.graphml",
                            ),
                        )
                    ),
                ]

                parc_files = pe.Node(
                    interface=util.IdentityInterface(
                        fields=["roi_colorLUTs", "roi_graphMLs"]
                    ),
                    name="parcellation_files",
                )
                parc_files.inputs.roi_colorLUTs = [
                    "{}".format(p) for p in roi_colorLUTs
                ]
                parc_files.inputs.roi_graphMLs = ["{}".format(p) for p in roi_graphMLs]

                flow.connect(
                    [
                        (
                            parc_node,
                            outputnode,
                            [("gray_matter_mask_file", "gm_mask_file")],
                        ),
                        (parc_node, outputnode, [("aparc_aseg", "aparc_aseg")]),
                        (
                            parc_node,
                            outputnode,
                            [("roi_files_in_structural_space", "roi_volumes")],
                        ),
                        (parc_files, outputnode, [("roi_colorLUTs", "roi_colorLUTs")]),
                        (parc_files, outputnode, [("roi_graphMLs", "roi_graphMLs")]),
                        # (parc_node,outputnode,[(("roi_files_in_structural_space",get_atlas_LUTs),"roi_colorLUTs")]),
                        # (parc_node,outputnode,[(("roi_files_in_structural_space",get_atlas_graphMLs),"roi_graphMLs")]),
                    ]
                )

                computeROIVolumetry = pe.Node(
                    interface=ComputeParcellationRoiVolumes(),
                    name="computeROIVolumetry",
                )
                computeROIVolumetry.inputs.parcellation_scheme = (
                    self.config.parcellation_scheme
                )

                flow.connect(
                    [
                        (
                            parc_node,
                            computeROIVolumetry,
                            [("roi_files_in_structural_space", "roi_volumes")],
                        ),
                        (
                            parc_files,
                            computeROIVolumetry,
                            [("roi_graphMLs", "roi_graphMLs")],
                        ),
                        (
                            computeROIVolumetry,
                            outputnode,
                            [("roi_volumes_stats", "roi_volumes_stats")],
                        ),
                    ]
                )
            else:
                # def get_atlas_LUTs(paths):
                #     colorLUTs = [os.path.join(pkg_resources.resource_filename('
                #                     cmtklib',os.path.join('data','parcellation','nativefreesurfer','
                #                                           freesurferaparc','FreeSurferColorLUT_adapted.txt'))),
                #                  ]
                #     return colorLUTs
                #
                # def get_atlas_graphMLs(paths):
                #     graphMLs = [os.path.join(pkg_resources.resource_filename(
                #                   'cmtklib',os.path.join('data','parcellation','nativefreesurfer',
                #                                          'freesurferaparc','resolution83.graphml'))),
                #                  ]
                #     return graphMLs

                roi_colorLUTs = [
                    os.path.join(
                        pkg_resources.resource_filename(
                            "cmtklib",
                            os.path.join(
                                "data",
                                "parcellation",
                                "nativefreesurfer",
                                "freesurferaparc",
                                "FreeSurferColorLUT_adapted.txt",
                            ),
                        )
                    )
                ]

                roi_graphMLs = [
                    os.path.join(
                        pkg_resources.resource_filename(
                            "cmtklib",
                            os.path.join(
                                "data",
                                "parcellation",
                                "nativefreesurfer",
                                "freesurferaparc",
                                "freesurferaparc.graphml",
                            ),
                        )
                    )
                ]

                parc_files = pe.Node(
                    interface=util.IdentityInterface(
                        fields=["roi_colorLUTs", "roi_graphMLs"]
                    ),
                    name="parcellation_files",
                )
                parc_files.inputs.roi_colorLUTs = [
                    "{}".format(p) for p in roi_colorLUTs
                ]
                parc_files.inputs.roi_graphMLs = ["{}".format(p) for p in roi_graphMLs]

                flow.connect(
                    [
                        (
                            parc_node,
                            outputnode,
                            [("gray_matter_mask_file", "gm_mask_file")],
                        ),
                        (parc_node, outputnode, [("aparc_aseg", "aparc_aseg")]),
                        (
                            parc_node,
                            outputnode,
                            [("roi_files_in_structural_space", "roi_volumes")],
                        ),
                        (parc_files, outputnode, [("roi_colorLUTs", "roi_colorLUTs")]),
                        (parc_files, outputnode, [("roi_graphMLs", "roi_graphMLs")]),
                        # (parc_node,outputnode,[(("roi_files_in_structural_space",get_atlas_LUTs),"roi_colorLUTs")]),
                        # (parc_node,outputnode,[(("roi_files_in_structural_space",get_atlas_graphMLs),"roi_graphMLs")]),
                    ]
                )

                computeROIVolumetry = pe.Node(
                    interface=ComputeParcellationRoiVolumes(),
                    name="computeROIVolumetry",
                )
                computeROIVolumetry.inputs.parcellation_scheme = (
                    self.config.parcellation_scheme
                )

                flow.connect(
                    [
                        (
                            parc_node,
                            computeROIVolumetry,
                            [("roi_files_in_structural_space", "roi_volumes")],
                        ),
                        (
                            parc_files,
                            computeROIVolumetry,
                            [("roi_graphMLs", "roi_graphMLs")],
                        ),
                        (
                            computeROIVolumetry,
                            outputnode,
                            [("roi_volumes_stats", "roi_volumes_stats")],
                        ),
                    ]
                )

            # TODO
            # if self.config.pipeline_mode == "fMRI":
            #     erode_wm = pe.Node(interface=cmtk.Erode(),name="erode_wm")
            #     flow.connect([
            #                 (inputnode,erode_wm,[("custom_wm_mask","in_file")]),
            #                 (erode_wm,outputnode,[("out_file","wm_eroded")]),
            #                 ])
            #     if os.path.exists(self.config.csf_file):
            #         erode_csf = pe.Node(interface=cmtk.Erode(in_file = self.config.csf_file),name="erode_csf")
            #         flow.connect([
            #                     (erode_csf,outputnode,[("out_file","csf_eroded")])
            #                     ])
            #     if os.path.exists(self.config.brain_file):
            #         erode_brain = pe.Node(interface=cmtk.Erode(in_file = self.config.brain_file),name="erode_brain")
            #         flow.connect([
            #                     (erode_brain,outputnode,[("out_file","brain_eroded")])
            #                     ])

    def define_inspect_outputs(self):
        """Update the `inspect_outputs' class attribute.

        It contains a dictionary of stage outputs with corresponding commands for visual inspection.
        """
        anat_sinker_dir = os.path.join(
            os.path.dirname(self.stage_dir), "anatomical_sinker"
        )
        anat_sinker_report = os.path.join(anat_sinker_dir, "_report", "report.rst")

        if self.config.parcellation_scheme != "Custom":
            if os.path.exists(anat_sinker_report):
                anat_outputs = get_pipeline_dictionary_outputs(
                    anat_sinker_report, self.output_dir
                )

                white_matter_file = anat_outputs["anat.@wm_mask"]

                if isinstance(anat_outputs["anat.@roivs"], str):
                    lut_file = pkg_resources.resource_filename(
                        "cmtklib",
                        os.path.join(
                            "data",
                            "parcellation",
                            "nativefreesurfer",
                            "freesurferaparc",
                            "FreeSurferColorLUT_adapted.txt",
                        ),
                    )
                    roi_v = anat_outputs["anat.@roivs"]

                    if os.path.exists(white_matter_file) and os.path.exists(roi_v):
                        self.inspect_outputs_dict[os.path.basename(roi_v)] = [
                            "freeview",
                            "-v",
                            white_matter_file + ":colormap=GEColor",
                            roi_v + ":colormap=lut:lut=" + lut_file,
                        ]
                elif isinstance(anat_outputs["anat.@roivs"], list):
                    if self.config.parcellation_scheme == "Lausanne2008":
                        resolution = {
                            "1": "resolution83",
                            "2": "resolution150",
                            "3": "resolution258",
                            "4": "resolution500",
                            "5": "resolution1015",
                        }
                        for roi_v in anat_outputs["anat.@roivs"]:
                            roi_basename = os.path.basename(roi_v)
                            scale = roi_basename[23:-7]
                            lut_file = pkg_resources.resource_filename(
                                "cmtklib",
                                os.path.join(
                                    "data",
                                    "parcellation",
                                    "lausanne2008",
                                    resolution[scale],
                                    resolution[scale] + "_LUT.txt",
                                ),
                            )
                            if os.path.exists(white_matter_file) and os.path.exists(
                                roi_v
                            ):
                                self.inspect_outputs_dict[roi_basename] = [
                                    "freeview",
                                    "-v",
                                    white_matter_file + ":colormap=GEColor",
                                    roi_v + ":colormap=lut:lut=" + lut_file,
                                ]
                    elif self.config.parcellation_scheme == "Lausanne2018":
                        for roi_v, lut_file in zip(
                            anat_outputs["anat.@roivs"], anat_outputs["anat.@luts"]
                        ):
                            roi_basename = os.path.basename(roi_v)

                            if os.path.exists(white_matter_file) and os.path.exists(
                                roi_v
                            ):
                                self.inspect_outputs_dict[roi_basename] = [
                                    "freeview",
                                    "-v",
                                    white_matter_file + ":colormap=GEColor",
                                    roi_v + ":colormap=lut:lut=" + lut_file,
                                ]

                # self.inspect_outputs = self.inspect_outputs_dict.keys()
        # else:
        #     self.inspect_outputs_dict["Custom atlas"] = [
        #         'fsleyes', self.config.atlas_nifti_file, "-cm", "random"]

        self.inspect_outputs = sorted(
            [key for key in list(self.inspect_outputs_dict.keys())], key=str.lower
        )

    def has_run(self):
        """Function that returns `True` if the stage has been run successfully.

        Returns
        -------
        `True` if the stage has been run successfully
        """
        if self.config.parcellation_scheme != "Custom":
            if self.config.parcellation_scheme == "Lausanne2018":
                return os.path.exists(
                    os.path.join(
                        self.stage_dir, "parcCombiner", "result_parcCombiner.pklz"
                    )
                )
            else:
                return os.path.exists(
                    os.path.join(
                        self.stage_dir,
                        "%s_parcellation" % self.config.parcellation_scheme,
                        "result_%s_parcellation.pklz" % self.config.parcellation_scheme,
                    )
                )
        # else:
        #     return os.path.exists(self.config.atlas_nifti_file)
