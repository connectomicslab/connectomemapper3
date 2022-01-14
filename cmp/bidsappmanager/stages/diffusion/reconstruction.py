# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""Definition of diffusion reconstruction config UI classes."""

# General imports
import re
import os
import pkg_resources

from traits.api import *
from traitsui.api import *

# Own imports
from cmp.stages.diffusion.reconstruction import DipyReconConfig, MRtrixReconConfig


# Reconstruction configuration
class Dipy_recon_configUI(DipyReconConfig):
    """Class that extends the :class:`DipyReconConfig` with graphical components.

    Attributes
    ----------
    flip_table_axis : list of string
        List of axis to flip in the gradient table. Valid values are
        'x', 'y', 'z'

    traits_view : traits.ui.View
        TraitsUI view that displays the attributes of this class, e.g.
        the parameters for diffusion reconstruction using Dipy

    See also
    ---------
    cmp.stages.diffusion.reconstruction.DipyReconConfig
    """

    flip_table_axis = List(editor=CheckListEditor(values=["x", "y", "z"], cols=3))

    traits_view = View(  # Item('gradient_table',label='Gradient table (x,y,z,b):'),
        Item("flip_table_axis", style="custom", label="Flip bvecs:"),
        # Item('custom_gradient_table',enabled_when='gradient_table_file=="Custom..."'),
        # Item('b_value'),
        # Item('b0_volumes'),
        Group(
            Item("local_model", editor=EnumEditor(name="local_model_editor")),
            Group(
                Item("lmax_order"),
                # Item('normalize_to_B0'),
                Item("single_fib_thr", label="FA threshold"),
                visible_when="local_model",
            ),
            visible_when='imaging_model != "DSI"',
        ),
        Group(
            Item("shore_radial_order", label="Radial order"),
            Item("shore_zeta", label="Scale factor (zeta)"),
            Item("shore_lambda_n", label="Radial regularization constant"),
            Item("shore_lambda_l", label="Angular regularization constant"),
            Item("shore_tau", label="Diffusion time (s)"),
            Item(
                "shore_constrain_e0",
                label="Constrain the optimization such that E(0) = 1.",
            ),
            Item(
                "shore_positive_constraint",
                label="Constrain the propagator to be positive.",
            ),
            label="Parameters of SHORE reconstruction model",
            visible_when='imaging_model == "DSI"',
        ),
        Item("mapmri", visible_when='imaging_model != "DTI"'),
        Group(
            VGroup(
                Item("radial_order"), HGroup(Item("small_delta"), Item("big_delta"))
            ),
            HGroup(Item("laplacian_regularization"), Item("laplacian_weighting")),
            Item("positivity_constraint"),
            label="MAP_MRI settings",
            visible_when="mapmri",
        ),
    )


class MRtrix_recon_configUI(MRtrixReconConfig):
    """Class that extends the :class:`MRtrixReconConfig` with graphical components.

    Attributes
    ----------
    flip_table_axis : list of string
        List of axis to flip in the gradient table. Valid values are
        'x', 'y', 'z'

    traits_view : traits.ui.View
        TraitsUI view that displays the attributes of this class, e.g.
        the parameters for diffusion reconstruction using MRtrix

    See also
    ---------
    cmp.stages.diffusion.reconstruction.MRtrixReconConfig
    """

    flip_table_axis = List(editor=CheckListEditor(values=["x", "y", "z"], cols=3))

    traits_view = View(
        Item("flip_table_axis", style="custom", label="Flip gradient table:"),
        Item("local_model", editor=EnumEditor(name="local_model_editor")),
        Group(
            Item("lmax_order"),
            # Item('normalize_to_B0'),
            Item("single_fib_thr", label="FA threshold"),
            visible_when="local_model",
        ),
    )
