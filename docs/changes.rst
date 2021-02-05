
Changes
========

****************************
Version 3.0.0-RC3
****************************

Date: February 05, 2021

This version corresponds to the third release candidate of Connectome Mapper 3.
In particular, it integrates `Pull Request #62 <https://github.com/connectomicslab/connectomemapper3/pull/62>`_ which includes:

*Updates*

* MRtrix3 has been updated from `3.0_RC3_latest` to `3.0.2`.
* Numpy has been updated from `1.18.5` to `1.19.2`.
* Nipype has been updated to `1.5.0` to `1.5.1`.
* Dipy has been updated from `1.0.0` to `1.3.0`.
* CVXPY has been updated from `1.1.5` to `1.1.7`.

*Documentation*

* Update outdated screenshots for GUI documentation page at `readthedocs <https://connectome-mapper-3.readthedocs.io/en/latest/api_doc.html>`_ reported at `CMTK user-group <https://groups.google.com/g/cmtk-users/c/oSjqfjiTcmg/m/4PHLDpPSCwAJ>`_.
* Correction of multiple typos.

*Bug fixes*

* Update code for Dipy tracking with DTI model following major changes in Dipy 1.0 (Fix reported issue `#54 <https://github.com/connectomicslab/connectomemapper3/issues/54>`_).
* Update to Dipy 1.3.0 has removed the deprecated warnings related to CVXPY when using MAP_MRI (`#63 <https://github.com/connectomicslab/connectomemapper3/issues/63>`_)
* Do not set anymore `OMP_NUM_THREADS` at execution due to allocation errors raised when using numpy function dot in Dipy.

*Software development life cycle*

* Add `Test 08` that runs anatomical and fMRI pipelines with:
  Lausanne2018 parcellation, FSL FLIRT co-registration, all nuisance regression, linear detrending and scrubbing
* Add `Test 09` that runs anatomical and dMRI pipelines with:
  Lausanne2018 parcellation, FSL FLIRT, Dipy SHORE, MRtrix SD_Stream tracking, MRtrix SIFT tractogram filtering
* Remove `deploy_singularity_latest` from the workflow for the sake of space on Sylabs.io.

Please check the `main pull request 62 page <https://github.com/connectomicslab/connectomemapper3/pull/62>`_ for more details.


****************************
Version 3.0.0-RC2-patch1
****************************

Date: February 4, 2021

This version fixes bugs in the second release candidate of Connectome Mapper 3 (v3.0.0-RC2).
In particular, it includes:

*Bug fixes*

* Fix the error to save connectome in GraphML format reported in `#65 <https://github.com/connectomicslab/connectomemapper3/issues/65>`_ and
  (`Pull Request #66 <https://github.com/connectomicslab/connectomemapper3/pull/66>`_).

*Software development life cycle*

* Remove publication of the Singularity image to sylabs.io when the master branch is updated for the sake of space (11GB limit)

*Commits*

