# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""Module that defines CMTK Nipype interfaces for the Functional MRI pipeline."""

# General imports
from traits.api import *
import os
import numpy as np
import nibabel as nib
import scipy.io as sio
from nipype.interfaces.base import (
    BaseInterface,
    BaseInterfaceInputSpec,
    TraitedSpec,
    InputMultiPath,
)


class DiscardTPInputSpec(BaseInterfaceInputSpec):
    in_file = File(exists=True, mandatory=True, desc="Input 4D fMRI image")

    n_discard = Int(mandatory=True, desc="Number of n first frames to discard")


class DiscardTPOutputSpec(TraitedSpec):
    out_file = File(exists=True, desc="Output 4D fMRI image with discarded frames")


class DiscardTP(BaseInterface):
    """Discards the n first time frame in functional MRI data.

    Examples
    --------
    >>> from cmtklib.functionalMRI import DiscardTP
    >>> discard = DiscardTP()
    >>> discard.inputs.base_dir = '/my_directory'
    >>> discard.inputs.in_file = '/path/to/sub-01_task-rest_desc-preproc_bold.nii.gz'
    >>> discard.inputs.n_discard = 5
    >>> discard.run()  # doctest: +SKIP

    """

    input_spec = DiscardTPInputSpec
    output_spec = DiscardTPOutputSpec

    def _run_interface(self, runtime):
        dataimg = nib.load(self.inputs.in_file)
        data = dataimg.get_data()

        n_discard = int(self.inputs.n_discard) - 1

        new_data = data.copy()
        new_data = new_data[:, :, :, n_discard:-1]

        hd = dataimg.get_header()
        hd.set_data_shape(
            [
                hd.get_data_shape()[0],
                hd.get_data_shape()[1],
                hd.get_data_shape()[2],
                hd.get_data_shape()[3] - n_discard - 1,
            ]
        )
        img = nib.Nifti1Image(new_data, dataimg.get_affine(), hd)
        nib.save(img, os.path.abspath("fMRI_discard.nii.gz"))
        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["out_file"] = os.path.abspath("fMRI_discard.nii.gz")
        return outputs


class NuisanceRegressionInputSpec(BaseInterfaceInputSpec):
    in_file = File(exists=True, desc="Input fMRI volume")

    brainfile = File(desc="Eroded brain mask registered to fMRI space")

    csf_file = File(desc="Eroded CSF mask registered to fMRI space")

    wm_file = File(desc="Eroded WM mask registered to fMRI space")

    motion_file = File(desc="motion nuisance effect")

    gm_file = InputMultiPath(File(), desc="GM atlas files registered to fMRI space")

    global_nuisance = Bool(desc="If `True` perform global nuisance regression")

    csf_nuisance = Bool(desc="If `True` perform CSF nuisance regression")

    wm_nuisance = Bool(desc="If `True` perform WM nuisance regression")

    motion_nuisance = Bool(desc="If `True` perform motion nuisance regression")

    nuisance_motion_nb_reg = Int(
        "36", desc="Number of reg to use in motion nuisance regression"
    )

    n_discard = Int(
        desc="Number of volumes discarded from the fMRI sequence during preprocessing"
    )


class NuisanceRegressionOutputSpec(TraitedSpec):
    out_file = File(exists=True, desc="Output fMRI Volume")

    averageGlobal_npy = File(desc="Output of global regression in `.npy` format")

    averageCSF_npy = File(desc="Output of CSF regression in `.npy` format")

    averageWM_npy = File(desc="Output of WM regression in `.npy` format")

    averageGlobal_mat = File(desc="Output matrix of global regression")

    averageCSF_mat = File(desc="Output matrix of CSF regression")

    averageWM_mat = File(desc="Output matrix of WM regression")


