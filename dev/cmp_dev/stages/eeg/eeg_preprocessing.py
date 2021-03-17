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
from dev.cmtklib_dev.interfaces.invsol import CartoolInverseSolutionROIExtraction
from cmtklib.util import get_pipeline_dictionary_outputs

class EEGPreprocessingConfig(HasTraits):

    eeg_format = Str('EEGLAB')

    def update_atlas_info(self):
        """Update `atlas_info` class attribute."""
        atlas_name = os.path.basename(self.atlas_nifti_file)
        atlas_name = os.path.splitext(os.path.splitext(atlas_name)[0])[
            0].encode('ascii')
        self.atlas_info = {
            atlas_name: {'number_of_regions': self.number_of_regions, 'node_information_graphml': self.graphml_file}}

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


class EEGPreprocessingStage(Stage):
    def __init__(self, pipeline_mode, bids_dir, output_dir):
        """Constructor of a :class:`~cmp.stages.parcellation.parcellation.ParcellationStage` instance."""
        self.name = 'eeg_preprocessing_stage'
        self.bids_dir = bids_dir
        self.output_dir = output_dir
        self.config = EEGPreprocessingConfig()
        self.config.pipeline_mode = pipeline_mode
        self.inputs = ["subjects_dir", "subject_id", "eeg_format"]
        self.outputs = ["eeg_data"]

    def create_workflow(self, flow, inputnode, outputnode):
        """Create the stage worflow.

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

        outputnode.inputs.eeg_format = self.config.eeg_format

        def get_basename(path):
            """Return ``os.path.basename()`` of a ``path``.

            Parameters
            ----------
            path : os.path
                Path to extract the containing directory

            Returns
            -------
            path : os.path
                Path to the containing directory
            """
            import os
            path = os.path.basename(path)
            print(path)
            return path

        if self.config.eeg_format == "EEGLAB":

            
            eeglab2fif_node = pe.Node(interface = EEGLAB2fif(
                ), name="eeglab2fif")
            
            
            flow.connect([
                (inputnode, eeglab2fif_node,
                    [('epochs','eeg_ts_file'),
                    ('behav','behav_file'),
                    ('epochs_fif','epochs_fif_fname'),
                    ])
                ])        

    def define_inspect_outputs(self):
        """Update the `inspect_outputs' class attribute.

        It contains a dictionary of stage outputs with corresponding commands for visual inspection.
        """
        eeg_sinker_dir = os.path.join(os.path.dirname(self.stage_dir), 'eeg_sinker')
        eeg_sinker_report = os.path.join(eeg_sinker_dir, '_report', 'report.rst')

        """if self.config.eeg_format == "EEGLAB":
                                    if os.path.exists(eeg_sinker_report):
                                        eeg_outputs = get_pipeline_dictionary_outputs(eeg_sinker_report, self.output_dir)
        """

        raise NotImplementedError


    def has_run(self):
        """Function that returns `True` if the stage has been run successfully.

        Returns
        -------
        `True` if the stage has been run successfully
        """
        if self.config.eeg_format == "EEGLAB":            
            return os.path.exists(self.config.epochs_fif)