* CI: remove publication of latest tag image on sylabs.io for space (2 days ago) - commit c765f79
* Merge pull request #66 from connectomicslab/v3.0.0-RC2-hotfix1 (3 days ago) - commit 0a2603e
* FIX: update g2.node to g2.nodes when saving connectomes as graphml (fix #65) (6 days ago) - commit d629eef
* FIX: enabled/disabled gray-out button "Run BIDS App" with Qt Style sheet [skip ci] (3 weeks ago) - commit 10e78d9
* MAINT: removed commented lines in cmpbidsappmanager/gui.py [skip ci] (3 weeks ago) - commit 4cc11e7
* FIX: check availability of modalities in the BIDS App manager window [skip ci] (3 weeks ago) - commit 80fbee2
* MAINT: update copyright year [skip ci] (3 weeks ago) - commit f7d0ffb
* CI: delete previous container with latest TAG on sylabs.io [skip ci] (4 weeks ago) - commit 15c9b18
* DOC: update tag to latest in runonhpc.rst [skip ci] (4 weeks ago) - commit 3165bcc
* CI: comment lines related to version for singularity push (4 weeks ago) - commit 3952d46


****************************
Version 3.0.0-RC2
****************************

Date: December 24, 2020

This version corresponds to the second release candidate of Connectome Mapper 3. In particular, it integrates `Pull Request #45 <https://github.com/connectomicslab/connectomemapper3/pull/45>`_ which includes:

*New feature*

* Add SIFT2 tractogram filtering (requested in `#48 <https://github.com/connectomicslab/connectomemapper3/issues/48>`_, PR `#52 <https://github.com/connectomicslab/connectomemapper3/pull/52>`_).
* Add a tracker to support us seeking for new funding. User is still free to opt-out and disable it with the new option flag `--notrack`.
* Add options suggested by `Theaud G et al. (2020) <https://doi.org/10.1016/j.neuroimage.2020.116889>`_ to better control factors having impacts on reproducibility. It includes:

    * Set the number of ITK threads used by ANTs for registration (option flag `--ants_number_of_threads`).
    * Set the seed of the random number generator used by ANTs for registration (option flag `--ants_random_seed`).
    * Set the seed of the random number generator used by MRtrix for tractography seeding and track propagation (option flag `--mrtrix_random_seed`).

* Full support of Singularity (see `Software development life cycle <circleci>`_).

*Code refactoring*

* A number of classes describing interfaces to `fsl` and `mrtrix3` have been moved from ``cmtklib/interfaces/util.py`` to ``cmtklib/interfaces/fsl.py`` and ``cmtklib/interfaces/mrtrix3.py``.
* Capitalize the first letter of a number of class names.
* Lowercase a number of variable names in `cmtklib/parcellation.py`.

*Graphical User Interface*

* Improve display of qpushbuttons with images in the GUI (PR `#52 <https://github.com/connectomicslab/connectomemapper3/pull/52>`_).
* Make the window to control BIDS App execution scrollable.
* Allow to specify a custom output directory.
* Tune new options in the window to control BIDS App multi-threading (OpenMP and ANTs) and random number generators (ANTs and MRtrix).

*Documentation*

* Full code documentation with *numpydoc*-style docstrings.
* API documentation page at `readthedocs <https://connectome-mapper-3.readthedocs.io/en/latest/api_doc.html>`_.

*Bug fixes*

* Fix the error reported in `#17 <https://github.com/connectomicslab/connectomemapper3/issues/17>`_ if it is still occuring.
* Review statements for creating contents of BIDS App entrypoint scripts to fix issue with Singularity converted images reported in `#47 <https://github.com/connectomicslab/connectomemapper3/issues/47>`_.
* Install `dc` package inside the BIDS App to fix the issue with FSL BET reported in `#50 <https://github.com/connectomicslab/connectomemapper3/issues/50>`_.
* Install `libopenblas` package inside the BIDS App to fix the issue with FSL EDDY_OPENMP reported in `#49 <https://github.com/connectomicslab/connectomemapper3/issues/49>`_.

.. _circleci:

*Software development life cycle*

* Add a new job `test_docker_fmri` that test the fMRI pipeline.
* Add `build_singularity`, `test_singularity_parcellation`, `deploy_singularity_latest`, and `deploy_singularity_release` jobs to build, test and deploy the Singularity image in CircleCI (PR `#56 <https://github.com/connectomicslab/connectomemapper3/pull/56>`_).

Please check the `main pull request 45 page <https://github.com/connectomicslab/connectomemapper3/pull/45>`_ for more details.


****************************
Version 3.0.0-RC1
****************************

Date: August 03, 2020

This version corresponds to the first release candidate of Connectome Mapper 3. In particular, it integrates Pull Request #40 where the last major changes prior to its official release have been made, which includes in particular:

*Migration to Python 3*

* Fixes automatically with ``2to3`` and manually a number of Python 2 statements invalid in python 3 including the print() function

* Correct automatically PEP8 code style issues with autopep8

* Correct manually a number of code stly issues reported by Codacy (bandits/pylints/flake8)

* Major dependency upgrades including:

	* ``dipy 0.15 -> 1.0`` and related code changes in ``cmtklib/interfaces/dipy`` (Check `here <https://dipy.org/documentation/1.0.0./api_changes/#dipy-1-0-changes>`_ for more details about Dipy 1.0 changes)

	.. warning::
	  Interface for tractography based on Dipy DTI model and EuDX tractography, which has been drastically changed in Dipy 1.0, has not been updated yet, It will be part of the next release candidate.

	* ``nipype 1.1.8 -> 1.5.0``

	* ``pybids 0.9.5 -> 0.10.2``

	* ``pydicom 1.4.2 -> 2.0.0``

	* ``networkX 2.2 -> 2.4``

	* ``statsmodels 0.9.0 -> 0.11.1``

	* ``obspy 1.1.1 -> 1.2.1``

	* ``traits 5.1 -> 6.0.0``

	* ``traitsui 6.0.0 -> 6.1.3``

	* ``numpy 1.15.4 -> 1.18.5``

	* ``matplotlib 1.1.8 -> 1.5.0``

	* ``fsleyes 0.27.3 -> 0.33.0``

	* ``mne 0.17.1 -> 0.20.7``

	* ``sphinx 1.8.5 -> 3.1.1``

	* ``sphinx_rtd_theme 0.4.3 -> 0.5.0``

	* ``recommonmark 0.5.0 -> 0.6.0``

*New feature*

* Option to run Freesurfer recon-all in parallel and to specify the number of threads used by not only Freesurfer but also all softwares relying on OpenMP for multi-threading. This can be achieved by running the BIDS App with the new option flag ``--number_of_threads``.

*Changes in BIDS derivatives*

* Renamed connectivity graph files to better conform to the  `BIDS extension proposal on connectivity data schema <https://docs.google.com/document/d/1ugBdUF6dhElXdj3u9vw0iWjE6f_Bibsro3ah7sRV0GA>`_. They are now saved by default in a TSV file as a list of edges.

*Code refactoring*

* Functions to save and load pipeline configuration files have been moved to ``cmtklib/config.py``

*Bug fixes*

* Major changes in how inspection of stage/pipeline outputs with the graphical user interface (cmpbidsappmanager) which was not working anymore after migration to Python3

* Fixes to compute the structural connectivity matrices following migration to python 3

* Fixes to computes ROI volumetry for Lausanne2008 and NativeFreesurfer parcellation schemes

* Add missing renaming of the ROI volumetry file for the NativeFreesurfer parcellation scheme following BIDS

* Create the mask used for computing peaks from the Dipy CSD model when performing Particle Filtering Tractography (development still on-going)

* Add missing renaming of Dipy tensor-related maps (AD, RD, MD) following BIDS

* Remove all references to use Custom segmentation / parcellation / diffusion FOD image / tractogram, inherited from CMP2 but not anymore functional following the adoption of BIDS standard inside CMP3.

*Software development life cycle*

* Use `Codacy <https://www.codacy.com/>`_ to support code reviews and monitor code quality over time.

* Use `coveragepy <https://coverage.readthedocs.io/en/coverage-5.2/>`_  in CircleCI during regression tests of the BIDS app and create code coverage reports published on our `Codacy project page <https://app.codacy.com/gh/connectomicslab/connectomemapper3/dashboard>`_.

* Add new regression tests in CircleCI to improve code coverage:
	* Test 01: Lausanne2018 (full) parcellation + Dipy SHORE + Mrtrix3 SD_STREAM tractography
	* Test 02: Lausanne2018 (full) parcellation + Dipy SHORE + Mrtrix3 ACT iFOV2 tractography
	* Test 03: Lausanne2018 (full) parcellation + Dipy SHORE + Dipy deterministic tractography
	* Test 04: Lausanne2018 (full) parcellation + Dipy SHORE + Dipy Particle Filtering tractography
	* Test 05: Native Freesurfer (Desikan-Killiany) parcellation
	* Test 06: Lausanne2008 parcellation (as implemented in CMP2)

* Moved pipeline configurations for regression tests in CircleCI from ``config/`` to ``.circle/tests/configuration_files``

* Moved lists of expected regression test outputs  in CircleCI from ``.circle/`` to ``.circle/tests/expected_outputs``


Please check the `pull request 40 page <https://github.com/connectomicslab/connectomemapper3/pull/40>`_ for more details.


****************************
Version 3.0.0-beta-RC2
****************************

Date: June 02, 2020

This version integrates Pull Request #33 which corresponds to the last beta release that still relies on Python 2.7. It includes in particular:


*Upgrade*

* Uses  `fsleyes` instead of `fslview` (now deprecated), which now included in the conda environment of the GUI (`py27cmp-gui`).

*New feature*

* Computes of ROI volumetry stored in `<output_dir>/sub-<label>(/ses<label>)/anat` folder, recognized by their `_stats.tsv` file name suffix.

*Improved replicability*

* Sets the `MATRIX_RNG_SEED` environment variable (used by MRtrix) and seed for the numpy random number generator (`numpy.random.seed()`)

*Bug fixes*

* Fixes the output inspector window of the cmpbidsappmanager (GUI) that fails to find existing outputs, after adoption of /bids_dir and /output_dir in the bidsapp docker image.

* Fixes the way to get the list of networkx edge attributes in `inspect_outputs()` of `ConnectomeStage` for the output inspector window of the cmpbidsappmanager (GUI)

* Added missing package dependencies (`fury` and `vtk`) that fixes dipy_CSD execution error when trying to import module actor from dipy.viz to save the results in a png

* Fixes a number of unresolved references identified by pycharm code inspection tool

*Code refactoring*

* Interfaces for fMRI processing were moved to `cmtklib/functionalMRI.py`.

* Interface for fMRI connectome creation (`rsfmri_conmat`)  moved to  `cmtklib/connectome.py`

Please check the `pull request 33 page <https://github.com/connectomicslab/connectomemapper3/pull/33>`_ for change details.


****************************
Version 3.0.0-beta-RC1
****************************

Date: March 26, 2020

This version integrates Pull Request #28 which includes in summary:

* A major revision of continuous integration testing and deployment with CircleCI which closes `Issue 14 <https://github.com/connectomicslab/connectomemapper3/issues/14>`_ integrates an in-house dataset published and available on Zenodo @ https://doi.org/10.5281/zenodo.3708962.

* Multiple bug fixes and enhancements incl. close `Issue 30 <https://github.com/connectomicslab/connectomemapper3/issues/30>`_ , update mrtrix3 to RC3 version, bids-app run command generated by the GUI, location of the configuration and log files to be more BIDS compliant.

* Change in tagging beta version which otherwise might not be meaningfull in accordance with the release date (especially when the expected date is delayed due to unexpected errors that might take longer to be fixed than expected).

Please check the `pull request 28 page <https://github.com/connectomicslab/connectomemapper3/pull/28>`_ for a full list of changes.


****************************
Version 3.0.0-beta-20200227
****************************

Date: February 27, 2020

This version addresses multiple issues to make successful conversion and run of the CMP3 BIDS App on HPC (Clusters) using Singularity.

* Revised the build of the master and BIDS App images:

	* Install locales and set `$LC_ALL` and `$LANG` to make freesurfer hippocampal subfields and brainstem segmentation (matlab-based) modules working when run in the converted SIngularity image

  	* BIDS input and output directories inside the BIDS App container are no longer the `/tmp` and `/tmp/derivatives` folders but `/bids_dir` and `/output_dir`.
  	  .. warning:: this might affect the use of Datalad container (To be confirmed.)

  	* Fix the branch of mrtrix3 to check out

  	* Updated metadata

* Fix the configuration of CircleCI to not use Docker layer cache feature anymore as this feature is not included anymore in the free plan for open source projects.

* Improved documentation where the latest version should be dynamically generated everywhere it should appear.


****************************
Version 3.0.0-beta-20200206
****************************

Date: February 06, 2020

* Implementation of an in-house Nipype interface to AFNI 3DBandPass which can handle to check output as ..++orig.BRIK or as ..tlrc.BRIK (The later can occur with HCP preprocessed fmri data)


****************************
Version 3.0.0-beta-20200124
****************************

Date: January 24, 2020

* Updated multi-scale parcellation with a new symmetric version:

	1. The right hemisphere labels were projected in the left hemisphere to create a symmetric version of the multiscale cortical parcellation proposed by Cammoun2012_.
	2. For scale 1, the boundaries of the projected regions over the left hemisphere were matched to the boundaries of the original parcellation for the left hemisphere.
	3. This transformation was applied for the rest of the scales.

	.. _Cammoun2012: https://doi.org/10.1016/j.jneumeth.2011.09.031

* Updated documentation with list of changes