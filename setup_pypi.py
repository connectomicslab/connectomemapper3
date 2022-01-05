#!/usr/bin/env python

"""`Setup_pypi.py` for Connectome Mapper 3 for publication to PyPI that does not contain `cmtklib.data`."""

import os
import sys
import setuptools
from setuptools.command.install import install

from cmp.info import __version__


class VerifyVersionCommand(install):
    """Custom command to verify that the git tag matches our version"""

    description = "verify that the git tag matches our version"

    def run(self):
        """Verify that the git tag (`CIRCLE_TAG`) matches our version."""
        tag = os.getenv('CIRCLE_TAG')
        version = f'{__version__}'
        if tag != version:
            info = f"Git tag: {tag} does not match the version of this app: {version}"
            sys.exit(info)


# Get directory where this file is located
directory = os.path.abspath(os.path.dirname(__file__))

# Remove any MANIFEST of a previous installation
if os.path.exists("MANIFEST"):
    os.remove("MANIFEST")

# Define the packages to be installed
packages = [
    "cmp",
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
    "cmp.bidsappmanager",
    "cmp.bidsappmanager.gui",
    "cmp.bidsappmanager.stages",
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
    "cmtklib",
    "cmtklib.bids",
    "cmtklib.interfaces",
    "resources",
]

# Define the package data to be installed
package_data = {
    "cmp": ["cmp3_icon.png", "config/*.json"],
    "cmp.bidsappmanager": [
        "images/*.png",
        "pipelines/anatomical/*.png",
        "pipelines/diffusion/*.png",
        "pipelines/functional/*.png",
    ],
    "resources": ["buttons/*.png", "icons/*png"],
}

# Extract package requirements from Conda environment.yml
include_conda_pip_dependencies = False
install_requires = []
dependency_links = []
if include_conda_pip_dependencies:
    path = os.path.join(directory, "docker", "environment.yml")
    with open(path) as read_file:
        state = "PREAMBLE"
        for line in read_file:
            line = line.rstrip().lstrip(" -")
            if line == "dependencies:":
                state = "CONDA_DEPS"
            elif line == "pip:":
                state = "PIP_DEPS"
            elif state == "CONDA_DEPS":
                line = "==".join(line.split("="))
                line = line.split("==")[0]
                # Python is a valid dependency for Conda but not setuptools, so skip it
                if "python" in line:
                    pass
                else:
                    # Appends to dependencies
                    install_requires.append(line)
            elif state == "PIP_DEPS":
                line = line.split("==")[0]
                # Appends to dependency links
                dependency_links.append(line)
                # Adds package name to dependencies
                install_requires.append(line)
print(f"Install requires: {install_requires}")
print(f"Dependency links: {dependency_links}")


# Read the contents of your README file
with open(os.path.join(directory, "README.md"), encoding="utf-8") as f:
    long_description = f.read()


def main():
    """Main function of CMP3 ``setup.py``"""
    # Setup configuration
    setuptools.setup(
        name="connectomemapper",
        version=__version__,
        description="Connectome Mapper 3: A Flexible and Open-Source Pipeline Software for Multiscale Multimodal Human Connectome Mapping",
        long_description=long_description,
        long_description_content_type="text/markdown",
        author="Sebastien Tourbier",
        author_email="sebastien.tourbier@alumni.epfl.ch",
        url="https://github.com/connectomicslab/connectomemapper3",
        entry_points={
            "console_scripts": [
                'connectomemapper3 = cmp.cli.connectomemapper3:main',
                'cmpbidsappmanager = cmp.cli.cmpbidsappmanager:main',
                'showmatrix_gpickle = cmp.cli.showmatrix_gpickle:main',
                'connectomemapper3_docker = cmp.cli.connectomemapper3_docker:main',
                'connectomemapper3_singularity = cmp.cli.connectomemapper3_singularity:main'
            ]
        },
        license="BSD-3-Clause",
        classifiers=[
            "Development Status :: 5 - Production/Stable",
            "Intended Audience :: Science/Research",
            "Intended Audience :: Developers",
            "License :: OSI Approved",
            "Programming Language :: Python",
            "Topic :: Software Development",
            "Topic :: Scientific/Engineering",
            "Operating System :: Microsoft :: Windows",
            "Operating System :: POSIX",
            "Operating System :: Unix",
            "Operating System :: MacOS",
            "Programming Language :: Python :: 3.7",
        ],
        maintainer="Connectomics Lab, CHUV",
        maintainer_email="sebastien.tourbier@alumni.epfl.ch",
        packages=packages,
        include_package_data=True,
        package_data=package_data,
        # requires=["numpy (>=1.18)", "nipype (>=1.5.0)", "pybids (>=0.10.2)"],
        install_requires=install_requires,
        dependency_links=dependency_links,
        python_requires=">=3.7",
        cmdclass={
            "verify": VerifyVersionCommand,
        },
    )


if __name__ == "__main__":
    main()
