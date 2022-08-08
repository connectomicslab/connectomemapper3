# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""This module defines the `visualize_eeg_pipeline_outputs` script that loads and displays the different MNE outputs of the EEG pipeline.

Examples
--------

Here are a few usage examples:

    1. Show all electrode epochs

        .. code-block:: bash

            $ python cmp/cli/visualize_eeg_pipeline_outputs.py \
                --epo_file /path/to/sub-01/eeg/sub-01_task-faces_epo.fif

    2. Carpet plot of ROI time series when using Cartool for ESI

        .. code-block:: bash

            $ python cmp/cli/visualize_eeg_pipeline_outputs.py \
                --epo_file /path/to/sub-01/eeg/sub-01_task-faces_epo.fif \
                --rtc_file /path/to/sub-01_task-faces_atlas-L2018_res-scale1_timeseries.npy \
                --atlas_annot lausanne2018.scale1 \
                --fs_subject sub-01 \
                --fs_subjects_dir /path/to/derivatives/freesurfer-7.1.1 \
                --roi_tsv_file /path/to/sub-01_atlas-L2018_res-scale1_dseg.tsv

    3. Carpet plot of ROI time series when using MNE for ESI

        .. code-block:: bash

            $ python cmp/cli/visualize_eeg_pipeline_outputs.py \
                --epo_file /path/to/sub-01/eeg/sub-01_task-faces_epo.fif \
                --rtc_file /path/to/sub-01_task-faces_atlas-L2018_res-scale1_timeseries.npy \
                --atlas_annot lausanne2018.scale1 \
                --fs_subject sub-01 \
                --fs_subjects_dir /path/to/derivatives/freesurfer-7.1.1 \
                --roi_tsv_file /path/to/sub-01_atlas-L2018_res-scale1_dseg.tsv

    4. Display BEM surfaces only on T1w

        .. code-block:: bash

            $ python cmp/cli/visualize_eeg_pipeline_outputs.py \
                 --bem_file /path/to/sub-01_task-faces_bem.fif \
                 --fs_subject sub-01 \
                 --fs_subjects_dir /path/to/derivatives/freesurfer-7.1.1

    5. Display BEM surfaces and source position on T1w

    .. code-block:: bash

        $ python cmp/cli/visualize_eeg_pipeline_outputs.py \
             --bem_file /path/to/sub-01_task-faces_bem.fif \
             --fs_subject sub-01 \
             --fs_subjects_dir /path/to/derivatives/freesurfer-7.1.1 \
             --src_file /path/to/sub-01_task-faces_src.fif

    6. Plot the noise covariance

    .. code-block:: bash

        $ python cmp/cli/visualize_eeg_pipeline_outputs.py \
             --epo_file /path/to/sub-01_task-faces_epo.fif \
             --fs_subject sub-01 \
             --fs_subjects_dir /path/to/derivatives/freesurfer-7.1.1 \
             --noisecov_file /path/to/sub-01_task-faces_noisecov.fif
