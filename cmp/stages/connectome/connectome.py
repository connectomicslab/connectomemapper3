# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""Definition of config and stage classes for building structural connectivity matrices."""

# Global imports
import os

from traits.api import *

import networkx as nx

# Nipype imports
import nipype.interfaces.utility as util
import nipype.pipeline.engine as pe

# Own imports
from cmp.stages.common import Stage
import cmtklib.connectome
from cmtklib.util import get_pipeline_dictionary_outputs


class ConnectomeConfig(HasTraits):
    """Class used to store configuration parameters of a :class:`~cmp.stages.connectome.connectome.ConnectomeStage` instance.

    Attributes
    ----------
    compute_curvature : traits.Bool
        Compute fiber curvature (Default: False)

    output_types : ['gPickle', 'mat', 'graphml']
        Output connectome format

    connectivity_metrics : ['Fiber number', 'Fiber length', 'Fiber density', 'Fiber proportion', 'Normalized fiber density', 'ADC', 'gFA']
        Set of connectome maps to compute

    log_visualization : traits.Bool
        Log visualization that might be obsolete as this has been detached
        after creation of the bidsappmanager (Default: True)

    circular_layout : traits.Bool
        Visualization of the connectivity matrix using a circular layout
        that might be obsolete as this has been detached after creation
        of the bidsappmanager (Default: False)

    subject : traits.Str
        BIDS subject ID (in the form ``sub-XX``)

    See Also
    --------
    cmp.stages.connectome.connectome.ConnectomeStage
    """

    # modality = List(['Deterministic','Probabilistic'])
    compute_curvature = Bool(False)
    output_types = List(["gPickle", "mat", "graphml"])
    connectivity_metrics = List(
        [
            "Fiber number",
            "Fiber length",
            "Fiber density",
            "Fiber proportion",
            "Normalized fiber density",
            "ADC",
            "gFA",
        ]
    )
    log_visualization = Bool(True)
    circular_layout = Bool(False)
    subject = Str


