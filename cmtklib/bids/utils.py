# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""This module provides CMTK Utility functions to handle BIDS datasets."""

import os
import json
from glob import glob

from traits.api import Bool
from nipype.interfaces.base import (
    BaseInterfaceInputSpec,
    BaseInterface,
    TraitedSpec,
    File,
    InputMultiPath,
    OutputMultiPath
)

from cmtklib.bids.io import (
    __cmp_directory__, __nipype_directory__, __freesurfer_directory__
)


def write_derivative_description(bids_dir, deriv_dir, pipeline_name):
    """Write a dataset_description.json in each type of CMP derivatives.

    Parameters
    ----------
    bids_dir : string
        BIDS root directory

    deriv_dir : string
        Output/derivatives directory

    pipeline_name : string
        Type of derivatives (`['cmp-<version>', 'freesurfer-<version>', 'nipype-<version>']`)
    """
    from cmp.info import __version__, __url__, DOCKER_HUB

    bids_dir = os.path.abspath(bids_dir)
    deriv_dir = os.path.abspath(deriv_dir)

    desc = {}

    if pipeline_name == __cmp_directory__:
        desc = {
            "Name": "CMP3 Outputs",
            "BIDSVersion": "1.4.0",
            "DatasetType": "derivatives",
            "GeneratedBy": [
                {
                    "Name": pipeline_name,
                    "Version": __version__,
                    "Container": {
                        "Type": "docker",
                        "Tag": "{}:{}".format(DOCKER_HUB, __version__)
                    },
                    "CodeURL": __url__
                }
            ]
        }
    elif pipeline_name == __freesurfer_directory__:
        desc = {
            "Name": "Freesurfer Outputs of CMP3 ({})".format(__version__),
            "BIDSVersion": "1.4.0",
            "DatasetType": "derivatives",
            "GeneratedBy": [
                {
                    "Name": "freesurfer",
                    "Version": "6.0.1",
                    "Container": {
                        "Type": "docker",
                        "Tag": "{}:{}".format(DOCKER_HUB, __version__)
                    },
                    "CodeURL": __url__
                }
            ]
        }
    elif pipeline_name == __nipype_directory__:
        from nipype import __version__ as nipype_version

        desc = {
            "Name": "Nipype Outputs of CMP3 ({})".format(__version__),
            "BIDSVersion": "1.4.0",
            "DatasetType": "derivatives",
            "GeneratedBy": [
                {
                    "Name": pipeline_name,
                    "Version": nipype_version,
                    "Container": {
                        "Type": "docker",
                        "Tag": "{}:{}".format(DOCKER_HUB, __version__)
                    },
                    "CodeURL": __url__
                }
            ]
        }

    # Keys that can only be set by environment
    # if 'CMP_DOCKER_TAG' in os.environ:
    #     desc['DockerHubContainerTag'] = os.environ['CMP_DOCKER_TAG']
    # if 'CMP_SINGULARITY_URL' in os.environ:
    #     singularity_url = os.environ['CMP_SINGULARITY_URL']
    #     desc['SingularityContainerURL'] = singularity_url

    #     singularity_md5 = _get_shub_version(singularity_url)
    #     if singularity_md5 and singularity_md5 is not NotImplemented:
    #         desc['SingularityContainerMD5'] = _get_shub_version(
    #             singularity_url)

    # Keys deriving from source dataset
    orig_desc = {}
    fname = os.path.join(bids_dir, "dataset_description.json")
    if os.access(fname, os.R_OK):
        with open(fname, "r") as fobj:
            orig_desc = json.load(fobj)

    if "DatasetDOI" in orig_desc:
        desc["SourceDatasets"]: [
            {
                "DOI": orig_desc["DatasetDOI"],
                "URL": 'https://doi.org/{}'.format(orig_desc["DatasetDOI"]),
                "Version": "TODO: To be updated",
            }
        ]
    else:
        desc["SourceDatasets"]: [
            {
                "DOI": "TODO: To be updated",
                "URL": "TODO: To be updated",
                "Version": "TODO: To be updated",
            }
        ]

    desc[
        "License"
    ] = "TODO: To be updated (See https://creativecommons.org/about/cclicenses/)"

    with open(
        os.path.join(deriv_dir, pipeline_name, "dataset_description.json"), "w"
    ) as fobj:
        json.dump(desc, fobj, indent=4)