"""

import sys
import argparse

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import mne

from cmp.info import __version__


def create_parser():
    """Create the argument parser of `visualize_eeg_pipeline_outputs` python script.

    Returns
    -------
    p : argparse.ArgumentParser
        Argument parser
    """
    p = argparse.ArgumentParser(description="Script to visualize outputs of the EEG pipeline.")

    p.add_argument(
        "--fs_subject",
        help="Freesurfer subject directory.",
    )

    p.add_argument(
        "--fs_subjects_dir",
        help="Freesurfer subjects directory.",
    )

    p.add_argument(
        "--epo_file",
        help="Epochs file in fif format.",
    )

    p.add_argument(
        "--bem_file",
        help="BEM file in fif format.",
    )

    p.add_argument(
        "--src_file",
        help="Source space file in fif format.",
    )

    p.add_argument(
        "--noisecov_file",
        help="Noise covariance file in fif format.",
    )

    p.add_argument(
        "--rtc_file",
        help="ROI time courses file in fif format.",
    )

    p.add_argument(
        "--atlas_annot",
        help="Parcellation annotation file used to extract ROI labels.",
    )

    p.add_argument(
        "--roi_tsv_file",
        help="Parcellation index/label mapping file used to extract ROI labels.",
    )

    p.add_argument(
        "--trans_file",
        help="ROI time courses file in fif format.",
    )

    p.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"Connectome Mapper version {__version__}",
    )

    return p


def create_roi_labels(mean_rtc, fs_subject, fs_subjects_dir, atlas_annot, roi_tsv_file=None):
    """Create list of labels depending on the employed EEG pipeline (Cartool vs. MNE).

    Parameters
    ----------
    mean_rtc : numpy.Array
        Numpy array containing the ROI time-series

    fs_subject : str
        Freesurfer subject directory

    fs_subjects_dir : str
        Freesurfer subjects directory

    atlas_annot : str
        Basename of parcellation annotation file

    roi_tsv_file : str
        Path to parcellation index/label mapping TSV file

    Returns
    -------
    mean_rtc : numpy.Array
        Numpy array containing the ROI time-series

    roi_labels : list
        List of ROI labels in the order of the rows of `mean_rtc`
    """
    # Get number of ROIs (rows) in the ROI time-series array
    nb_rois = mean_rtc.shape[0]

    # Get parcellation labels from the annotation file
    # used by MNE
    labels_parc = mne.read_labels_from_annot(
        subject=fs_subject,
        parc=atlas_annot,
        subjects_dir=fs_subjects_dir
    )
    roi_labels = [label.name for label in labels_parc]

    print(f'nb_rois: {nb_rois}')
    print(f'roi_labels (length): {len(roi_labels)}')

    # Special handle of labels for Cartool as it includes
    # all cortical and sub-cortical rois
    if len(roi_labels) < nb_rois:
        if roi_tsv_file is not None:
            # Cartool is also using sub-cortical
            df_labels = pd.read_csv(roi_tsv_file, delimiter="\t")
            roi_labels = [lab for lab in list(df_labels["name"]) if "brainstem" not in lab]
            print(f'new roi_labels (length): {len(roi_labels)}')
        else:
            raise ValueError("Number of ROI labels and number of ROIs in the time series are not corresponding."
                             "A parcellation index/label mapping file in TSV must be provided with option flag "
                             "--roi_tsv_file.")
    else:  # Special handle of labels for MNE (cortical-only)
        # Sort labels by hemisphere as they are alternating otherwise
        sorting = list(np.arange(0, nb_rois, 2)) + list(np.arange(1, nb_rois, 2))
        # Update list of ROI names
        labels_list_left = [lab for lab in roi_labels if '-lh' in lab]
        labels_list_right = [lab for lab in roi_labels if '-rh' in lab]
        roi_labels = labels_list_left + labels_list_right
        mean_rtc = mean_rtc[sorting, :]

    return mean_rtc, roi_labels


def plot_roi_time_series(mean_rtc, roi_labels, t_min, t_max, title=None):
    """Display ROI time series as a carpet plot.

    Parameters
    ----------
    mean_rtc : numpy.array
        Numpy array containing ROI time series

    roi_labels : list
        List of ROI labels

    t_min : float
        Relative start time in sec. (x-axis)

    t_max : float
        Relative end time in sec. (x-axis)

    title : str
        Title of the figure
    """
    # Get maximum absolute value for the colormap
    vminmax = np.max(abs(mean_rtc))

    # Set figure size
    plt.rcParams['figure.figsize'] = (10, 6.67)

    # Display ROI time series as a carpet plot
    plt.imshow(
        mean_rtc,
        aspect='auto',
        extent=[1e3 * t_min, 1e3 * t_max, 0, mean_rtc.shape[0]],
        interpolation='None',
        vmin=-vminmax,
        vmax=vminmax,
        cmap='magma'
    )
    # Set label of x- and y- axis
    plt.xlabel('Time (ms)')
    plt.ylabel('ROIs')

    # Add colorbar legend
    cbar = plt.colorbar()
    cbar.set_label('Source activity (a.u.)')

    # Show ROI labels only for parcellation that has less than 100 ROIS
    # i.e. NativeFreesurfer and scale 1 of Lausanne2018
    if mean_rtc.shape[0] < 100:
        locs = np.arange(0, mean_rtc.shape[0]) + 0.5
        _ = plt.yticks(locs, roi_labels, rotation=0, fontsize=6)

    # Set figure title
    plt.title(title)

    # Adjust figure margins
    plt.tight_layout()


def main():
    """Main function that load and display different outputs of the EEG pipeline using MNE visualization features.

    Returns
    -------
    exit_code : {0, 1}
        An exit code given to `sys.exit()` that can be:

            * '0' in case of successful completion

            * '1' in case of an error
    """
    # Parse script arguments
    parser = create_parser()
    args = parser.parse_args()

    if args.epo_file:
        epo = mne.read_epochs(args.epo_file)

        if args.noisecov_file:
            noisecov = mne.read_cov(args.noisecov_file)
            mne.viz.plot_cov(noisecov, epo.info)

        elif args.rtc_file:
            # Load ROI time series
            # shape: (#trials x #rois x time)
            rtc = np.load(args.rtc_file)

            # Compute mean over trials
            # shape: (#rois x time)
            mean_rtc = np.mean(rtc, axis=0)

            mean_rtc, roi_labels = create_roi_labels(
                mean_rtc=mean_rtc,
                fs_subject=args.fs_subject,
                fs_subjects_dir=args.fs_subjects_dir,
                atlas_annot=args.atlas_annot,
                roi_tsv_file=args.roi_tsv_file
            )

            plot_roi_time_series(
                mean_rtc=mean_rtc,
                roi_labels=roi_labels,
                t_min=epo.times.min(),
                t_max=epo.times.max(),
                title=f"ROI time-series for {args.fs_subject}"
            )
        else:
            fig = plt.figure()
            mne.viz.plot_epochs(epo, title=f"Epochs for {args.fs_subject}")
            plt.close(fig)

    elif args.bem_file:
        # bem_solution = mne.read_bem_solution(args.bem_file)
        plot_bem_kwargs = dict(
            subject=args.fs_subject,
            subjects_dir=args.fs_subjects_dir,
            brain_surfaces='white',
            orientation='coronal',
            slices=[50, 100, 150, 200]
        )

        if args.src_file:
            src = mne.read_source_spaces(args.src_file)

            fig = plt.figure()
            fig_bem = mne.viz.plot_bem(
                src=src,
                **plot_bem_kwargs
            )
            fig_bem.canvas.set_window_title(f"BEM surfaces and sources for {args.fs_subject}")
            plt.tight_layout()
            plt.close(fig)

        else:
            fig = plt.figure()
            fig_bem = mne.viz.plot_bem(
                **plot_bem_kwargs
            )
            fig_bem.canvas.set_window_title(f"BEM surfaces for {args.fs_subject}")
            plt.tight_layout()
            plt.close(fig)

    else:
        print('INVALID USAGE. Please enter the command: visualize_eeg_pipeline_outputs -h to get a list of possible options.')
        return 1

    plt.show()
    return 0


if __name__ == "__main__":
    sys.exit(main())
