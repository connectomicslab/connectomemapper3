#!/usr/bin/env python

import sys
import json
import argparse
import nibabel as nib
import numpy as np


def main(dwi_files, json_files, bval_files, bvec_files, dwi_out_file, json_out_file, bval_out_file, bvec_out_file):
    print('Combine the following single-shell DWI:')

    print(dwi_files)

    bvec_x = ''
    bvec_y = ''
    bvec_z = ''

    bval_out = ''

    json_out_data = {}

    for i, (dwi_file, json_file, bval_file, bvec_file) in enumerate(
            zip(sorted(dwi_files), sorted(json_files), sorted(bval_files), sorted(bvec_files))):
        print('Loading input {}...'.format(i))
        print('  - {}'.format(dwi_file))
        print('  - {}'.format(json_file))
        print('  - {}'.format(bval_file))
        print('  - {}'.format(bvec_file))

        # FIXME: Should check if same name

        # Load the nifti and get the data
        img = nib.load(dwi_file)
        data = img.get_data()

        print('Shape: {}'.format(data.shape))

        # Get a reference nifti header and initialize the matrix for storing multishell data
        if i == 0:
            out_header = img.header.copy()
            dwi_out_data = data

            # Combine the bvec and remove the \n newline code
            with open(bvec_file, 'r') as f:
                lines = f.readlines()
                bvec_x += lines[0].split('\n')[0]
                bvec_y += lines[1].split('\n')[0]
                bvec_z += lines[2].split('\n')[0]

            # Combine the bval and remove the \n newline code
            with open(bval_file, 'r') as f:
                lines = f.readlines()
                bval_out += lines[0].split('\n')[0]

            # Combine the json metadata (relevant fields)
            with open(json_file) as f:
                data = json.load(f)
                json_out_data = data
                json_out_data['ProtocolName'] = [json_out_data['ProtocolName']]
                json_out_data['SequenceName'] = [json_out_data['SequenceName']]
                json_out_data['SAR'] = [json_out_data['SAR']]
                json_out_data['global']['const']['SAR'] = [
                    json_out_data['global']['const']['SAR']]

        else:
            dwi_out_data = np.concatenate((dwi_out_data, data), axis=3)

            # Combine the bvec and remove the \n newline code
            with open(bvec_file, 'r') as f:
                lines = f.readlines()
                bvec_x += lines[0].split('\n')[0]
                bvec_y += lines[1].split('\n')[0]
                bvec_z += lines[2].split('\n')[0]

            # Combine the bvec and remove the \n newline code
            with open(bval_file, 'r') as f:
                lines = f.readlines()
                bval_out += lines[0].split('\n')[0]

            # Combine the json metadata (relevant fields)
            with open(json_file) as f:
                data = json.load(f)
                json_out_data['SliceTiming'] += data['SliceTiming']
                json_out_data['ProtocolName'].append(data['ProtocolName'])
                json_out_data['SequenceName'].append(data['SequenceName'])
                json_out_data['SAR'].append(data['SAR'])
                json_out_data['dcmmeta_shape'][3] += data['dcmmeta_shape'][3]

                json_out_data['global']['const']['SAR'].append(
                    data['global']['const']['SAR'])

                json_out_data['time']['samples']['AcquisitionNumber'] += data['time']['samples']['AcquisitionNumber']
                json_out_data['time']['samples']['AcquisitionTime'] += data['time']['samples']['AcquisitionTime']
                json_out_data['time']['samples']['ContentTime'] += data['time']['samples']['ContentTime']
                json_out_data['time']['samples']['InstanceCreationTime'] += data['time']['samples'][
                    'InstanceCreationTime']
                json_out_data['time']['samples']['InstanceNumber'] += data['time']['samples']['InstanceNumber']
                json_out_data['time']['samples']['LargestImagePixelValue'] += data['time']['samples'][
                    'LargestImagePixelValue']
                json_out_data['time']['samples']['SequenceName'] += data['time']['samples']['SequenceName']
                json_out_data['time']['samples']['WindowCenter'] += data['time']['samples']['WindowCenter']
                json_out_data['time']['samples']['WindowWidth'] += data['time']['samples']['WindowWidth']

    # Save output bvec file
    print("Saving output bvec file as {} with:".format(bvec_out_file))
    print('  bvec_x : {}'.format(bvec_x))
    print('  bvec_y : {}'.format(bvec_y))
    print('  bvec_z : {}'.format(bvec_z))
    with open(bvec_out_file, 'w+') as f_out:
        f_out.writelines([bvec_x + "\n", bvec_y + "\n", bvec_z + "\n"])

    # Save output bval file
    print("Saving output bval file as {} with:".format(bval_out_file))
    print('  bval : {}'.format(bval_out))
    with open(bval_out_file, 'w+') as f_out:
        f_out.write(bval_out + "\n")

    # Update the dimension in the output header
    out_header['dim'][4] = dwi_out_data.shape[3]

    print("Saving output multishell DWI nifti as {} with:".format(dwi_out_file))
    print('  Shape : {}'.format(dwi_out_data.shape))
    print('  Header: {}'.format(out_header))
    out_img = nib.Nifti1Image(
        dwi_out_data, header=out_header, affine=img.affine)
    out_img.to_filename(dwi_out_file)

    # Save output bvec file
    print("Saving output multishell DWI json as {} with:".format(json_out_file))
    with open(json_out_file, 'w+') as f_out:
        json.dump(json_out_data, f_out, indent=4, sort_keys=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Create multi-shell DWI by combining single shell DWIs')
    parser.add_argument('--dwi', type=str, nargs='+',
                        help='Path to each single shell DWI nifti to be combined')
    parser.add_argument('--json', type=str, nargs='+',
                        help='Path to each single shell DWI json to be combined')
    parser.add_argument('--bval', type=str, nargs='+',
                        help='Path to .bval file of each single shell DWI to be combined')
    parser.add_argument('--bvec', type=str, nargs='+',
                        help='Path to .bvec file of each single shell DWI to be combined')
    parser.add_argument(
        '--dwi_output', help='Output filename of the combined multi-shell DWI nifti')
    parser.add_argument(
        '--json_output', help='Output filename of the combined multi-shell DWI json')
    parser.add_argument(
        '--bval_output', help='Output filename of the combined multi-shell DWI bval')
    parser.add_argument(
        '--bvec_output', help='Output filename of the combined multi-shell DWI bvec')
    args = parser.parse_args()

    if len(args.dwi) != len(args.json):
        print('Error: number of single-shell DWI niftis and jsons are different')
        sys.exit(1)

    if len(args.dwi) != len(args.bval):
        print('Error: number of single-shell DWI niftis and bvals are different')
        sys.exit(1)

    if len(args.dwi) != len(args.bvec):
        print('Error: number of single-shell DWI niftis and bvecs are different')
        sys.exit(1)

    main(args.dwi, args.json, args.bval, args.bvec, args.dwi_output, args.json_output, args.bval_output,
         args.bvec_output)