def _get_shub_version(singularity_url):
    """Get singularity_md5 from URL.

    .. note::
        Not implemented yet

    Parameters
    ----------
    singularity_url : url
        URL to image on singularity hub

    """
    return NotImplemented


class CreateBIDSStandardParcellationLabelIndexMappingFileInputSpec(
    BaseInterfaceInputSpec
):
    """Specify the inputs of the :obj:`~cmtklib.bids.utils.CreateBIDSStandardParcellationLabelIndexMappingFile`."""

    roi_graphml = File(
        mandatory=True,
        exists=True,
        desc="Path to graphml file that describes graph nodes for a given parcellation",
    )
    roi_colorlut = File(
        mandatory=True,
        exists=True,
        desc="Path to FreesurferColorLUT.txt file that describes the RGB color of the "
        "graph nodes for a given parcellation",
    )
    verbose = Bool(
        False,
        desc="Verbose mode"
    )


class CreateBIDSStandardParcellationLabelIndexMappingFileOutputSpec(
    TraitedSpec
):
    """Specify the output of the :obj:`~cmtklib.bids.utils.CreateBIDSStandardParcellationLabelIndexMappingFile`."""

    roi_bids_tsv = File(
        desc="Output BIDS standard generic label-index mapping file that describes parcellation nodes",
    )


