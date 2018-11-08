#!/usr/bin/env python

"""Connectome Mapper and CMTKlib
"""
import os
import sys
from glob import glob
if os.path.exists('MANIFEST'): os.remove('MANIFEST')

packages=["cmp","cmp.interfaces","cmp.stages",
          "cmp.stages.preprocessing",
          "cmp.stages.segmentation",
          "cmp.stages.parcellation",
          "cmp.stages.registration",
          "cmp.stages.diffusion",
          "cmp.stages.functional",
          "cmp.stages.connectome",
          "cmp.pipelines",
          "cmp.pipelines.anatomical",
          "cmp.pipelines.diffusion",
          "cmp.pipelines.functional",
          "cmtklib",
          "cmp.configurator","cmp.configurator.stages",
          "cmp.configurator.stages.preprocessing",
          "cmp.configurator.stages.segmentation",
          "cmp.configurator.stages.parcellation",
          "cmp.configurator.stages.registration",
          "cmp.configurator.stages.diffusion",
          "cmp.configurator.stages.functional",
          "cmp.configurator.stages.connectome",
          "cmp.configurator.pipelines",
          "cmp.configurator.pipelines.anatomical",
          "cmp.configurator.pipelines.diffusion",
          "cmp.configurator.pipelines.functional",
          "resources"]

package_data = {'cmp':
                ['cmp3_icon.png',
                'configurator/images/*.png',
                'configurator/pipelines/anatomical/*.png',
                'configurator/pipelines/diffusion/*.png',
                'configurator/pipelines/functional/*.png',
                'pipelines/anatomical/*.png',
                'pipelines/diffusion/*.png',
                'pipelines/functional/*.png'],
                'resources':
                ['buttons/*.png',
                 'icons/*png'],
                'cmtklib':
                ['data/parcellation/lausanne2008/*/*.*',
                 'data/parcellation/lausanne2018/*.*',
                 'data/parcellation/lausanne2018/*/*.*',
		        'data/segmentation/ants_template_IXI/*/*.*',
		        'data/segmentation/ants_template_IXI/*.*',
                'data/segmentation/ants_MICCAI2012_multi-atlas_challenge_data/*/*.*',
		        'data/segmentation/ants_MICCAI2012_multi-atlas_challenge_data/*.*',
                'data/parcellation/nativefreesurfer/*/*.*',
                'data/colortable_and_gcs/*.*',
                'data/colortable_and_gcs/my_atlas_gcs/*.*',
                'data/diffusion/odf_directions/*.*',
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
    setup(name='cmp',
          version=__version__,
          description='Connectome Mapper',
          long_description="""Connectome Mapper implements a full diffusion MRI processing pipeline, from raw Diffusion/T1/T2 """ + \
          """data to multi-resolution connection matrices. It also offers support for resting state fMRI data processing and multi-resolution functional connection matrices creation. """ + \
          """The Connectome Mapper is part of the Connectome Mapping Toolkit.""",
          author= 'CHUV-EPFL',
          author_email='info@connectomics.org',
          url='http://www.connectomics.org/',
          scripts = glob('scripts/*'),
          license='Modified BSD License',
          packages = packages,
        classifiers = [c.strip() for c in """\
            Development Status :: 3 - Beta
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
