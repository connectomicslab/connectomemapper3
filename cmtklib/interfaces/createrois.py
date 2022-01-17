import pycartool as cart
import nibabel
import os
import pickle
import numpy as np
from nipype.interfaces.base import BaseInterface, BaseInterfaceInputSpec, traits, TraitedSpec


class CreateRoisInputSpec(BaseInterfaceInputSpec):
    """Input specification for InverseSolution."""

    subject = traits.Str(
        desc='subject', mandatory=True)
    
    bids_dir = traits.Str(
        desc='base directory', mandatory=True)

    parcellation = traits.Str(
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

    output_query = traits.Dict(
        desc='BIDSDataGrabber output_query', mandatory=True)

    derivative_list = traits.List(
        exists=True, desc='List of derivatives to add to the datagrabber', mandatory=True)


class CreateRois(BaseInterface):
    input_spec = CreateRoisInputSpec
    output_spec = CreateRoisOutputSpec

    def _run_interface(self, runtime):
        subject = self.inputs.subject
        parcellation_image_path = self.inputs.parcellation
        parcellation_name = parcellation_image_path.split('/')[-1].split('.')[0]
        cartool_dir = os.path.join(self.inputs.bids_dir,'derivatives',self.inputs.cartool_dir)
        cmp3_dir = os.path.join(self.inputs.bids_dir,'derivatives',self.inputs.cmp3_dir)
        self.derivative_list = self.inputs.derivative_list
        self.output_query = self.inputs.output_query

        self._create_roi_files(subject, parcellation_image_path, parcellation_name, cartool_dir, cmp3_dir)

        self.derivative_list.append('cartool-v3.80')

        self.output_query['rois'] = {
            # 'scope': 'cartool-v3.80',
            'extension': ['pickle.rois']
        }
        self.output_query['src'] = {
            # 'scope': 'cartool-v3.80',
            'extension': ['spi']
        }
        self.output_query['invsol'] = {
            # 'scope': 'cartool-v3.80',
            'extension': ['LAURA.is']
        }

        return runtime

    @staticmethod
    def _create_roi_files(subject, parcellation, parcellation_name, cartool_dir, cmp3_dir):
        spipath = os.path.join(cartool_dir, subject, subject + '.spi')
        source = cart.source_space.read_spi(spipath)

        impath = os.path.join(parcellation)
        im = nibabel.load(impath)
        imdata = im.get_fdata()
        x, y, z = np.where(imdata)
        center_brain = [np.mean(x), np.mean(y), np.mean(z)]
        source.coordinates[:, 0] = - source.coordinates[:, 0]
        source.coordinates = source.coordinates - source.coordinates.mean(0) + center_brain

        xyz = source.get_coordinates()
        xyz = np.round(xyz).astype(int)
        num_spi = len(xyz)

        # label positions
        rois_file = np.zeros(num_spi)
        x_roi, y_roi, z_roi = np.where((imdata > 0) & (imdata < np.unique(imdata)[-1]))

        # For each coordinate
        for spi_id, spi in enumerate(xyz):
            distances = ((spi.reshape(-1, 1) - [x_roi, y_roi, z_roi]) ** 2).sum(0)
            roi_id = np.argmin(distances)
            rois_file[spi_id] = imdata[x_roi[roi_id], y_roi[roi_id], z_roi[roi_id]]

        groups_of_indexes = [np.where(rois_file == roi)[0].tolist() for roi in np.unique(rois_file)]
        names = [str(int(i)) for i in np.unique(rois_file) if i != 0]

        rois_file_new = cart.regions_of_interest.RegionsOfInterest(names=names,
                                                                   groups_of_indexes=groups_of_indexes,
                                                                   source_space=source)

        if not os.path.isdir(os.path.join(cartool_dir, subject, 'Rois')):
            os.mkdir(os.path.join(cartool_dir, subject, 'Rois'))
        filename_pkl = os.path.join(cartool_dir, subject, 'Rois', parcellation_name + '.pickle.rois')
        filehandler = open(filename_pkl, 'wb')
        pickle.dump(rois_file_new, filehandler)
        filehandler.close()

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['output_query'] = self.output_query
        outputs['derivative_list'] = self.derivative_list
        return outputs