class CreateBIDSStandardParcellationLabelIndexMappingFile(BaseInterface):
    """Creates the BIDS standard generic label-index mapping file that describes parcellation nodes."""

    input_spec = CreateBIDSStandardParcellationLabelIndexMappingFileInputSpec
    output_spec = CreateBIDSStandardParcellationLabelIndexMappingFileOutputSpec

    def _run_interface(self, runtime):
        import numpy as np
        import re
        import csv
        import networkx as nx

        # Extract code mapping from parcellation freesurfer color lookup table
        with open(self.inputs.roi_colorlut, "r") as f:
            lut_content = f.readlines()
        # Process line by line
        pattern = re.compile(
            r"\d{1,5}[ ]+[a-zA-Z-_0-9*.]+[ ]+\d{1,3}[ ]+\d{1,3}[ ]+\d{1,3}[ ]+\d{1,3}"
        )
        rois_rgb = np.empty((0, 4), dtype=np.int64)
        for line in lut_content:
            if pattern.match(line):
                s = line.rstrip().split(" ")
                s = list(filter(None, s))
                rois_rgb = np.append(
                    rois_rgb,
                    np.array([[int(s[0]), int(s[2]), int(s[3]), int(s[4])]]),
                    axis=0,
                )

        if self.inputs.verbose:
            print(f'ROIS RGB Colors: {rois_rgb}')

        # Read the graphml node description file
        nodes_g = nx.readwrite.graphml.read_graphml(self.inputs.roi_graphml)
        nodes = nodes_g.nodes(data=True)
        del nodes_g

        # Create a dictionary conformed to BIDS with index, name, color, and mapping columns
        output_bids_node_description = []
        for node in nodes:
            # Get the node attribute dictionary
            in_node_description = node[1]
            # Fill index and name
            out_node_description = {
                "index": 'n/a',
                "name": 'n/a',
            }
            in_node_description_keys = list(in_node_description.keys())
            if ("dn_correspondence_id" in in_node_description_keys) and ("dn_fsname" in in_node_description_keys):
                out_node_description = {
                    "index": int(in_node_description["dn_correspondence_id"]),
                    "name": in_node_description["dn_fsname"].lower(),
                }
            elif ("dn_multiscaleID" in in_node_description_keys) and ("dn_name" in in_node_description_keys):
                out_node_description = {
                    "index": int(in_node_description["dn_multiscaleID"]),
                    "name": in_node_description["dn_name"].lower(),
                }
            else:
                print('  .. Error: Parcellation keys not found in the graphml.')
            # Convert RGB color to hexadecimal
            r, g, b = (
                rois_rgb[rois_rgb[:, 0].astype(int) == out_node_description["index"]][:, 1],
                rois_rgb[rois_rgb[:, 0].astype(int) == out_node_description["index"]][:, 2],
                rois_rgb[rois_rgb[:, 0].astype(int) == out_node_description["index"]][:, 3],
            )
            if self.inputs.verbose:
                print(f'DEBUG: node = {out_node_description["index"]} '
                      f'(name = {out_node_description["name"]}), '
                      f'roi rgb = {rois_rgb[rois_rgb[:, 0].astype(int) == out_node_description["index"]]}')
            # Make sure we have scalar and not arrays of one element
            r = r[0] if hasattr(r, '__len__') else r
            g = g[0] if hasattr(g, '__len__') else g
            b = b[0] if hasattr(b, '__len__') else b
            if self.inputs.verbose:
                print(f'DEBUG: node = {out_node_description["index"]} '
                      f'(name = {out_node_description["name"]}), '
                      f'r = {r}, g = {g}, b = {b}')
            # Fill hexadecimal color
            out_node_description["color"] = "#%02x%02x%02x" % (
                r.squeeze(),
                g.squeeze(),
                b.squeeze(),
            )
            # Fill mapping
            if "brainstem" in in_node_description["dn_name"]:
                out_node_description["mapping"] = 10
            else:
                if "subcortical" in in_node_description["dn_region"]:
                    out_node_description["mapping"] = 9
                elif "cortical" in in_node_description["dn_region"]:
                    out_node_description["mapping"] = 8
            # Add standardized node description dictionary to the list
            output_bids_node_description.append(out_node_description)

        # Write list of standardized node description dictionaries to output TSV file
        keys = ["index", "name", "color", "mapping"]
        output_tsv_filename = self._gen_output_filename(self.inputs.roi_graphml)
        print(f'\t\t > Save TSV file to {output_tsv_filename}...')
        with open(output_tsv_filename, "w") as output_tsv_file:
            dict_writer = csv.DictWriter(output_tsv_file, keys, delimiter="\t")
            dict_writer.writeheader()
            dict_writer.writerows(output_bids_node_description)

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        output_tsv_filename = self._gen_output_filename(self.inputs.roi_graphml)
        output_tsv_filename = os.path.abspath(output_tsv_filename)
        outputs["roi_bids_tsv"] = output_tsv_filename
        return outputs

    @staticmethod
    def _gen_output_filename(input_file):
        from pathlib import Path

        fpath = Path(input_file)
        return str(fpath.stem) + ".tsv"


class CreateCMPParcellationNodeDescriptionFilesFromBIDSFileInputSpec(
    BaseInterfaceInputSpec
):
    """Specify the inputs of the :obj:`~cmtklib.bids.utils.CreateCMPParcellationNodeDescriptionFilesFromBIDSFile`."""

    roi_bids_tsv = File(
        mandatory=True,
        exists=True,
        desc="Output BIDS standard generic label-index mapping file that "
        "describes parcellation nodes",
    )


class CreateCMPParcellationNodeDescriptionFilesFromBIDSFileOutputSpec(
    TraitedSpec
):
    """Specify the output of the :obj:`~cmtklib.bids.utils.CreateCMPParcellationNodeDescriptionFilesFromBIDSFile`."""

    roi_graphml = File(
        desc="Path to graphml file that describes graph nodes for a given parcellation",
    )
    roi_colorlut = File(
        desc="Path to FreesurferColorLUT.txt file that describes the RGB color of the "
        "graph nodes for a given parcellation",
    )