class NuisanceRegression(BaseInterface):
    """Regress out nuisance signals (WM, CSF, movements) through GLM.

    Examples
    --------
    >>> from cmtklib.functionalMRI import NuisanceRegression
    >>> nuisance = NuisanceRegression()
    >>> nuisance.inputs.base_dir = '/my_directory'
    >>> nuisance.inputs.in_file = '/path/to/sub-01_task-rest_desc-preproc_bold.nii.gz'
    >>> nuisance.inputs.wm_file = '/path/to/sub-01_task-rest_desc-preproc_bold.nii.gz'
    >>> nuisance.inputs.csf_file = '/path/to/sub-01_task-rest_desc-preproc_bold.nii.gz'
    >>> nuisance.inputs.motion_file = '/path/to/sub-01_motions.par'
    >>> nuisance.inputs.gm_file = ['/path/to/sub-01_space-meanBOLD_atlas-L2018_desc-scale1_dseg.nii.gz',
    >>>                            '/path/to/sub-01_space-meanBOLD_atlas-L2018_desc-scale2_dseg.nii.gz',
    >>>                            '/path/to/sub-01_space-meanBOLD_atlas-L2018_desc-scale3_dseg.nii.gz',
    >>>                            '/path/to/sub-01_space-meanBOLD_atlas-L2018_desc-scale4_dseg.nii.gz',
    >>>                            '/path/to/sub-01_space-meanBOLD_atlas-L2018_desc-scale5_dseg.nii.gz']
    >>> nuisance.inputs.global_nuisance = False
    >>> nuisance.inputs.csf_nuisance = True
    >>> nuisance.inputs.wm_nuisance = True
    >>> nuisance.inputs.motion_nuisance = True
    >>> nuisance.inputs.nuisance_motion_nb_reg = 36
    >>> nuisance.inputs.n_discard = 5
    >>> nuisance.run()  # doctest: +SKIP

    """

    input_spec = NuisanceRegressionInputSpec
    output_spec = NuisanceRegressionOutputSpec

    def _run_interface(self, runtime):
        # Output from previous preprocessing step
        ref_path = self.inputs.in_file

        # Extract whole brain average signal
        dataimg = nib.load(ref_path)
        data = dataimg.get_data()
        tp = data.shape[3]
        if self.inputs.global_nuisance:
            brainfile = self.inputs.brainfile  # load eroded whole brain mask
            brain = nib.load(brainfile).get_data().astype(np.uint32)
            global_values = data[brain == 1].mean(axis=0)
            global_values = global_values - np.mean(global_values)
            np.save(os.path.abspath("averageGlobal.npy"), global_values)
            sio.savemat(
                os.path.abspath("averageGlobal.mat"), {"avgGlobal": global_values}
            )

        # Extract CSF average signal
        if self.inputs.csf_nuisance:
            csffile = self.inputs.csf_file  # load eroded CSF mask
            csf = nib.load(csffile).get_data().astype(np.uint32)
            csf_values = data[csf == 1].mean(axis=0)
            csf_values = csf_values - np.mean(csf_values)
            np.save(os.path.abspath("averageCSF.npy"), csf_values)
            sio.savemat(os.path.abspath("averageCSF.mat"), {"avgCSF": csf_values})

        # Extract WM average signal
        if self.inputs.wm_nuisance:
            WMfile = self.inputs.wm_file  # load eroded WM mask
            WM = nib.load(WMfile).get_data().astype(np.uint32)
            wm_values = data[WM == 1].mean(axis=0)
            wm_values = wm_values - np.mean(wm_values)
            np.save(os.path.abspath("averageWM.npy"), wm_values)
            sio.savemat(os.path.abspath("averageWM.mat"), {"avgWM": wm_values})

        # Import parameters from head motion estimation
        if self.inputs.motion_nuisance:
            move = np.genfromtxt(self.inputs.motion_file)
            move = move - np.mean(move, 0)

            # Update
            move_der1 = np.concatenate((np.zeros([1, 6]), move[0:-1, :]), axis=0)
            move_der2 = np.concatenate((np.zeros([2, 6]), move[0:-2, :]), axis=0)
            move_sq = np.square(move)
            move_der1_sq = np.square(move_der1)
            move_der2_sq = np.square(move_der2)

            move_der1 = move_der1 - np.mean(move_der1)
            move_der2 = move_der2 - np.mean(move_der2)
            move_der1_sq = move_der1_sq - np.mean(move_der1_sq)
            move_der2_sq = move_der2_sq - np.mean(move_der2_sq)
            move_sq = move_sq - np.mean(move_sq)

            if (
                self.inputs.nuisance_motion_nb_reg == "12"
                or self.inputs.nuisance_motion_nb_reg == "24"
                or self.inputs.nuisance_motion_nb_reg == "36"
            ):
                move = np.hstack((move, move_sq))
            if (
                self.inputs.nuisance_motion_nb_reg == "24"
                or self.inputs.nuisance_motion_nb_reg == "36"
            ):
                move = np.hstack((move, move_der1))
                move = np.hstack((move, move_der1_sq))
            if self.inputs.nuisance_motion_nb_reg == "36":
                move = np.hstack((move, move_der2))
                move = np.hstack((move, move_der2_sq))

        # GLM: regress out nuisance covariates
        new_data = data.copy()

        # s = gconf.parcellation.keys()[0]

        gm = nib.load(self.inputs.gm_file[0]).get_data().astype(np.uint32)
        # if float(self.inputs.n_discard) > 0:
        #     n_discard = int(self.inputs.n_discard) - 1
        #     if self.inputs.motion_nuisance:
        #         move = move[n_discard:-1,:]

        # build regressors matrix
        if self.inputs.global_nuisance:
            X = np.hstack(global_values.reshape(tp, 1))
            print("> Detrend global average signal")
            if self.inputs.csf_nuisance:
                X = np.hstack((X.reshape(tp, 1), csf_values.reshape(tp, 1)))
                print("... Detrend CSF average signal")
                if self.inputs.wm_nuisance:
                    X = np.hstack((X, wm_values.reshape(tp, 1)))
                    print("... ... Detrend WM average signal")
                    if self.inputs.motion_nuisance:
                        print("... ... ... pre-Detrend motion average signals")
                        X = np.hstack((X, move))
                        print("... ... ... Detrend motion average signals")
                elif self.inputs.motion_nuisance:
                    X = np.hstack((X, move))
                    print("... ... Detrend motion average signals")
            elif self.inputs.wm_nuisance:
                X = np.hstack((X.reshape(tp, 1), wm_values.reshape(tp, 1)))
                print("... Detrend WM average signal")
                if self.inputs.motion_nuisance:
                    X = np.hstack((X, move))
                    print("... ... Detrend motion average signals")
            elif self.inputs.motion_nuisance:
                X = np.hstack((X.reshape(tp, 1), move))
                print("... Detrend motion average signals")
        elif self.inputs.csf_nuisance:
            X = np.hstack((csf_values.reshape(tp, 1)))
            print("> Detrend CSF average signal")
            if self.inputs.wm_nuisance:
                X = np.hstack((X.reshape(tp, 1), wm_values.reshape(tp, 1)))
                print("... Detrend WM average signal")
                if self.inputs.motion_nuisance:
                    X = np.hstack((X, move))
                    print("... ... Detrend motion average signals")
            elif self.inputs.motion_nuisance:
                X = np.hstack((X.reshape(tp, 1), move))
                print("... Detrend motion average signals")
        elif self.inputs.wm_nuisance:
            X = np.hstack((wm_values.reshape(tp, 1)))
            print("> Detrend WM average signal")
            if self.inputs.motion_nuisance:
                print("... pre-Detrend motion average signals")
                # print('... move shape :',move.shape)
                # print('... X shape :',X.shape)
                Y = X.reshape(tp, 1)
                # print('... Y shape :',Y.shape)
                X = np.hstack((Y, move))
                print("... Detrend motion average signals")
        elif self.inputs.motion_nuisance:
            X = move
            print("> Detrend motion average signals")

        import statsmodels.api as sm

        X = sm.add_constant(X)
        # print('Shape X GLM')
        # print(X.shape)

        # loop throughout all GM voxels
        for index, _ in np.ndenumerate(gm):
            Y = data[index[0], index[1], index[2], :].reshape(tp, 1)
            gls_model = sm.GLS(Y, X)
            gls_results = gls_model.fit()
            # new_data[index[0],index[1],index[2],:] = gls_results.resid
            new_data[
                index[0], index[1], index[2], :
            ] = gls_results.resid  # + gls_results.params[8]

        img = nib.Nifti1Image(new_data, dataimg.get_affine(), dataimg.get_header())
        nib.save(img, os.path.abspath("fMRI_nuisance.nii.gz"))

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["out_file"] = os.path.abspath("fMRI_nuisance.nii.gz")
        if self.inputs.global_nuisance:
            outputs["averageGlobal_npy"] = os.path.abspath("averageGlobal.npy")
            outputs["averageGlobal_mat"] = os.path.abspath("averageGlobal.mat")
        if self.inputs.csf_nuisance:
            outputs["averageCSF_npy"] = os.path.abspath("averageCSF.npy")
            outputs["averageCSF_mat"] = os.path.abspath("averageCSF.mat")
        if self.inputs.wm_nuisance:
            outputs["averageWM_npy"] = os.path.abspath("averageWM.npy")
            outputs["averageWM_mat"] = os.path.abspath("averageWM.mat")
        return outputs


