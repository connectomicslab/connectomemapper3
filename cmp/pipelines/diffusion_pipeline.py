
import os
from common import *
try: 
	from traits.api import *
except ImportError: 
	from enthought.traits.api import *
import nipype.pipeline.engine as pe
import nipype.interfaces.io as nio

from cmp.stages.preprocessing.preprocessing import Preprocessing
from cmp.stages.segmentation.segmentation import Segmentation
from cmp.stages.parcellation.parcellation import Parcellation
from cmp.stages.diffusion.diffusion import Diffusion
from cmp.stages.registration.registration import Registration
from cmp.stages.connectome.connectome import Connectome

def get_stages():
	stages = {'Preprocessing':Preprocessing(process_type='Diffusion'), 'Segmentation':Segmentation(), 
			'Parcellation':Parcellation(), 'Diffusion':Diffusion(), 'Registration':Registration(), 'Connectome':Connectome()}
	
	return stages
	
def preprocess(project):
	print '**** Preprocessing ****'
	diffusion_available = False
	t1_available = False
	t2_available = False
	
	# Check for (and if existing, convert) diffusion data
	diffusion_model = []
	for model in ['DSI','DTI','HARDI']:
		input_dir = os.path.join(project.base_directory,'RAWDATA',model)
		if len(os.listdir(input_dir)) > 0:
			if convert_rawdata(project.base_directory, input_dir):
				diffusion_available = True
				diffusion_model.append(model)
	
	# Check for (and if existing, convert)  T1
	input_dir = os.path.join(project.base_directory,'RAWDATA','T1')
	if len(os.listdir(input_dir)) > 0:
		if convert_rawdata(project.base_directory, input_dir):
			t1_available = True
			
	# Check for (and if existing, convert)  T2
	input_dir = os.path.join(project.base_directory,'RAWDATA','T2')
	if len(os.listdir(input_dir)) > 0:
		if convert_rawdata(project.base_directory, input_dir):
			t2_available = True	
			
	if diffusion_available:
		project.stages['Diffusion'].config.imaging_model_choices = diffusion_model
		if t2_available:
		    swap_and_reorient(project.base_directory,os.path.join(project.base_directory,'NIFTI','T2.nii.gz'),
		        os.path.join(project.base_directory,'NIFTI',diffusion_model[0]+'.nii.gz'))
		if t1_available:
			swap_and_reorient(project.base_directory,os.path.join(project.base_directory,'NIFTI','T1.nii.gz'),
			    os.path.join(project.base_directory,'NIFTI',diffusion_model[0]+'.nii.gz'))
			return True, 'Preprocessing finished successfully.\nDiffusion and morphological data available.'
		else:
			project.stages['Segmentation'].enabled = False
			project.stages['Parcellation'].enabled = False
			return True, 'Preprocessing finished with warnings.\nMorphological data not available, morphological workflows will not run.'
	elif t1_available:
		project.stages['Diffusion'].enabled = False
		return True, 'Preprocessing finished with warnings.\nDiffusion data not available, diffusion workflows will not run.'
		
	return False, 'Error during preprocessing. No diffusion or morphological data available in folder '+os.path.join(project.base_directory,'RAWDATA')+'!'
			
	
def process(project):
	print '**** Processing ****'
	flow = pe.Workflow(name='diffusion_pipeline', base_dir=os.path.join(project.base_directory,'NIPYPE'))
	
	# Data import
	datasource = pe.Node(interface=nio.DataGrabber(outfields = ['DSI','DTI','HARDI','T1','T2']), name='datasource')
	datasource.inputs.base_directory = os.path.join(project.base_directory,'NIFTI')
	#datasource.inputs.outfields = ['DSI','DTI','HARDI','T1','T2']
	datasource.inputs.template = '*'
	datasource.inputs.raise_on_empty = False
	datasource.inputs.field_template = dict(DSI='DSI.nii.gz',DTI='DTI.nii.gz',HARDI='HARDI.nii.gz',T1='T1.nii.gz',T2='T2.nii.gz')
	
	
	# create sub workflows that will exist anyway
	#reg_flow = project.stages['Registration'].create_worfklow()
	#con_flow = project.stages['Connectome'].create_worfklow()
	
	if project.stages['Diffusion'].enabled:
		diff_flow = project.stages['Diffusion'].create_workflow()
		flow.connect([(datasource,diff_flow, [('DSI','inputnode.DSI'),('DTI','inputnode.DTI'),('HARDI','inputnode.HARDI')])])
		
	flow.run()
	
	flow.save(os.path.join(project.base_directory,'workflow'))
	
	return True,'Processing sucessful'
		
		