class CreateCMPParcellationNodeDescriptionFilesFromBIDSFile(BaseInterface):
    """Creates CMP graphml and FreeSurfer colorLUT files that describe parcellation nodes from the BIDS TSV file"""

    input_spec = CreateCMPParcellationNodeDescriptionFilesFromBIDSFileInputSpec
    output_spec = CreateCMPParcellationNodeDescriptionFilesFromBIDSFileOutputSpec

    def _run_interface(self, runtime):
        import csv
        from pathlib import Path
        from time import localtime, strftime

        # Read standard BIDS parcellation node description in TSV format
        with open(self.inputs.roi_bids_tsv, "r") as data:
            bids_dict_nodes = []
            for line in csv.DictReader(data, delimiter="\t"):
                bids_dict_nodes.append(line)

        # Create colorLUT file, write header and parcellation node line
        color_lut_file = self._gen_output_filename(self.inputs.roi_bids_tsv, "colorlut")
        print("Create colorLUT file as %s" % color_lut_file)

        with open(color_lut_file, "w+") as f_color_lut:
            time_now = strftime("%a, %d %b %Y %H:%M:%S", localtime())
            hdr_lines = [
                "#$Id: {}_FreeSurferColorLUT.txt {} \n \n".format(
                    Path(self.inputs.roi_bids_tsv).stem, time_now
                ),
                "{:<4} {:<55} {:>3} {:>3} {:>3} {} \n \n".format(
                    "#No.", "Label Name:", "R", "G", "B", "A"
                ),
            ]
            f_color_lut.writelines(hdr_lines)
            del hdr_lines

            for bids_node in bids_dict_nodes:
                # Convert hexadecimal to RGB color
                h = bids_node["color"].lstrip("#")
                (r, g, b) = tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))
                line = [
                    "{:<4} {:<55} {:>3} {:>3} {:>3} {} \n".format(
                        bids_node["index"], bids_node["name"], r, g, b, 0
                    )
                ]
                f_color_lut.writelines(line)
                del line

        # Create graphml file, write header and parcellation node line
        graphml_file = self._gen_output_filename(self.inputs.roi_bids_tsv, "graphml")
        print("Create graphml_file as %s" % graphml_file)

        with open(graphml_file, "w+") as f_graphml:
            # Write header
            hdr_lines = [
                "{}\n".format('<?xml version="1.0" encoding="utf-8"?>'),
                "{}\n".format(
                    '<graphml xmlns="http://graphml.graphdrawing.org/xmlns" '
                    'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
                    'xsi:schemaLocation="http://graphml.graphdrawing.org/xmlns http://graphml.graphdrawing.org/xmlns/1.0/graphml.xsd">'
                ),
                "{}\n".format(
                    '\t<key attr.name="dn_region" attr.type="string" for="node" id="d0" />'
                ),
                "{}\n".format(
                    '\t<key attr.name="dn_fsname" attr.type="string" for="node" id="d1" />'
                ),
                "{}\n".format(
                    '\t<key attr.name="dn_hemisphere" attr.type="string" for="node" id="d2" />'
                ),
                "{}\n".format(
                    '\t<key attr.name="dn_multiscaleID" attr.type="int" for="node" id="d3" />'
                ),
                "{}\n".format(
                    '\t<key attr.name="dn_name" attr.type="string" for="node" id="d4" />'
                ),
                "{}\n".format('\t<graph edgedefault="undirected" id="">'),
            ]
            f_graphml.writelines(hdr_lines)
            del hdr_lines

            for bids_node in bids_dict_nodes:
                # Write node description lines
                node_lines = [
                    "{}\n".format('\t\t<node id="%i">' % int(bids_node["index"])),
                    "{}\n".format('\t\t\t<data key="d0">%s</data>' % "cortical"),
                    "{}\n".format('\t\t\t<data key="d1">%s</data>' % bids_node["name"]),
                    "{}\n".format('\t\t\t<data key="d2">%s</data>' % None),
                    "{}\n".format(
                        '\t\t\t<data key="d3">%i</data>' % int(bids_node["index"])
                    ),
                    "{}\n".format('\t\t\t<data key="d4">%s</data>' % bids_node["name"]),
                    "{}\n".format("\t\t</node>"),
                ]
                f_graphml.writelines(node_lines)
                del node_lines

            # Write bottom lines
            bottom_lines = ["{}\n".format("\t</graph>"), "{}\n".format("</graphml>")]
            f_graphml.writelines(bottom_lines)
            del bottom_lines

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["roi_colorlut"] = os.path.abspath(
            self._gen_output_filename( self.inputs.roi_bids_tsv, "colorlut")
        )
        outputs["roi_graphml"] = os.path.abspath(
            self._gen_output_filename(self.inputs.roi_bids_tsv, "graphml")
        )
        return outputs

    @staticmethod
    def _gen_output_filename(input_tsv_filename, output_type):
        from pathlib import Path

        tsv_filename_path = Path(input_tsv_filename)
        if output_type == "colorlut":
            outprefix_name = tsv_filename_path.stem
            return "{}_FreeSurferColorLUT.txt".format(outprefix_name.replace('_dseg', ''))
        if output_type == "graphml":
            outprefix_name = tsv_filename_path.stem
            return "{}.graphml".format(outprefix_name)


