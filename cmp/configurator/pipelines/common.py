# Copyright (C) 2009-2017, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" Common functions for CMP pipelines
"""

import os

from traits.api import *
from traitsui.api import *

import apptools.io.api as io

from pyface.qt.QtCore import *
from pyface.qt.QtGui import *
from traitsui.qt4.extra.qt_view import QtView

class Pipeline(HasTraits):
    # informations common to project_info
    base_directory = Directory
    root = Property
    subject = 'sub-01'
    last_date_processed = Str
    last_stage_processed = Str

    # num core settings
    number_of_cores = 1

    anat_flow = None

    traits_view = QtView(Include('pipeline_group'))

    #-- Traits Default Value Methods -----------------------------------------

    # def _base_directory_default(self):
    #     return getcwd()

    #-- Property Implementations ---------------------------------------------

    @property_depends_on('base_directory')
    def _get_root(self):
        return File(path=self.base_directory)

    def __init__(self, project_info):
        self.base_directory = project_info.base_directory
        self.subject = project_info.subject
        self.number_of_cores = project_info.number_of_cores

        for stage in self.stages.keys():
            if len(project_info.subject_sessions)>0:
                self.stages[stage].stage_dir = os.path.join(self.base_directory,"derivatives",'cmp',self.subject,project_info.subject_session,'tmp',self.pipeline_name,self.stages[stage].name)
            else:
                self.stages[stage].stage_dir = os.path.join(self.base_directory,"derivatives",'cmp',self.subject,'tmp',self.pipeline_name,self.stages[stage].name)
            # if self.stages[stage].name == 'segmentation_stage' or self.stages[stage].name == 'parcellation_stage':
            #     #self.stages[stage].stage_dir = os.path.join(self.base_directory,"derivatives",'freesurfer',self.subject,self.stages[stage].name)
            #     self.stages[stage].stage_dir = os.path.join(self.base_directory,"derivatives",'cmp',self.subject,'tmp','nipype','common_stages',self.stages[stage].name)
            # else:
            #     self.stages[stage].stage_dir = os.path.join(self.base_directory,"derivatives",'cmp',self.subject,'tmp','nipype',self.pipeline_name,self.stages[stage].name)

    def check_config(self):
        if self.stages['Segmentation'].config.seg_tool ==  'Custom segmentation':
            if not os.path.exists(self.stages['Segmentation'].config.white_matter_mask):
                return('\nCustom segmentation selected but no WM mask provided.\nPlease provide an existing WM mask file in the Segmentation configuration window.\n')
            if not os.path.exists(self.stages['Parcellation'].config.atlas_nifti_file):
                return('\n\tCustom segmentation selected but no atlas provided.\nPlease specify an existing atlas file in the Parcellation configuration window.\t\n')
            if not os.path.exists(self.stages['Parcellation'].config.graphml_file):
                return('\n\tCustom segmentation selected but no graphml info provided.\nPlease specify an existing graphml file in the Parcellation configuration window.\t\n')
        # if self.stages['MRTrixConnectome'].config.output_types == []:
        #     return('\n\tNo output type selected for the connectivity matrices.\t\n\tPlease select at least one output type in the connectome configuration window.\t\n')
        if self.stages['Connectome'].config.output_types == []:
            return('\n\tNo output type selected for the connectivity matrices.\t\n\tPlease select at least one output type in the connectome configuration window.\t\n')
        return ''

    def create_stage_flow(self, stage_name):
        stage = self.stages[stage_name]
        flow = pe.Workflow(name=stage.name)
        inputnode = pe.Node(interface=util.IdentityInterface(fields=stage.inputs),name="inputnode")
        outputnode = pe.Node(interface=util.IdentityInterface(fields=stage.outputs),name="outputnode")
        flow.add_nodes([inputnode,outputnode])
        stage.create_workflow(flow,inputnode,outputnode)
        return flow

    def fill_stages_outputs(self):
        for stage in self.stages.values():
            if stage.enabled:
                stage.define_inspect_outputs()

    def clear_stages_outputs(self):
        for stage in self.stages.values():
            if stage.enabled:
                stage.inspect_outputs_dict = {}
                stage.inspect_outputs = ['Outputs not available']
