# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""Module that defines traits-based classes for Connectome Mapper 3 BIDS App Interface TraitsUI View."""

from traits.api import Property
from traitsui.api import TabularAdapter


class MultiSelectAdapter(TabularAdapter):
    """This adapter is used by left and right tables for selection of subject to be processed."""

    # Titles and column names for each column of a table.
    # In this example, each table has only one column.
    columns = [("", "myvalue")]
    width = 100

    # Magically named trait which gives the display text of the column named
    # 'myvalue'. This is done using a Traits Property and its getter:
    myvalue_text = Property

    def _get_myvalue_text(self):
        """The getter for Property 'myvalue_text'.

        It simply takes the value of the corresponding item in the list
        being displayed in this table. A more complicated example could
        format the item before displaying it.
        """
        return f"sub-{self.item}"

