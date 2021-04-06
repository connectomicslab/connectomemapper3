import pycartool as cart
import nibabel
import os
import pickle
import numpy as  np
import mne 
from nipype.interfaces.base import BaseInterface, BaseInterfaceInputSpec, traits, TraitedSpec, InputMultiPath

class CreateRoisInputSpec(BaseInterfaceInputSpec):
    """Input specification for InverseSolution."""

    subject_id = traits.Str(
        desc='subject id', mandatory=True)

    parcellation = traits.List(
        desc='parcellation scheme', mandatory=True)

    cartool_dir = traits.Str(
        desc='Cartool directory', mandatory=True)

    cmp3_dir = traits.Str(
        desc='CMP3 directory', mandatory=True)

    output_query = traits.Dict(
        desc='BIDSDataGrabber output_query', mandatory=True)

    derivative_list = traits.List(
            exists=True, desc='List of derivatives to add to the datagrabber', mandatory=True)

class CreateRoisOutputSpec(TraitedSpec):
    """Output specification for InverseSolution."""

    #rois_pickle = traits.File(
    #    exists=True, desc='rois file, loaded with pickle', mandatory=True)

    output_query = traits.Dict(
        desc='BIDSDataGrabber output_query', mandatory=True)

    derivative_list = traits.List(
            exists=True, desc='List of derivatives to add to the datagrabber', mandatory=True)
    

class CreateRois(BaseInterface):

    input_spec = CreateRoisInputSpec
    output_spec = CreateRoisOutputSpec

    def _run_interface(self, runtime):
        subject_id = 'sub-'+self.inputs.subject_id
        parcellation_image_path = self.inputs.parcellation[0]
        parcellation_name = parcellation_image_path.split('/')[-1].split('.')[0]
        cartool_dir = self.inputs.cartool_dir
        cmp3_dir = self.inputs.cmp3_dir
        self.derivative_list = self.inputs.derivative_list
        self.output_query = self.inputs.output_query        

        self._create_roi_files(subject_id, parcellation_image_path, parcellation_name, cartool_dir, cmp3_dir)

        self.derivative_list.append('Cartool')

        self.output_query['rois'] = {
                                     'scope': 'Cartool',
                                     'extensions': ['pickle.rois']
                                     }
        self.output_query['src'] = {
                                    'scope': 'Cartool',
                                    'extensions': ['spi']
                                    }
        self.output_query['invsol'] = {
                                    'scope': 'Cartool',
                                    'extensions': ['LAURA.is']
                                    }

        return runtime

    def _create_roi_files(self, subject_id, parcellation, parcellation_name, cartool_dir, cmp3_dir):

        spipath = os.path.join(cartool_dir, subject_id, subject_id + '.spi')
        source = cart.source_space.read_spi(spipath)
        brain_cartool = os.path.join(cartool_dir,subject_id,subject_id+'.Brain.nii')
        brain_cartool = nibabel.load(brain_cartool)
        bc = brain_cartool.get_fdata()[:,:,:,0]
           
        #impath = os.path.join(cmp3_dir,subject_id,'anat',subject_id+'_label-'+parcellation+'_atlas.nii.gz')
        impath = os.path.join(parcellation)
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

        filename_pkl = os.path.join(cartool_dir, subject_id, 'Rois', parcellation_name + '.pickle.rois')
        filehandler = open(filename_pkl, 'wb') 
        pickle.dump(rois_file_new, filehandler)
        filehandler.close()

        """filename = os.path.join(cartool_dir, subject_id, 'Rois', parcellation_name + '.rois')
                                with open(filename, "w") as text_file:
                                    print("{}".format(num_spi), file=text_file)
                                    print("RO01", file=text_file)
                                    print("{}".format(len(names)), file=text_file)
                                    for i in range(len(names)):
                                        print("{}".format(names[i]), file=text_file)
                                        print(" ".join([str(elem) for elem in groups_of_indexes[i]]), file=text_file)"""

        #return filename_pkl
    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['output_query'] = self.output_query
        outputs['derivative_list'] = self.derivative_list
        return outputs
