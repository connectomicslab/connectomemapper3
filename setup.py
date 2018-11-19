#!/usr/bin/env python

"""Connectome Mapper 3 BIDS App Manager
"""
import os
import sys
from glob import glob
if os.path.exists('MANIFEST'): os.remove('MANIFEST')

packages=["cmtklib",
          "cmp",
          "cmp.bidsappmanager","cmp.bidsappmanager.stages",
          "cmp.bidsappmanager.stages.preprocessing",
          "cmp.bidsappmanager.stages.segmentation",
          "cmp.bidsappmanager.stages.parcellation",
          "cmp.bidsappmanager.stages.registration",
          "cmp.bidsappmanager.stages.diffusion",
          "cmp.bidsappmanager.stages.functional",
          "cmp.bidsappmanager.stages.connectome",
          "cmp.bidsappmanager.pipelines",
          "cmp.bidsappmanager.pipelines.anatomical",
          "cmp.bidsappmanager.pipelines.diffusion",
          "cmp.bidsappmanager.pipelines.functional",
          "resources"]

package_data = {'cmp.bidsappmanager':
                ['images/*.png',
                'pipelines/anatomical/*.png',
                'pipelines/diffusion/*.png',
                'pipelines/functional/*.png'],
                'resources':
                ['buttons/*.png',
                 'icons/*png'],
                'cmtklib':
                ['data/parcellation/lausanne2008/*/*.*',
		        'data/segmentation/ants_template_IXI/*/*.*',
		        'data/segmentation/ants_template_IXI/*.*',
                'data/parcellation/nativefreesurfer/*/*.*',
                'data/diffusion/gradient_tables/*.*',
                'data/segmentation/thalamus2018/*.*']
                }

################################################################################
# For some commands, use setuptools

if len(set(('develop', 'bdist_egg', 'bdist_rpm', 'bdist', 'bdist_dumb',
            'bdist_wininst', 'install_egg_info', 'egg_info', 'easy_install',
            )).intersection(sys.argv)) > 0:
    from setup_egg import extra_setuptools_args

# extra_setuptools_args can be defined from the line above, but it can
# also be defined here because setup.py has been exec'ed from
# setup_egg.py.
if not 'extra_setuptools_args' in globals():
    extra_setuptools_args = dict()

def main(**extra_args):
    from distutils.core import setup
    from cmp.info import __version__
    setup(name='cmpbidsappmanager',
          version=__version__,
          description='Connectome Mapper 3 BIDS App Manager',
          long_description="""Connectome Mapper 3 BIDS App Manager allows you to interact with the BIDS App of the Connectome Mapper 3, which implements a full diffusion MRI processing pipeline, from raw Diffusion/T1/T2 """ + \
          """data to multi-resolution connection matrices. It also offers support for resting state fMRI data processing and multi-resolution functional connection matrices creation. """ + \
          """The Connectome Mapper 3 BIDS App Manager is part of the Connectome Mapping Toolkit.""",
          author= 'CHUV-EPFL',
          author_email='info@connectomics.org',
          url='http://www.connectomics.org/',
          scripts = glob('scripts/*'),
          license='Modified BSD License',
          packages = packages,
        classifiers = [c.strip() for c in """\
            Development Status :: 1 - Beta
            Intended Audience :: Developers
            Intended Audience :: Science/Research
            Operating System :: OS Independent
            Programming Language :: Python
            Topic :: Scientific/Engineering
            Topic :: Software Development
            """.splitlines() if len(c.split()) > 0],
          maintainer = 'CIBM-CHUV Diffusion Group',
          maintainer_email = 'info@connectomics.org',
          package_data = package_data,
          requires=["numpy (>=1.2)", "nibabel (>=1.1.0)"],
          **extra_args
         )

if __name__ == "__main__":
    main(**extra_setuptools_args)
