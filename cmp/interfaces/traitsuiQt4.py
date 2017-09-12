# Copyright (C) 2009-2015, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" Defines the various button editors for the PyQt user interface toolkit.
"""

#-------------------------------------------------------------------------------
#  Imports:
#-------------------------------------------------------------------------------

from pyface.qt import QtCore, QtGui

#from traits.api import Unicode, List, Str, on_trait_change
from traits.api import *
from traitsui.api import *

from traitsui.qt4.button_editor import SimpleEditor

# FIXME: ToolkitEditorFactory is a proxy class defined here just for backward
# compatibility. The class has been moved to the
# traitsui.editors.button_editor file.
from traitsui.editors.button_editor \
    import ToolkitEditorFactory


#from traitsui.qt4.button_editor import SimpleEditor

#from editor import Editor

#-------------------------------------------------------------------------------
#  'QPushButtonCustomEditor' class:
#-------------------------------------------------------------------------------

class QPushButtonCustomEditor ( SimpleEditor ):
    """ Custom style editor for a button, which can contain an image.
    """

    # The mapping of button styles to Qt classes.
    _STYLE_MAP = {
        'checkbox': QtGui.QCheckBox,
        'radio':    QtGui.QRadioButton,
        'toolbar':  QtGui.QToolButton
    }

    #---------------------------------------------------------------------------
    #  Finishes initializing the editor by creating the underlying toolkit
    #  widget:
    #---------------------------------------------------------------------------

    def init ( self, parent ):
        """ Finishes initializing the editor by creating the underlying toolkit
            widget.
        """
        # FIXME: We ignore orientation, width_padding and height_padding.

        factory = self.factory

        btype = self._STYLE_MAP.get(factory.style, QtGui.QPushButton)
        self.control = btype()
        self.control.setText(self.string_value(factory.label))
	
	print "CUSTOM : "
	print factory.image
	
        if factory.image is not None:
            self.control.setIcon(factory.image.create_image())
            self.control.setIconSize( QtCore.QSize(abs(self.item.width),abs(self.item.height)) )
            self.control.setFlat(True)

        QtCore.QObject.connect(self.control, QtCore.SIGNAL('clicked()'),self.update_object )
        self.set_tooltip()