class ConnectomeStage(Stage):
    """Class that represents the connectome building stage of a :class:`~cmp.pipelines.diffusion.diffusion.DiffusionPipeline`.

    Methods
    -------
    create_workflow()
        Create the workflow of the diffusion `ConnectomeStage`

    See Also
    --------
    cmp.pipelines.diffusion.diffusion.DiffusionPipeline
    cmp.stages.connectome.connectome.ConnectomeConfig
    """

    def __init__(self, bids_dir, output_dir):
        """Constructor of a :class:`~cmp.stages.connectome.connectome.Connectome` instance."""
        self.name = "connectome_stage"
        self.bids_dir = bids_dir
        self.output_dir = output_dir

        self.config = ConnectomeConfig()
        self.inputs = [
            "roi_volumes_registered",
            "roi_graphMLs",
            "track_file",
            "parcellation_scheme",
            "atlas_info",
            "FA",
            "ADC",
            "AD",
            "RD",
            "skewness",
            "kurtosis",
            "P0",
            "shore_maps",
            "mapmri_maps",
        ]
        self.outputs = [
            "endpoints_file",
            "endpoints_mm_file",
            "final_fiberslength_files",
            "filtered_fiberslabel_files",
            "final_fiberlabels_files",
            "streamline_final_file",
            "connectivity_matrices",
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
        """
        cmtk_cmat = pe.Node(
            interface=cmtklib.connectome.DmriCmat(), name="compute_matrice"
        )
        cmtk_cmat.inputs.compute_curvature = self.config.compute_curvature
        cmtk_cmat.inputs.output_types = self.config.output_types

        # Additional maps
        map_merge = pe.Node(interface=util.Merge(9), name="merge_additional_maps")
        # fmt: off
        flow.connect(
            [
                (inputnode, map_merge, [("FA", "in1"),
                                        ("ADC", "in2"),
                                        ("AD", "in3"),
                                        ("RD", "in4"),
                                        ("skewness", "in5"),
                                        ("kurtosis", "in6"),
                                        ("P0", "in7"),
                                        ("shore_maps", "in8"),
                                        ("mapmri_maps", "in9")]),
                (map_merge, cmtk_cmat, [("out", "additional_maps")]),
                (inputnode, cmtk_cmat, [("track_file", "track_file"),
                                        ("roi_graphMLs", "roi_graphmls"),
                                        ("parcellation_scheme", "parcellation_scheme"),
                                        ("atlas_info", "atlas_info"),
                                        ("roi_volumes_registered", "roi_volumes")]),
                (cmtk_cmat, outputnode, [("endpoints_file", "endpoints_file"),
                                         ("endpoints_mm_file", "endpoints_mm_file"),
                                         ("final_fiberslength_files", "final_fiberslength_files"),
                                         ("filtered_fiberslabel_files", "filtered_fiberslabel_files"),
                                         ("final_fiberlabels_files", "final_fiberlabels_files"),
                                         ("streamline_final_file", "streamline_final_file"),
                                         ("connectivity_matrices", "connectivity_matrices")]),
            ]
        )
        # fmt: on

    def define_inspect_outputs(self):
        """Update the `inspect_outputs` class attribute.

        It contains a dictionary of stage outputs with corresponding commands for visual inspection.
        """
        # print('inspect outputs connectome stage')
        dwi_sinker_dir = os.path.join(
            os.path.dirname(self.stage_dir), "diffusion_sinker"
        )
        dwi_sinker_report = os.path.join(dwi_sinker_dir, "_report", "report.rst")

        if os.path.exists(dwi_sinker_report):
            dwi_outputs = get_pipeline_dictionary_outputs(
                dwi_sinker_report, self.output_dir
            )

            tracto = dwi_outputs["dwi.@streamline_final_file"]
            if os.path.exists(tracto):
                self.inspect_outputs_dict["Final tractogram"] = ["trackvis", tracto]

            mat = dwi_outputs["dwi.@connectivity_matrices"]

            map_scale = "default"
            if self.config.log_visualization:
                map_scale = "log"

            if self.config.circular_layout:
                layout = "circular"
            else:
                layout = "matrix"

            if isinstance(mat, str):
                # print("is str")
                if "gpickle" in mat:
                    # 'Fiber number','Fiber length','Fiber density','ADC','gFA'
                    con_name = os.path.basename(mat).split(".")[0].split("_")[-1]
                    # print("con_name:"+con_name)

                    # Load the connectivity matrix and extract the attributes (weights)
                    # con_mat =  pickle.load(mat, encoding="latin1")
                    con_mat = nx.read_gpickle(mat)
                    con_metrics = list(list(con_mat.edges(data=True))[0][2].keys())

                    # Create dynamically the list of output connectivity metrics for inspection
                    for con_metric in con_metrics:
                        metric_str = " ".join(con_metric.split("_"))
                        self.inspect_outputs_dict[con_name + " - " + metric_str] = [
                            "showmatrix_gpickle",
                            layout,
                            mat,
                            con_metric,
                            "False",
                            self.config.subject + " - " + con_name + " - " + metric_str,
                            map_scale,
                        ]

            else:
                # print("is list")
                for mat in dwi_outputs["dwi.@connectivity_matrices"]:
                    # print("mat : %s" % mat)
                    if "gpickle" in mat:
                        con_name = " ".join(
                            os.path.basename(mat).split(".")[0].split("_")
                        )
                        # print("con_name:"+con_name)

                        # Load the connectivity matrix and extract the attributes (weights)
                        # con_mat =  pickle.load(mat, encoding="latin1")
                        con_mat = nx.read_gpickle(mat)
                        con_metrics = list(list(con_mat.edges(data=True))[0][2].keys())

                        # Create dynamically the list of output connectivity metrics for inspection
                        for con_metric in con_metrics:
                            metric_str = " ".join(con_metric.split("_"))
                            self.inspect_outputs_dict[con_name + " - " + metric_str] = [
                                "showmatrix_gpickle",
                                layout,
                                mat,
                                con_metric,
                                "False",
                                self.config.subject
                                + " - "
                                + con_name
                                + " - "
                                + metric_str,
                                map_scale,
                            ]

            self.inspect_outputs = sorted(
                [key for key in list(self.inspect_outputs_dict.keys())], key=str.lower
            )
            # print(self.inspect_outputs)

    def has_run(self):
        """Function that returns `True` if the stage has been run successfully.

        Returns
        -------
        `True` if the stage has been run successfully
        """
        return os.path.exists(
            os.path.join(
                self.stage_dir, "compute_matrice", "result_compute_matrice.pklz"
            )
        )
