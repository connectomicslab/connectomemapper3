/**
 * Compute the P0 map from DTK (http://www.trackvis.org/dtk/?subsect=format) diffusion data.
 *
 * @author  alessandro.daducci@epfl.ch
 * @date, 08/03/2011
 */
#include <iostream>
#include <fstream>
#include <string>

#include "NIFTI.h"
#include <boost/program_options.hpp>

namespace po = boost::program_options;
using namespace std;
using namespace blitz;


int main(int argc, char** argv)
{
	string	DSI_basename, DWI_filename;


/*--------------------------*/
/*  Check INPUT parameters  */
/*--------------------------*/

	/* PARSING of INPUT parameters (achieved with BOOST libraries) */
	po::variables_map vm;
    try {
    	po::arg = "ARG";
		po::options_description desc("Parameters syntax");
        desc.add_options()
			("dwi", 	po::value<string>(&DWI_filename), "DWI path/filename (e.g. \"rawdata/DSI.nii\")")
            ("dsi", 	po::value<string>(&DSI_basename), "DSI path/basename (e.g. \"data/dsi_\")")
            ("help", "Print this help message")
        ;
        po::store(po::command_line_parser(argc, argv).options(desc).run(), vm);
        po::notify(vm);

        if ( argc<2 || vm.count("help") )
        {
			cout <<"\n"<< desc <<"\n\n";
			return 1;
		}
    }
    catch(exception& e) {
        cerr<< e.what() <<"\n";
        return 1;
    }
    catch(...) {
        cerr<<"Exception of unknown type!\n";
    }


	/* Check values */
	if ( !vm.count("dsi") ) {
		cerr<<"'dsi' parameter not set.\n";
		return 1;
	}
if ( !vm.count("dwi") ) {
		cerr<<"'dwi' parameter not set.\n";
		return 1;
	}


/*--------------------*/
/*  CALCULATE P0 map  */
/*--------------------*/
	string P0_filename = DSI_basename + "P0.nii";

	/* READING 'DWI' dataset */
	cout <<"\n-> Reading 'DWI' dataset...\n";

	NIFTI<INT16> niiDWI( DWI_filename, true );
	if ( !niiDWI.isValid() ) {
		if ( niiDWI.getErrorCode() == NIFTI_ERROR_WRONGDATATYPE )
			cerr<<"Datatype should be INT16!\n";
		else
			cerr<<"Unable to open file!\n";
		return 1;
	}

	// check the dimension of ODF dataset
	if ( niiDWI.hdr->dim[0]!=4 || niiDWI.hdr->dim[4]!=515 ){
		cerr<<"The dimension MUST be (*,*,*,515)!\n";
		return 1;
	}

	cout <<"   [ OK ]\n\n";


	/* CALCULATE P0 map  */
	int dim[4] 		= {niiDWI.hdr->dim[1],niiDWI.hdr->dim[2],niiDWI.hdr->dim[3], 1};
	float pixdim[4] = {niiDWI.hdr->pixdim[1],niiDWI.hdr->pixdim[2],niiDWI.hdr->pixdim[3], 1};

	NIFTI<FLOAT32> niiP0;
	niiP0.make( 3, dim, pixdim );
	(*niiP0.img) = (*niiP0.img) * 0;

	niiP0.copyHeader( niiDWI.hdr );
	niiP0.hdr->dim[0] 	= 3;
	niiP0.hdr->dim[1] 	= dim[0]; 		niiP0.hdr->dim[2] = dim[1]; 		niiP0.hdr->dim[3] = dim[2]; 		niiP0.hdr->dim[4] = dim[3];
	niiP0.hdr->pixdim[1] = pixdim[0];	niiP0.hdr->pixdim[2] = pixdim[1];	niiP0.hdr->pixdim[3] = pixdim[2];	niiP0.hdr->pixdim[4] = pixdim[3];
	niiP0.hdr->datatype 	= DT_FLOAT32;		niiP0.hdr->nbyper 		= 4;
	niiP0.hdr->cal_min		= 0;		niiP0.hdr->cal_max		= niiDWI.hdr->dim[4];
	niiP0.hdr->xyz_units  = 10;
	nifti_update_dims_from_array(niiP0.hdr);

	float b0;

	cout <<"-> Calculating P0 in each voxel...\n";
	for(int x=0; x<dim[0] ;x++)
		for(int y=0; y<dim[1] ;y++)
			for(int z=0; z<dim[2] ;z++)
			{
				float value;
				b0 = (*niiDWI.img)(x,y,z,0);
				if ( b0>0 ) {
					value = 0;
					for(int i=0; i<niiDWI.hdr->dim[4] ;i++)
						value += (*niiDWI.img)(x,y,z,i);
					(*niiP0.img)(x,y,z) = value / b0;
				}
				else
				(*niiP0.img)(x,y,z) = 0;
			}


	/* SAVE it as .nii  */
	niiP0.save( P0_filename );
	cout <<"   [ '"<< P0_filename <<"' written ]\n\n";

	return 0;
}
