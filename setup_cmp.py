#!/usr/bin/env python

"""`Setup.py` for Connectome Mapper processing core and CMTKlib."""

import os
import sys
import setuptools
from setuptools.command.install import install

from cmp.info import __version__


class VerifyVersionCommand(install):
    """Custom command to verify that the git tag matches our version"""
    description = 'verify that the git tag matches our version'

    def run(self):
        tag = os.getenv('CIRCLE_TAG')
        version = f'{__version__}'

        if tag != version:
            info = f'Git tag: {tag} does not match the version of this app: {version}'
            sys.exit(info)


directory = os.path.dirname(os.path.abspath(__file__))

if os.path.exists('MANIFEST'):
    os.remove('MANIFEST')

packages = ["cmp",
            "cmp.cli",
            "cmp.stages",
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
            "cmtklib", "cmtklib.bids",
            "cmtklib.interfaces",
            "resources"]

package_data = {'cmp':
                ['cmp3_icon.png'],
                'resources':
                    ['icons/*png'],
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

# Extract package requirements from Conda environment.yml
include_conda_pip_dependencies = False
install_requires = []
dependency_links = []
if include_conda_pip_dependencies:
    path = os.path.join(directory, 'ubuntu16.04', 'environment.yml')
    with open(path) as read_file:
        state = "PREAMBLE"
        for line in read_file:
            line = line.rstrip().lstrip(" -")
            if line == "dependencies:":
                state = "CONDA_DEPS"
            elif line == "pip:":
                state = "PIP_DEPS"
            elif state == "CONDA_DEPS":
                line = '=='.join(line.split('='))
                line = line.split('==')[0]
                # Python is a valid dependency for Conda but not setuptools, so skip it
                if "python" in line:
                    pass
                else:
                    # Appends to dependencies
                    install_requires.append(line)
            elif state == "PIP_DEPS":
                line = line.split('==')[0]
                # Appends to dependency links
                dependency_links.append(line)
                # Adds package name to dependencies
                install_requires.append(line)
print(f'Install requires: {install_requires}')
print(f'Dependency links: {dependency_links}')


def main():
    """Main function of CMP3 ``setup_cmp.py``"""
    setuptools.setup(
        name='cmp',
        version=__version__,
        description='Connectome Mapper 3: A software pipeline for multi-scale connectome mapping of multimodal data',
        long_description="""Connectome Mapper 3 implements a full diffusion MRI processing pipeline, from raw Diffusion/T1/T2
                         data to multi-resolution connection matrices, empowered by the Nipype workflow library.
                         It also offers support for resting state fMRI data processing and multi-resolution functional
                         connection matrices creation. """,
        author='Sebastien Tourbier',
        author_email='sebastien.tourbier@alumni.epfl.ch',
        url='https://github.com/connectomicslab/connectomemapper3',
        entry_points={
            "console_scripts": [
                'connectomemapper3 = cmp.cli.connectomemapper3:main',
            ]
        },
        license='BSD-3-Clause',
        classifiers=[
            'Development Status :: 4 - Beta',
            'Intended Audience :: Science/Research',
            'Intended Audience :: Developers',
            'License :: OSI Approved',
            'Programming Language :: Python',
            'Topic :: Software Development',
            'Topic :: Scientific/Engineering',
            'Operating System :: Microsoft :: Windows',
            'Operating System :: POSIX',
            'Operating System :: Unix',
            'Operating System :: MacOS',
            'Programming Language :: Python :: 3.7',
        ],
        maintainer='Connectomics Lab, CHUV',
        maintainer_email='info@connectomics.org',
        packages=packages,
        include_package_data=True,
        package_data=package_data,
        # requires=["numpy (>=1.18)", "nipype (>=1.5.0)", "pybids (>=0.10.2)"],
        install_requires=install_requires,
        dependency_links=dependency_links,
        python_requires='>=3.7',
        cmdclass={
                'verify': VerifyVersionCommand,
        }
        )


if __name__ == "__main__":
    main()