class DetrendingInputSpec(BaseInterfaceInputSpec):
    in_file = File(exists=True, mandatory=True, desc="fMRI volume to detrend")

    gm_file = InputMultiPath(
        File(exists=True), desc="ROI files registered to fMRI space"
    )

    mode = Enum(["linear", "quadratic", "cubic"], desc="Detrending order")


class DetrendingOutputSpec(TraitedSpec):
    out_file = File(exists=True, desc="Detrended fMRI volume")


class Detrending(BaseInterface):
    """Apply linear, quadratic or cubic detrending on the Functional MRI signal.

    Examples
    --------
    >>> from cmtklib.functionalMRI import Detrending
    >>> detrend = Detrending()
    >>> detrend.inputs.base_dir = '/my_directory'
    >>> detrend.inputs.in_file = '/path/to/sub-01_task-rest_desc-preproc_bold.nii.gz'
    >>> detrend.inputs.gm_file = ['/path/to/sub-01_space-meanBOLD_atlas-L2018_desc-scale1_dseg.nii.gz',
    >>>                            '/path/to/sub-01_space-meanBOLD_atlas-L2018_desc-scale2_dseg.nii.gz',
    >>>                            '/path/to/sub-01_space-meanBOLD_atlas-L2018_desc-scale3_dseg.nii.gz',
    >>>                            '/path/to/sub-01_space-meanBOLD_atlas-L2018_desc-scale4_dseg.nii.gz',
    >>>                            '/path/to/sub-01_space-meanBOLD_atlas-L2018_desc-scale5_dseg.nii.gz']
    >>> detrend.inputs.mode = 'quadratic'
    >>> detrend.run()  # doctest: +SKIP

    """

    input_spec = DetrendingInputSpec
    output_spec = DetrendingOutputSpec

    def _run_interface(self, runtime):
        print("Linear detrending")
        print("=================")

        # Output from previous preprocessing step
        ref_path = self.inputs.in_file

        # Load data
        dataimg = nib.load(ref_path)
        data = dataimg.get_data()
        tp = data.shape[3]

        # GLM: regress out nuisance covariates
        new_data_det = data.copy()
        gm = nib.load(self.inputs.gm_file[0]).get_data().astype(np.uint32)

        from scipy import signal

        for index, value in np.ndenumerate(gm):
            if value == 0:
                continue

            Ydet = signal.detrend(
                data[index[0], index[1], index[2], :].reshape(tp, 1), axis=0
            )
            new_data_det[index[0], index[1], index[2], :] = Ydet[:, 0]

        img = nib.Nifti1Image(new_data_det, dataimg.get_affine(), dataimg.get_header())
        nib.save(img, os.path.abspath("fMRI_detrending.nii.gz"))

        if self.inputs.mode == "quadratic":
            print("Quadratic detrending")
            print("=================")
            from obspy.signal.detrend import polynomial

            # GLM: regress out nuisance covariates
            new_data_det2 = new_data_det.copy()
            for index, value in np.ndenumerate(gm):
                if value == 0:
                    continue
                Ydet = polynomial(
                    new_data_det2[index[0], index[1], index[2], :], order=2
                )

            img = nib.Nifti1Image(
                new_data_det2, dataimg.get_affine(), dataimg.get_header()
            )
            nib.save(img, os.path.abspath("fMRI_detrending.nii.gz"))

        if self.inputs.mode == "cubic":
            print("Cubic-spline detrending")
            print("=================")
            from obspy.signal.detrend import spline

            # GLM: regress out nuisance covariates
            new_data_det2 = new_data_det.copy()
            for index, value in np.ndenumerate(gm):
                if value == 0:
                    continue
                Ydet = spline(new_data_det2[index[0], index[1], index[2], :], order=3)

            img = nib.Nifti1Image(
                new_data_det2, dataimg.get_affine(), dataimg.get_header()
            )
            nib.save(img, os.path.abspath("fMRI_detrending.nii.gz"))

        print("[ DONE ]")
        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["out_file"] = os.path.abspath("fMRI_detrending.nii.gz")
        return outputs