class CreateMultipleCMPParcellationNodeDescriptionFilesFromBIDSFileInputSpec(BaseInterfaceInputSpec):
    """Specify the inputs of the :obj:`~cmtklib.bids.utils.CreateMultipleCMPParcellationNodeDescriptionFilesFromBIDSFile`."""

    roi_bids_tsvs = InputMultiPath(
        File(mandatory=True,
             exists=True,
             desc="List of paths of output BIDS standard generic label-index mapping file that "
                  "describes parcellation nodes")
    )


class CreateMultipleCMPParcellationNodeDescriptionFilesFromBIDSFileOutputSpec(TraitedSpec):
    """Specify the output of the :obj:`~cmtklib.bids.utils.CreateMultipleCMPParcellationNodeDescriptionFilesFromBIDSFile`."""

    roi_graphmls = OutputMultiPath(
        File(desc="Path to graphml file that describes graph nodes for a given parcellation")
    )
    roi_colorluts = OutputMultiPath(
        File(desc="Paths to FreesurferColorLUT.txt files that describe the RGB color of the "
                  "graph nodes for a given list of parcellations")
    )


class CreateMultipleCMPParcellationNodeDescriptionFilesFromBIDSFile(BaseInterface):
    """Creates CMP graphml and FreeSurfer colorLUT files describing parcellation nodes from a list of BIDS TSV files"""

    input_spec = CreateMultipleCMPParcellationNodeDescriptionFilesFromBIDSFileInputSpec
    output_spec = CreateMultipleCMPParcellationNodeDescriptionFilesFromBIDSFileOutputSpec

    def _run_interface(self, runtime):
        for roi_bids_tsv in self.inputs.roi_bids_tsvs:
            ax = CreateCMPParcellationNodeDescriptionFilesFromBIDSFile(roi_bids_tsv=roi_bids_tsv)
            ax.run()
        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['roi_graphmls'] = glob(os.path.abspath("*.graphml"))
        outputs['roi_colorluts'] = glob(os.path.abspath("*_FreeSurferColorLUT.txt"))
        return outputs


def get_native_space_tsv_sidecar_files(filepathlist):
    """Return path to tsv sidecar file of a list of niftis (`.nii.gz`) without `_space-<label>_` in their filename."""
    out_filepathlist = []
    for filepath in filepathlist:
        if "space-" not in filepath:
            out_filepathlist.append(filepath.replace(".nii.gz", ".tsv"))
    return out_filepathlist


def get_native_space_files(filepathlist):
    """Return a list of files without `_space-<label>_` in the filename."""
    out_filepathlist = []
    for filepath in filepathlist:
        if "space-" not in filepath:
            out_filepathlist.append(filepath)
    return out_filepathlist


def get_native_space_no_desc_files(filepathlist):
    """Return a list of files without `_space-<label>_` and `_desc-<label>_` in the filename."""
    out_filepathlist = []
    for filepath in filepathlist:
        if "space-" not in filepath:
            out_filepathlist.append(filepath)
    return out_filepathlist
