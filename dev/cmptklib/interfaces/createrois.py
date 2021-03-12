import pycartool as cart
import nibabel

import pickle
import numpy as  np
import mne 
from nipype.interfaces.base import BaseInterface, BaseInterfaceInputSpec, traits, TraitedSpec, InputMultiPath

class CreateRoisInputSpec(BaseInterfaceInputSpec):
	"""Input specification for InverseSolution."""

	subject_id = traits.Str(
		desc='subject id', mandatory=True)

	parcellation = traits.Str(
		desc='parcellation scheme', mandatory=True)

	cartool_dir = traits.File(
		exists=True, desc='Cartool directory', mandatory=True)

	cmp3_dir = traits.Directory(
		exists=True, desc='CMP3 directory', mandatory=True)

class CreateRoisOutputSpec(TraitedSpec):
	"""Output specification for InverseSolution."""

	rois_pickle = traits.File(
		exists=True, desc='rois file, loaded with pickle', mandatory=True)


class CreateRois(BaseInterface):


	input_spec = CreateRoisInputSpec
	output_spec = CreateRoisOutputSpec


	def _run_interface(self, runtime):

		subject_id = self.inputs.subject_id
		parcellation = self.inputs.parcellation
		cartool_dir = self.inputs.cartool_dir
		cmp3_dir = self.inputs.cmp3_dir

		self.rois_pickle = _create_roi_files(subject_id, parcellation, 
											 cartool_dir, cmp3_dir):

		return runtime

	def _create_roi_files(self, subject_id, parcellation, cartool_dir, cmp3_dir):
	           
        spipath = os.path.join(cartool_dir,subject_id,subject_id+'.spi')
        source = cart.source_space.read_spi(spipath)
        brain_cartool = os.path.join(cartool_dir,subject_id,subject_id+'.Brain.nii')
        brain_cartool = nibabel.load(brain_cartool)
        bc = brain_cartool.get_fdata()[:,:,:,0]
           
        impath = os.path.join(cmp3_dir,subject_id,'anat',subject_id+'_label-'+parcellation+'_atlas.nii.gz')
        im = nibabel.load(impath)
        imdata = im.get_fdata()

        x,y,z = np.where(imdata)
        center_brain = [np.mean(x),np.mean(y),np.mean(z)]
        source.coordinates[:,0] = - source.coordinates[:,0]
        source.coordinates = source.coordinates -source.coordinates.mean(0) + center_brain

        xyz = source.get_coordinates()        
        xyz = np.round(xyz).astype(int)
        num_spi = len(xyz)

        # label positions
        rois_file = np.zeros(num_spi)
        x_roi,y_roi,z_roi = np.where((imdata>0)&(imdata<np.unique(imdata)[-1]))

        # For each coordinate
        for spi_id,spi in enumerate(xyz):
            distances = ((spi.reshape(-1,1)-[x_roi,y_roi,z_roi])**2).sum(0)
            roi_id = np.argmin(distances)            
            rois_file[spi_id] = imdata[x_roi[roi_id],y_roi[roi_id],z_roi[roi_id]]

        groups_of_indexes = [np.where(rois_file==roi)[0].tolist() for roi in np.unique(rois_file)]
        names = [str(int(i)) for i in np.unique(rois_file) if i!=0] 

        rois_file_new = cart.regions_of_interest.RegionsOfInterest(names = names,
                                                                   groups_of_indexes=groups_of_indexes,
                                                                   source_space=source)        

        filename_pkl = os.path.join(cartool_dir,subject_id,'Rois',subject_id+'_label-'+parcellation+'.pickle.rois')
        filehandler = open(filename_pkl, 'wb') 
        pickle.dump(rois_file_new, filehandler)
        filehandler.close()
                
        
        filename = os.path.join(cartool_dir,subject_id,'Rois',subject_id+'_label-'+parcellation+'.rois')
        with open(filename, "w") as text_file:
            print("{}".format(num_spi), file=text_file)
            print("RO01", file=text_file)
            print("{}".format(len(names)), file=text_file)
            for i in range(len(names)):
                print("{}".format(names[i]), file=text_file)
                print(" ".join([str(elem) for elem in groups_of_indexes[i]]), file=text_file)
	    
	    return filename_pkl
	def _list_outputs(self):
		outputs = self._outputs().get()
		outputs['rois_pickle'] = self.rois_pickle
		return outputs