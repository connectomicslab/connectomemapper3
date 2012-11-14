/**
 * Converts DTK data format (http://www.trackvis.org/dtk/?subsect=format) into our internal one (dir file).
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


/******************************/
/*----------  MAIN  ----------*/
/******************************/
int main(int argc, char** argv)
{
	string 	DATA_prefix, DATA_type, DIR_filename, ODFDIRLIST_filename;
	float	ix = 1.0, iy = 1.0, iz = 1.0;
	float	vf_THR;


	/***** PARSING of INPUT parameters (achieved with BOOST libraries) *****/
	po::variables_map vm;
    try {
    	po::arg = "ARG";
		po::options_description desc("Parameters syntax");
        desc.add_options()
            ("type", 	po::value<string>(&DATA_type), "type of diffusion data [dti|dsi]")
        	("prefix", 	po::value<string>(&DATA_prefix), "DATA path/prefix (e.g. \"data/dsi_\")")
            ("dirlist",	po::value<string>(&ODFDIRLIST_filename), "filename of the file containing ODF sampling directions [only for dsi]")
            ("vf", 		po::value<float>(&vf_THR)->default_value(0), "Peak threshold for maxima [0..1]")
            ("ix",		"invert x axis")
            ("iy",		"invert y axis")
            ("iz",		"invert z axis")
            ("help", 	"Print this help message")
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
        cerr << e.what() <<"\n";
        return 1;
    }
    catch(...) {
        cerr<<"Exception of unknown type!\n";
    }


	/* Check INOUT PARAMETERS */
	if ( !vm.count("prefix") ) {
		cerr<<"'prefix' parameter not set.\n";
		return 1;
	}
	if ( !vm.count("type") ) {
		cerr<<"'type' parameter not set.\n";
		return 1;
	}

	if ( DATA_type.compare("dsi")!=0 && vm.count("dirlist") ) {
		cerr<<"'dirlist' parameter is allowed only for 'dsi' scans.\n";
		return 1;
	}
	if ( DATA_type.compare("dsi")==0 && !vm.count("dirlist") ) {
		ODFDIRLIST_filename = "./181_vecs.dat";
	}

	if ( vm.count("ix") ) {
		cout <<"\nNB: 'x' component will be inverted!\n";
		ix = -1;
	}
	if ( vm.count("iy") ) {
		cout <<"\nNB: 'y' component will be inverted!\n";
		iy = -1;
	}
	if ( vm.count("iz") ) {
		cout <<"\nNB: 'z' component will be inverted!\n";
		iz = -1;
	}

	if ( vf_THR<0 || vf_THR>1 )
	{
		cerr<<"'vf' parameter must be in the range [0..1].\n";
		return 1;
	}
	cout <<"\n";


	/*----------------------------*/
	/*          DTI case          */
	/*----------------------------*/
	if ( DATA_type.compare("dti")==0 )
	{
		string 	V1_filename;

		cout <<"-> Converting 'dti' dataset\n   ------------------------\n\n";


		/* READING 'V1' dataset */
		cout <<"-> Reading 'V1' dataset...\n";

		V1_filename = DATA_prefix + "v1.nii";
		NIFTI<FLOAT32> niiV1( V1_filename, true );
		if ( !niiV1.isValid() ) {
			if ( niiV1.getErrorCode() == NIFTI_ERROR_WRONGDATATYPE )
				cerr<<"Datatype should be FLOAT32!\n";
			else
				cerr<<"Unable to open file!\n";
			return 1;
		}

		printf("      dim   : %d x %d x %d x %d\n", niiV1.hdr->dim[1],niiV1.hdr->dim[2],niiV1.hdr->dim[3],niiV1.hdr->dim[4]);
		printf("      pixdim: %.4f x %.4f x %.4f\n", niiV1.hdr->pixdim[1],niiV1.hdr->pixdim[2],niiV1.hdr->pixdim[3]);

		cout <<"   [ OK ]\n\n";


		/*  Perform conversion  */
		cout <<"-> Performing CONVERSION...\n";

		int 	dim[4] 		= {niiV1.hdr->dim[1],    niiV1.hdr->dim[2],    niiV1.hdr->dim[3],    12};
		float 	pixdim[4] 	= {niiV1.hdr->pixdim[1], niiV1.hdr->pixdim[2], niiV1.hdr->pixdim[3], 1};

		NIFTI<FLOAT32> niiDIR;
		niiDIR.make( 4, dim, pixdim );
		(*niiDIR.img) = (*niiDIR.img) * 0;

		// update the metadata
		niiDIR.copyHeader( niiV1.hdr );
		niiDIR.hdr->dim[0] 		= 4;
		niiDIR.hdr->dim[1]    	= dim[0]; 		niiDIR.hdr->dim[2]    = dim[1];		niiDIR.hdr->dim[3]    = dim[2]; 	niiDIR.hdr->dim[4]    = dim[3];
		niiDIR.hdr->pixdim[1] 	= pixdim[0];	niiDIR.hdr->pixdim[2] = pixdim[1];	niiDIR.hdr->pixdim[3] = pixdim[2];	niiDIR.hdr->pixdim[4] = pixdim[3];
		niiDIR.hdr->datatype 	= DT_FLOAT32;
		niiDIR.hdr->nbyper 		= 4;
		niiDIR.hdr->cal_min		= 0;
		niiDIR.hdr->cal_max		= 1;
		niiDIR.hdr->xyz_units	= 10;
		nifti_update_dims_from_array(niiDIR.hdr);

 		float norm = 1;
		for(int z=0; z<dim[2] ;z++)
		for(int y=0; y<dim[1] ;y++)
		for(int x=0; x<dim[0] ;x++)
		{
			// reorient direction according to QFORM
			norm = sqrt( (*niiV1.img)(x,y,z,0)*(*niiV1.img)(x,y,z,0)+(*niiV1.img)(x,y,z,1)*(*niiV1.img)(x,y,z,1)+(*niiV1.img)(x,y,z,2)*(*niiV1.img)(x,y,z,2));
			if (norm<=0) norm=1;

			(*niiDIR.img)(x,y,z, 0) =  1;
			(*niiDIR.img)(x,y,z, 1) =  ix * (*niiV1.img)(x,y,z,0) / norm;
			(*niiDIR.img)(x,y,z, 2) =  iy * (*niiV1.img)(x,y,z,1) / norm;
			(*niiDIR.img)(x,y,z, 3) =  iz * (*niiV1.img)(x,y,z,2) / norm;
			(*niiDIR.img)(x,y,z, 4) =  0;
			(*niiDIR.img)(x,y,z, 5) =  0;
			(*niiDIR.img)(x,y,z, 6) =  0;
			(*niiDIR.img)(x,y,z, 7) =  0;
			(*niiDIR.img)(x,y,z, 8) =  0;
			(*niiDIR.img)(x,y,z, 9) =  0;
			(*niiDIR.img)(x,y,z,10) =  0;
			(*niiDIR.img)(x,y,z,11) =  0;
		}

		DIR_filename = DATA_prefix + "dir.nii";
		niiDIR.save( DIR_filename );
		cout <<"   [ '"<< DIR_filename <<"' written ]\n\n";
	}


	/*----------------------------*/
	/*          DSI case          */
	/*----------------------------*/
	else if ( DATA_type.compare("dsi")==0 )
	{
		string 	ODF_filename, MAX_filename, B0_filename;

		cout <<"-> Converting 'dsi' dataset\n   ------------------------\n\n";


		/* READING the ODF sampling directions file */
		cout <<"-> Reading 'ODF SAMPLING DIRECTIONS' list...\n";

		Array<float,2> dirlist(181,3);

		FILE* fp = fopen(ODFDIRLIST_filename.c_str(),"r");
		if (fp==NULL)
			{ cerr<<"Unable to open file!\n"; return 1; }
		size_t bytesRead = fread((char*)dirlist.data(),1,4*3*181,fp);
		fclose(fp);

		cout <<"   [ 181 directions ]\n\n";


		/* READING 'ODF' dataset */
		cout <<"-> Reading 'ODF' dataset...\n";

		ODF_filename = DATA_prefix + "odf.nii";
		NIFTI<FLOAT32> niiODF( ODF_filename, true );
		if ( !niiODF.isValid() ) {
			if ( niiODF.getErrorCode() == NIFTI_ERROR_WRONGDATATYPE )
				cerr<<"Datatype should be FLOAT32!\n";
			else
				cerr<<"Unable to open file!\n";
			return 1;
		}

		printf("      dim   : %d x %d x %d x %d\n", niiODF.hdr->dim[1],niiODF.hdr->dim[2],niiODF.hdr->dim[3],niiODF.hdr->dim[4]);
		printf("      pixdim: %.4f x %.4f x %.4f x %.4f\n", niiODF.hdr->pixdim[1],niiODF.hdr->pixdim[2],niiODF.hdr->pixdim[3],niiODF.hdr->pixdim[4]);

		cout <<"   [ OK ]\n\n";

		// check the dimension of ODF dataset
		if ( niiODF.hdr->dim[0]!=4 || niiODF.hdr->dim[1]!=181 ){
			cerr<<"The dimension MUST be (181,*,*,*)!\n";
			return 1;
		}

		// calculate QFORM matrix (needed for correct reorientation of gradient directions)
		float d = niiODF.hdr->quatern_d;
		float c = niiODF.hdr->quatern_c;
		float b = niiODF.hdr->quatern_b;
		float a = sqrt(1.0-(b*b+c*c+d*d));
		cout <<"-> Compute QFORM matrix...\n";
		printf("      quatern_b, quatern_c, quatern_d,    : %.4f , %.4f , %.4f\n", b,c,d);

		Array<float,2> QFORM(3,3);
		QFORM = a*a+b*b-c*c-d*d, 2*b*c-2*a*d, 2*b*d+2*a*c,
			2*b*c+2*a*d, a*a+c*c-b*b-d*d, 2*c*d-2*a*b,
			2*b*d-2*a*c, 2*c*d+2*a*b, a*a+d*d-c*c-b*b;

		if ( QFORM(0,0)!=-1 || QFORM(1,0)!=0  || QFORM(2,0)!=0 ||
			 QFORM(0,1)!=0  || QFORM(1,1)!=-1 || QFORM(2,1)!=0 ||
			 QFORM(0,2)!=0  || QFORM(1,2)!=0  || QFORM(2,2)!=1 )
		{
			cerr <<"\nThe 'qform' information is not handled properly by this software! Be careful.\n";
			cerr << "   qform = "<< QFORM << "\n";
		}

		// Reorient sampling directions according to QFORM
		for(int i=0; i<181 ;i++) {
			Array<float,1> tmp( dirlist(i,Range(0,2)) );
			dirlist(i,0) = ix * ( tmp(0)*QFORM(0,0) + tmp(1)*QFORM(1,0) + tmp(2)*QFORM(2,0) );
			dirlist(i,1) = iy * ( tmp(0)*QFORM(0,1) + tmp(1)*QFORM(1,1) + tmp(2)*QFORM(2,1) );
			dirlist(i,2) = iz * ( tmp(0)*QFORM(0,2) + tmp(1)*QFORM(1,2) + tmp(2)*QFORM(2,2) );
			dirlist(i,1) = -dirlist(i,1);		// [NOTE] don't know why
		}


		/* READING 'MAX' dataset */
		cout <<"-> Reading 'MAX' dataset...\n";

		MAX_filename = DATA_prefix + "max.nii";
		NIFTI<INT16> niiMAX( MAX_filename, true );
		if ( !niiMAX.isValid() ) {
			if ( niiMAX.getErrorCode() == NIFTI_ERROR_WRONGDATATYPE )
				cerr<<"Datatype should be INT16!\n";
			else
				cerr<<"Unable to open file!\n";
			return 1;
		}

		printf("      dim   : %d x %d x %d x %d\n", niiMAX.hdr->dim[1],niiMAX.hdr->dim[2],niiMAX.hdr->dim[3],niiMAX.hdr->dim[4]);
		printf("      pixdim: %.4f x %.4f x %.4f x %.4f\n", niiMAX.hdr->pixdim[1],niiMAX.hdr->pixdim[2],niiMAX.hdr->pixdim[3],niiMAX.hdr->pixdim[4]);

		cout <<"   [ OK ]\n\n";

		// check dimension of MAX dataset
		if (
			niiMAX.hdr->dim[0] != niiODF.hdr->dim[0] ||
			niiMAX.hdr->dim[1] != niiODF.hdr->dim[1] ||
			niiMAX.hdr->dim[2] != niiODF.hdr->dim[2] || niiMAX.hdr->pixdim[2] != niiODF.hdr->pixdim[2] ||
			niiMAX.hdr->dim[3] != niiODF.hdr->dim[3] || niiMAX.hdr->pixdim[3] != niiODF.hdr->pixdim[3] ||
			niiMAX.hdr->dim[4] != niiODF.hdr->dim[4] || niiMAX.hdr->pixdim[4] != niiODF.hdr->pixdim[4]
			)
		{
			cerr<<"ODF and MAX have different geometry!\n";
			return 1;
		}



		/*  Perform conversion  */
		cout <<"-> Performing CONVERSION...\n";

		B0_filename = DATA_prefix + "b0.nii";
		NIFTI<INT16> niiB0( B0_filename, false );
		int     dim[4]         = {niiMAX.hdr->dim[2], niiMAX.hdr->dim[3], niiMAX.hdr->dim[4], 12};
		float   pixdim[4]      = {niiB0.hdr->pixdim[1], niiB0.hdr->pixdim[2], niiB0.hdr->pixdim[3], 1}; 
		printf("-> Creating 'DIR' file...\n");
		printf("      dim   : %d x %d x %d x %d\n", dim[0],dim[1],dim[2],dim[3]);
		printf("      pixdim: %.4f x %.4f x %.4f x %.4f\n", pixdim[0],pixdim[1],pixdim[2],pixdim[3]);

		NIFTI<FLOAT32> niiDIR;
		niiDIR.make( 4, dim, pixdim );
		(*niiDIR.img) = (*niiDIR.img) * 0;

		// update the metadata
		niiDIR.copyHeader( niiODF.hdr );
		niiDIR.hdr->dim[0] 		= 4;
		niiDIR.hdr->dim[1] 		= dim[0]; 		niiDIR.hdr->dim[2] = dim[1]; 		niiDIR.hdr->dim[3] = dim[2]; 		niiDIR.hdr->dim[4] = dim[3];
		niiDIR.hdr->pixdim[1] 	= pixdim[0];	niiDIR.hdr->pixdim[2] = pixdim[1];	niiDIR.hdr->pixdim[3] = pixdim[2];	niiDIR.hdr->pixdim[4] = 1;
		niiDIR.hdr->datatype 	= DT_FLOAT32;
		niiDIR.hdr->nbyper 		= 4;
		niiDIR.hdr->cal_min		= 0;
		niiDIR.hdr->cal_max		= 1;
		niiDIR.hdr->xyz_units 	= 10;
		nifti_update_dims_from_array(niiDIR.hdr);

		FLOAT32 vf[3], MIN, MAX, value;
		int   pos[3], x, y, z, i, i1, i2, i3;
		for(z=0; z<dim[2] ;z++)
		for(y=0; y<dim[1] ;y++)
		for(x=0; x<dim[0] ;x++)
		{
			// locate the 3 major maxima
			MIN = MAX = -1;
			for(i=0; i<181 ;i++) {
				value = (*niiODF.img)(i,x,y,z);
				if (value<MIN) MIN = value;
				else if (value>MAX) MAX = value;
			}

			for(i=0; i<3 ;i++)
				vf[i] = pos[i] = 0;

			for(i1=0; i1<181 ;i1++)
				if ( (*niiMAX.img)(i1,x,y,z)==1 )
				{
					value = ((*niiODF.img)(i1,x,y,z) - MIN) / (MAX-MIN);
					if ( value < vf_THR ) continue;

					for(i2=0; i2<3 ;i2++)
						if ( value > vf[i2] )
						{
							for(i3=2; i3>i2 ;i3--)
							{
								vf[i3]  = vf[i3-1];
								pos[i3] = pos[i3-1];
							}
							vf[i2]  = value;
							pos[i2] = i1;
							break;
						}
				}

				// normalize the volume fraction to 1
				value = vf[0]+vf[1]+vf[2];
				if ( value>0 )
				{
					vf[0] = vf[0]/value;
					vf[1] = vf[1]/value;
					vf[2] = vf[2]/value;
				}

				// store the data for this voxel
				for(i2=0; i2<3 ;i2++)
				{
					(*niiDIR.img)(x,y,z,4*i2+0) = vf[i2];
					(*niiDIR.img)(x,y,z,4*i2+1) = dirlist(pos[i2],0);
					(*niiDIR.img)(x,y,z,4*i2+2) = dirlist(pos[i2],1);
					(*niiDIR.img)(x,y,z,4*i2+3) = dirlist(pos[i2],2);
				}
		}

		DIR_filename = DATA_prefix + "dir.nii";
		niiDIR.save( DIR_filename );
		cout <<"   [ '"<< DIR_filename <<"' written ]\n\n";
	}


	else {
		cerr<<"'type' parameter can be only 'dti' or 'dsi'.\n";
		return 1;
	}


	return 0;
}