class ScrubbingInputSpec(BaseInterfaceInputSpec):
    in_file = File(exists=True, mandatory=True, desc="fMRI volume to scrubb")

    wm_mask = File(exists=True, desc="WM mask registered to fMRI space")

    gm_file = InputMultiPath(
        File(exists=True), desc="ROI volumes registered to fMRI space"
    )

    motion_parameters = File(
        exists=True, desc="Motion parameters from preprocessing stage"
    )


class ScrubbingOutputSpec(TraitedSpec):
    fd_mat = File(exists=True, desc="FD matrix for scrubbing")

    dvars_mat = File(exists=True, desc="DVARS matrix for scrubbing")

    fd_npy = File(exists=True, desc="FD in .npy format")

    dvars_npy = File(exists=True, desc="DVARS in .npy format")


class Scrubbing(BaseInterface):
    """Computes scrubbing parameters: `FD` and `DVARS`.

    Examples
    --------
    >>> from cmtklib.functionalMRI import Scrubbing
    >>> scrub = Scrubbing()
    >>> scrub.inputs.base_dir = '/my_directory'
    >>> scrub.inputs.in_file = '/path/to/sub-01_task-rest_desc-preproc_bold.nii.gz'
    >>> scrub.inputs.gm_file = ['/path/to/sub-01_space-meanBOLD_atlas-L2018_desc-scale1_dseg.nii.gz',
    >>>                         '/path/to/sub-01_space-meanBOLD_atlas-L2018_desc-scale2_dseg.nii.gz',
    >>>                         '/path/to/sub-01_space-meanBOLD_atlas-L2018_desc-scale3_dseg.nii.gz',
    >>>                         '/path/to/sub-01_space-meanBOLD_atlas-L2018_desc-scale4_dseg.nii.gz',
    >>>                         '/path/to/sub-01_space-meanBOLD_atlas-L2018_desc-scale5_dseg.nii.gz']
    >>> scrub.inputs.wm_mask = '/path/to/sub-01_space-meanBOLD_label-WM_dseg.nii.gz'
    >>> scrub.inputs.gm_file = '/path/to/sub-01_space-meanBOLD_label-GM_dseg.nii.gz'
    >>> scrub.inputs.mode = 'quadratic'
    >>> scrub.run()  # doctest: +SKIP

    """

    input_spec = ScrubbingInputSpec
    output_spec = ScrubbingOutputSpec

    def _run_interface(self, runtime):
        print("Precompute FD and DVARS for scrubbing")
        print("=====================================")
        import scipy.io as sio

        # Output from previous preprocessing step
        ref_path = self.inputs.in_file

        dataimg = nib.load(ref_path)
        data = dataimg.get_data()
        tp = data.shape[3]
        WMfile = self.inputs.wm_mask
        WM = nib.load(WMfile).get_data().astype(np.uint32)
        GM = nib.load(self.inputs.gm_file[0]).get_data().astype(np.uint32)
        mask = WM + GM
        move = np.genfromtxt(self.inputs.motion_parameters)

        # initialize motion measures
        FD = np.zeros((tp - 1, 1))
        DVARS = np.zeros((tp - 1, 1))

        # loop throughout all the time points
        FD[0] = 0
        DVARS[0] = 0
        for i in range(1, tp - 1):
            # FD
            move0 = move[i - 1, :]
            move1 = move[i, :]
            this_move = move1 - move0
            this_move = np.absolute(this_move)
            FD[i] = this_move.sum()

            # DVARS
            # extract current and following time points
            temp0 = data[:, :, :, i - 1]
            temp1 = data[:, :, :, i]
            temp = temp1 - temp0
            temp = np.power(temp, 2)
            temp = temp[mask > 0]
            DVARS[i] = np.power(temp.mean(), 0.5)

        np.save(os.path.abspath("FD.npy"), FD)
        np.save(os.path.abspath("DVARS.npy"), DVARS)
        sio.savemat(os.path.abspath("FD.mat"), {"FD": FD})
        sio.savemat(os.path.abspath("DVARS.mat"), {"DVARS": DVARS})

        print("[ DONE ]")
        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["fd_mat"] = os.path.abspath("FD.mat")
        outputs["dvars_mat"] = os.path.abspath("DVARS.mat")
        outputs["fd_npy"] = os.path.abspath("FD.npy")
        outputs["dvars_npy"] = os.path.abspath("DVARS.npy")
        return outputs
