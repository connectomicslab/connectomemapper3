# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""Definition of common parent classes for pipelines."""

import os
import threading
import time

from traits.api import *

import nipype.pipeline.engine as pe
import nipype.interfaces.utility as util
from nipype.interfaces.base import File, Directory

from cmtklib.bids.io import __nipype_directory__


class Pipeline(HasTraits):
    """Parent class that extends `HasTraits` and represents a processing pipeline.

    It is extended by the various pipeline classes.

    See Also
    --------
    cmp.pipelines.anatomical.anatomical.AnatomicalPipeline
    cmp.pipelines.diffusion.diffusion.DiffusionPipeline
    cmp.pipelines.functional.fMRI.fMRIPipeline
    """

    # informations common to project_info
    base_directory = Directory
    output_directory = Directory

    root = Property
    subject = "sub-01"
    last_date_processed = Str
    last_stage_processed = Str

    # num core settings
    number_of_cores = 1

    anat_flow = None

    # -- Property Implementations ---------------------------------------------
    @property_depends_on("base_directory")
    def _get_root(self):
        return File(path=self.base_directory)

    def __init__(self, project_info):
        self.base_directory = project_info.base_directory
        self.number_of_cores = project_info.number_of_cores

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

    def create_stage_flow(self, stage_name):
        """Create the sub-workflow of a processing stage.

        Parameters
        ----------
        stage_name : str
            Stage name

        Returns
        -------
        flow : nipype.pipeline.engine.Workflow
            Created stage sub-workflow

        """
        stage = self.stages[stage_name]
        flow = pe.Workflow(name=stage.name)
        inputnode = pe.Node(
            interface=util.IdentityInterface(fields=stage.inputs), name="inputnode"
        )
        outputnode = pe.Node(
            interface=util.IdentityInterface(fields=stage.outputs), name="outputnode"
        )
        flow.add_nodes([inputnode, outputnode])
        stage.create_workflow(flow, inputnode, outputnode)
        return flow

    def fill_stages_outputs(self):
        """Update processing stage output list for visual inspection."""
        for stage in list(self.stages.values()):
            if stage.enabled:
                stage.define_inspect_outputs()

    def clear_stages_outputs(self):
        """Clear processing stage outputs."""
        for stage in list(self.stages.values()):
            if stage.enabled:
                stage.inspect_outputs_dict = {}
                stage.inspect_outputs = ["Outputs not available"]
                # Remove result_*.pklz files to clear them from visualisation drop down list
                # stage_results = [os.path.join(dirpath, f)
                #                 for dirpath, dirnames, files in os.walk(stage.stage_dir)
                #                 for f in fnmatch.filter(files, 'result_*.pklz')]
                # for stage_res in stage_results:
                #    os.remove(stage_res)
