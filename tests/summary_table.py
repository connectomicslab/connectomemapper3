from os import path as op
import numpy as np
# from nipype.interfaces.base import traits
from traits.api import *
from traitsui.api import *
from traitsui.qt4.extra.qt_view import QtView

from traitsui.tabular_adapter import TabularAdapter
from pyface.image_resource import ImageResource


class Data(HasTraits):
    subject = Str('')
    session = Str('')
    anat_available = Bool(False)
    dmri_available = Bool(False)
    fmri_available = Bool(False)
    anat_processed = Bool(False)
    dmri_processed = Bool(False)
    fmri_processed = Bool(False)


class SummaryAdapter(TabularAdapter):
    columns = [  # ('i','index'),
        ('Subject', 'subject'),
        ('Session', 'session'),
        ('Anatomical Pipeline', 'anat_processed'),
        ('Diffusion Pipeline', 'dmri_processed'),
        ('fMRI Pipeline', 'fmri_processed')]

    # even_bg_color  = wx.Colour( 201, 223, 241 )
    font = 'Courier 10'
    label_alignment = Str('right')

    anat_processed_image = Property
    dmri_processed_image = Property
    fmri_processed_image = Property

    # big_text       = Str
    # big_width      = Float( 18 )
    # big_image      = Property

    # def _get_index_text(self):
    #     return str(self.row)

    def _get_session_text(self):
        if self.item.session != '':
            return str(self.row)
        else:
            return str("N.A.")

    def _get_label_text(self):
        if self.item.session != '':
            return str("%s_%s" % (self.item.subject, self.item.session))
        else:
            return str("%s" % (self.item.subject))

    def _get_anat_processed_image(self):
        if self.item.anat_available:
            if not self.item.anat_processed:
                return 'red_ball'
            else:
                return 'green_ball'
        else:
            return None

    def _get_dmri_processed_image(self):
        if self.item.dmri_available:
            if not self.item.dmri_processed:
                print("Red")
                return 'red_ball'
            else:
                print("Green")
                return 'green_ball'
        else:
            print("None")
            return None

    def _get_fmri_processed_image(self):
        if self.item.fmri_available:
            if not self.item.fmri_processed:
                return 'red_ball'
            else:
                return 'green_ball'
        else:
            return None


class Summary(HasTraits):
    summary_table = List(Data)
    subject = Instance(Data)

    view = QtView(
        Item('summary_table',
             editor=TableEditor(editable=False,
                                selected='subject',
                                adapter=SummaryAdapter(),
                                # operations = [],
                                # images     = [ op.abspath('green_ball.png'),
                                #             op.abspath('red_ball.png'), ]
                                )
             ),
        resizable=True,
        width=0.75,
        height=0.75
    )


if __name__ == '__main__':
    subjects = ['sub-A006',
                'sub-A007']

    sessions = [['ses-20180730', 'ses-20160520161029', 'ses-20170523161523'],
                ['ses-20180730']]

    summary_table = []

    for sub, sub_sessions in zip(subjects, sessions):
        if len(sub_sessions) > 0:
            for ses in sub_sessions:
                print("Process subject %s - session %s" % (sub, ses))
                data = Data(subject=sub,
                            session=ses,
                            anat_available=True,
                            dmri_available=True,
                            fmri_available=True,
                            anat_processed=True,
                            dmri_processed=True,
                            fmri_processed=False)

                # summary_table.append(("%s_%s"%(sub,ses),True,True,False))
                summary_table.append(data)
        # else:
        #     print("Process subject %s - no session "%(sub))
    print(summary_table)
    # summary_table = [('i','index'),('Subject/Session Id', 'label'), ('Anatomical Pipeline', 'anatomical_processed'), ('Diffusion Pipeline', 'diffusion_processed'), ('fMRI Pipeline', 'fmri_processed')]

    test = Summary(summary_table=summary_table)
    test.configure_traits(view='view')
    # --[Tabular Editor Definition]--------------------------------------------------
