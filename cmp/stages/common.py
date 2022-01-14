# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""Definition of common parent classes for stages."""

# Libraries imports
import os

from traits.api import *


class Stage(HasTraits):
    """Parent class that extends `HasTraits`  and represents a processing pipeline stage.

    It is extended by the various pipeline stage subclasses.

    Attributes
    ----------
    bids_subject_label : traits.Str
        BIDS subject (participant) label

    bids_session_label : traits.Str
        BIDS session label

    bids_dir : traits.Str
        BIDS dataset root directory

    output_dir : traits.Str
        Output directory

    inspect_outputs : traits.Dict
        Dictionary of stage outputs with corresponding commands for visual inspection
        (Initialization: 'Outputs not available')

    inspect_outputs_enum : traits.Enum
        Choice of output to be visually inspected
        (values='inspect_outputs')

    enabled : traits.Bool
        Stage enabled in the pipeline
        (Default: True)

    config : Instance(HasTraits)
        Instance of stage configuration

    See Also
    --------
    cmp.stages.preprocessing.preprocessing.PreprocessingStage
    cmp.stages.diffusion.diffusion.DiffusionStage
    cmp.stages.registration.registration.RegistrationStage
    cmp.stages.connectome.connectome.ConnectomeStage
    cmp.stages.preprocessing.fmri_preprocessing.PreprocessingStage
    cmp.stages.functional.functionalMRI.FunctionalMRIStage
    cmp.stages.connectome.fmri_connectome.ConnectomeStage
    """

    bids_subject_label = Str(desc="BIDS subject (participant) label")
    bids_session_label = Str("", desc="BIDS session label")
    bids_dir = Str
    output_dir = Str
    inspect_outputs = ["Outputs not available"]
    inspect_outputs_enum = Enum(values="inspect_outputs")
    inspect_outputs_dict = Dict
    enabled = True
    config = Instance(HasTraits)

    def is_running(self):
        """Return the number of unfinished files in the stage.

        Returns
        -------
        nb_of_unfinished_files : int
            Number of unfinished files in the stage
        """
        unfinished_files = [
            os.path.join(dirpath, f)
            for dirpath, dirnames, files in os.walk(self.stage_dir)
            for f in files
            if f.endswith("_unfinished.json")
        ]
        nb_of_unfinished_files = len(unfinished_files)
        return nb_of_unfinished_files
