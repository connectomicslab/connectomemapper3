/**
 * Compute the GFA map from DTK (http://www.trackvis.org/dtk/?subsect=format) diffusion data.
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


unsigned int moment;	// keep the moment (2,3,4...) to calculate


int main(int argc, char** argv)
{
	string	DSI_basename;


/*--------------------------*/
/*  Check INPUT parameters  */
/*--------------------------*/

	/* PARSING of INPUT parameters (achieved with BOOST libraries) */
	po::variables_map vm;
    try {
    	po::arg = "ARG";
		po::options_description desc("Parameters syntax");
        desc.add_options()
            ("dsi", 	po::value<string>(&DSI_basename), "DSI path/basename (e.g. \"data/dsi_\")")
            ("m", 		po::value<unsigned int>(&moment)->default_value(2), "Moment to calculate [2,3,4]")
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
	if ( !vm.count("dsi") )
	{
		cerr<<"'dsi' parameter not set.\n";
		return 1;
	}

	string GFA_filename;
	switch (moment)
	{
		case 2:	GFA_filename = DSI_basename + "gfa.nii"; break;
		case 3:	GFA_filename = DSI_basename + "skewness.nii"; break;
		case 4:	GFA_filename = DSI_basename + "kurtosis.nii"; break;
		default:
			cerr<<"'m' parameter is not in the {2,3,4} valid range.\n";
			return 1;
	}


/*---------------------*/
/*  CALCULATE GFA map  */
/*---------------------*/

	/* READING 'ODF' dataset */
	cout <<"\n-> Reading 'ODF' dataset...\n";

	string ODF_filename = DSI_basename + "odf.nii";
	NIFTI<FLOAT32> niiODF( ODF_filename, true );
	if ( !niiODF.isValid() ) {
		if ( niiODF.getErrorCode() == NIFTI_ERROR_WRONGDATATYPE )
			cerr<<"Datatype should be FLOAT32!\n";
		else
			cerr<<"Unable to open file!\n";
		return 1;
	}
	// check the dimension of ODF dataset
	if ( niiODF.hdr->dim[0]!=4 || niiODF.hdr->dim[1]!=181 ){
		cerr<<"The dimension MUST be (181,*,*,*)!\n";
		return 1;
	}

	cout <<"   [ OK ]\n\n";



	/* CALCULATE GFA map  */
	string B0_filename = DSI_basename + "b0.nii";
	NIFTI<INT16> niiB0( B0_filename, false );
	int     dim[4]         = {niiODF.hdr->dim[2],    niiODF.hdr->dim[3],    niiODF.hdr->dim[4], 	1};
	float   pixdim[4]      = {niiB0.hdr->pixdim[1],  niiB0.hdr->pixdim[2],  niiB0.hdr->pixdim[3], 	1}; 
	short   nDIR		   = niiODF.hdr->dim[1];
	printf("-> Creating 'scalars' files...\n");
	printf("      dim   : %d x %d x %d x %d\n", dim[0],dim[1],dim[2],dim[3]);
	printf("      pixdim: %.4f x %.4f x %.4f x %.4f\n", pixdim[0],pixdim[1],pixdim[2],pixdim[3]);

	NIFTI<FLOAT32> niiGFA;
	niiGFA.make( 3, dim, pixdim );
	(*niiGFA.img) = (*niiGFA.img) * 0;

	// update the metadata
	niiGFA.copyHeader( niiODF.hdr );
	niiGFA.hdr->dim[0] 		= 3;
	niiGFA.hdr->dim[1] 		= dim[0]; 		niiGFA.hdr->dim[2] = dim[1]; 		niiGFA.hdr->dim[3] = dim[2]; 		niiGFA.hdr->dim[4] = dim[3];
	niiGFA.hdr->pixdim[1]	= pixdim[0];	niiGFA.hdr->pixdim[2] = pixdim[1];	niiGFA.hdr->pixdim[3] = pixdim[2];	niiGFA.hdr->pixdim[4] = pixdim[3];
	niiGFA.hdr->datatype	= DT_FLOAT32;	niiGFA.hdr->nbyper 		= 4;
	niiGFA.hdr->cal_min		= 0;			niiGFA.hdr->cal_max		= 1;
	niiGFA.hdr->xyz_units  = 10;
	nifti_update_dims_from_array(niiGFA.hdr);

	Array<float,1> ODF(nDIR);
	float STD, RMS, MEAN, SUM, SQRT, sign;
	MEAN = 1.0 / nDIR;
	SQRT = 1.0 / moment;

	cout <<"-> Calculating GFA in each voxel...\n";
	for(int x=0; x<dim[0] ;x++)
	for(int y=0; y<dim[1] ;y++)
	for(int z=0; z<dim[2] ;z++)
	{
		SUM = 0;
		for(int i=0; i<nDIR ;i++)
			SUM += (*niiODF.img)(i, x,y,z);
 		if (SUM<=0) continue;

		for(int i=0; i<nDIR ;i++)
			ODF(i) = (*niiODF.img)(i, x,y,z) / SUM;

 		STD = sum(pow(ODF-MEAN,(float)moment)) / (nDIR-1);
 		RMS = sum(pow(ODF,(float)moment)) / nDIR;

 		if (moment==3 && STD<0) sign = -1; else sign=1;

 		if (RMS>0)
 			(*niiGFA.img)(x,y,z) = sign * pow( abs(STD / RMS), SQRT);
 		else
 			(*niiGFA.img)(x,y,z) = -1;
	}


	/* SAVE it as .nii  */
	niiGFA.save( GFA_filename );
	cout <<"   [ '"<< GFA_filename <<"' written ]\n\n";

	return 0;
}
