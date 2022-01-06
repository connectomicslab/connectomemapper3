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


class ProgressWindow(HasTraits):
    """Progress window of stage execution

    (Not used anymore by CMP3)
    """

    main_status = Str("Processing launched...")
    stages_status = List([""])


class ProgressThread(threading.Thread):
    """Class use to monitor stage execution in a :class:`threading.Thread`.

    Information is display in the ProgressWindow
    (Not used anymore by CMP3)
    """

    stages = {}
    stage_names = []
    pw = Instance(ProgressWindow)

    def run(self):
        """Monitors stage execution a workflow."""
        c = 0

        while c < len(self.stage_names):
            time.sleep(5)
            c = 0
            statuses = []
            for stage in self.stage_names:
                if self.stages[stage].enabled:
                    if self.stages[stage].has_run():
                        statuses.append(stage + " stage finished!")
                        c = c + 1
                    elif self.stages[stage].is_running():
                        statuses.append(stage + " stage running...")
                    else:
                        statuses.append(stage + " stage waiting...")
                else:
                    c = c + 1
                    statuses.append(stage + " stage not selected for running!")
            self.pw.stages_status = statuses
        self.pw.main_status = "Processing finished!"
        self.pw.stages_status = ["All stages finished!"]


class ProcessThread(threading.Thread):
    """Class use to represent the pipeline process as a :class:`threading.Thread`.

    Attributes
    ----------
    pipeline <Instance>
         Any Pipeline instance
    """

    pipeline = Instance(Any)

    def run(self):
        """Execute the pipeline."""
        self.pipeline.process()


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
            # if self.stages[stage].name == 'segmentation_stage' or self.stages[stage].name == 'parcellation_stage':
            #     #self.stages[stage].stage_dir = os.path.join(self.base_directory,"derivatives",
            #                                                  'freesurfer',self.subject,self.stages[stage].name)
            #     self.stages[stage].stage_dir = os.path.join(self.base_directory,"derivatives",
            #                                                 'cmp',self.subject,'tmp','nipype','common_stages',self.stages[stage].name)
            # else:
            #     self.stages[stage].stage_dir = os.path.join(self.base_directory,"derivatives",
            #                                                 'cmp',self.subject,'tmp','nipype',self.pipeline_name,self.stages[stage].name)

    def check_config(self):
        """Old method that was checking custom settings (obsolete).

        Returns
        -------

        """
        # if self.stages['Segmentation'].config.seg_tool == 'Custom segmentation':
        #     if not os.path.exists(self.stages['Segmentation'].config.white_matter_mask):
        #         return (
        #             '\nCustom segmentation selected but no WM mask provided.\n'
        #             'Please provide an existing WM mask file in the Segmentation configuration window.\n')
        #     if not os.path.exists(self.stages['Parcellation'].config.atlas_nifti_file):
        #         return (
        #             '\n\tCustom segmentation selected but no atlas provided.\n'
        #             'Please specify an existing atlas file in the Parcellation configuration window.\t\n')
        #     if not os.path.exists(self.stages['Parcellation'].config.graphml_file):
        #         return (
        #             '\n\tCustom segmentation selected but no graphml info provided.\n'
        #             'Please specify an existing graphml file in the Parcellation configuration window.\t\n')
        # if self.stages['MRTrixConnectome'].config.output_types == []:
        #     return('\n\tNo output type selected for the connectivity matrices.\t\n\t'
        #            'Please select at least one output type in the connectome configuration window.\t\n')
        if not self.stages["Connectome"].config.output_types:
            return (
                "\n\tNo output type selected for the connectivity matrices.\t\n\t"
                "Please select at least one output type in the connectome configuration window.\t\n"
            )
        return ""

    def create_stage_flow(self, stage_name):
        """Create the sub-workflow of a processing stage.

        Parameters
        ----------
        stage_name

        Returns
        -------

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

    def check_stages_execution(self):
        """Check stage execution."""
        for stage in list(self.stages.values()):
            if stage.has_run():
                print(f"{stage} stage finished!")
            if stage.is_running():
                print(f"{stage} stage running...")

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

    def launch_process(self):
        """Launch the processing."""
        pt = ProcessThread()
        pt.pipeline = self
        pt.start()
