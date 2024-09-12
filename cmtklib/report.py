# Copyright (C) 2009-2021, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""Module that defines Nipype interfaces for visual diagnostic plots."""

from nipype.interfaces.base import BaseInterface, TraitedSpec, File, traits, Directory, CommandLine, BaseInterfaceInputSpec
import numpy as np
import matplotlib.pyplot as plt
import nilearn.plotting as nplt

class overlayAnatDiffQC_InputSpec(BaseInterfaceInputSpec):
    anat_file = File(exists=True)
    dwi_fa_file = File(exists=True)
    out_anat_dwi_plot = File(exists=False)


class overlayAnatDiffQC_OutputSpec(TraitedSpec):
    out_anat_dwi_plot = File(exists=True)


class overlayAnatDiffQC(BaseInterface):
    """Produce an anatomical T1 image with diffusion FA overlay

    .. note::
        Note used.
    """
    input_spec = overlayAnatDiffQC_InputSpec
    output_spec = overlayAnatDiffQC_OutputSpec
    title = "Anatomical T1 image with diffusion FA overlay"

    def _run_interface(self,runtime):
        nplt.plot_anat(self.inputs.anat_file,
                       title=title,
                       display_mode='ortho', dim=0, draw_cross=False, annotate=False)
        display.add_overlay(self.inputs.dwi_fa_file)
        display.savefig(self.inputs.out_anat_dwi_plot)
        display.close()
        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        nplt.plot_anat(self.inputs.anat_file,
                       title=title,
                       display_mode='ortho', dim=0, draw_cross=False, annotate=False)
        display.add_overlay(self.inputs.dwi_fa_file)
        display.savefig(self.inputs.out_anat_dwi_plot)
        display.close()

        outputs["out_anat_dwi_plot"] = self.inputs.out_anat_dwi_plot
        return outputs

class carpetPlot_InputSpec(BaseInterfaceInputSpec):
    timeseries_npy = File(exists=True)
    out_carpet_plot = File(exists=False)


class carpetPlot_OutputSpec(TraitedSpec):
    out_carpet_plot = File(exists=True)


class carpetPlot(BaseInterface):
    """Produce a carpet plot for artifact correction.

    .. note::
        Note used.
    """
    input_spec = carpetPlot_InputSpec
    output_spec = carpetPlot_OutputSpec

    def _carpet_plot(self):
        timeseries = np.load(self.inputs.timeseries_npy)
        figsize = (10, 10)
        figure = plt.figure(figsize=figsize)
        axes = figure.add_subplot(1, 1, 1)
        axes.set_xlabel("ROI")
        axes.set_ylabel("Time sample")
        m = axes.imshow(timeseries, interpolation = "nearest", cmap = "magma")
        plt.colorbar(m, shrink = 0.1)

        plt.savefig(self.inputs.out_carpet_plot)
        plt.close()

    def _run_interface(self,runtime):
        self._carpet_plot()
        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        self._carpet_plot()

        outputs["out_carpet_plot"] = self.inputs.out_carpet_plot
        return outputs