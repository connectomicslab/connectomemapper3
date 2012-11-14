/**
 * Performs streamline fiber-tracking.
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

#include "streamline.h"

streamline* TRACKER;


/*-----------------------------------------------------   main()   -----------------------------------------------------*/
int main(int argc, char** argv)
{
	tracking_config 	CONFIG;
	string 				DIR_filename, MASK_filename, SEED_filename, TRK_filename;


	/***** PARSING of INPUT parameters (achieved with BOOST libraries) *****/
	po::variables_map vm;
    try {
    	po::arg = "ARG";
		po::options_description desc("Parameters syntax");
        desc.add_options()
            ("dir", 		po::value<string>(&DIR_filename), "DIR path/filename (e.g. \"data/dsi_DIR.nii\")")
            ("seed",		po::value<string>(&SEED_filename), "SEED MASK path/filename (e.g. \"data/seed_mask.nii\")")
            ("wm", 			po::value<string>(&MASK_filename), "WM MASK path/filename (e.g. \"data/mask.nii\")")
            ("angle", 		po::value<float>(&CONFIG.maxAngle)->default_value(45), "ANGLE threshold [degree]")
            ("out", 		po::value<string>(&TRK_filename), "OUTPUT path/filename (e.g. \"data/fibers.trk\")\n")
            ("seeds", 		po::value<int>(&CONFIG.seeds)->default_value(1), "number of random seed points per voxel")
            ("minLength", 	po::value<int>(&CONFIG.minLength)->default_value(10), "minimum length of a fiber [steps]")
            ("maxLength", 	po::value<int>(&CONFIG.maxLength)->default_value(1000), "maximum length of a fiber [steps]")
            ("stepSize", 	po::value<float>(&CONFIG.stepSize)->default_value(1), "step size [mm]")
            ("vf", 			po::value<float>(&CONFIG.volFracThr)->default_value(0), "keep only maxima above given volume fraction [0..1]")

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
        cerr<< e.what() <<"\n\n";
        return 1;
    }
    catch(...) {
        cerr<<"Exception of unknown type!\n\n";
    }


	/* Check INOUT PARAMETERS */
	if ( !vm.count("dir") )
	{
		cerr<<"'dir' parameter not set.\n\n";
		return 1;
	}
	if ( !vm.count("seed") )
	{
		SEED_filename = "";
	}
	if ( !vm.count("wm") )
	{
		cerr<<"'wm' parameter not set.\n\n";
		return 1;
	}
	if ( !vm.count("out") )
	{
		cerr<<"'out' parameter not set.\n\n";
		return 1;
	}

	if ( CONFIG.volFracThr<0 || CONFIG.volFracThr>1 )
	{
		cerr<<"'vf' parameter must be in the range [0..1].\n\n";
		return 1;
	}
	if ( CONFIG.stepSize<=0 || CONFIG.stepSize>4 )
	{
		cerr<<"'stepSize' parameter must be in the range (0..4].\n\n";
		return 1;
	}
	if ( CONFIG.maxLength<1 || CONFIG.maxLength>1000 )
	{
		cerr<<"'maxLength' parameter must be in the range [1..1000].\n\n";
		return 1;
	}
	if ( CONFIG.maxAngle<1 || CONFIG.maxAngle>90 )
	{
		cerr<<"'maxAngle' parameter must be in the range [1..90].\n\n";
		return 1;
	}
	if ( CONFIG.seeds<1 || CONFIG.seeds>64 )
	{
		cerr<<"'seeds' parameter must be in the range [1..64].\n\n";
		return 1;
	}


	/* PRINT a summary of parameters */
	cout <<"\nFiber-tracking PARAMETERS\n=========================\n";
	cout <<"\tAngle\t\t:\t"<< CONFIG.maxAngle <<"°\n";
	cout <<"\t# seeds/voxel\t:\t"<< CONFIG.seeds <<"\n";
	cout <<"\tDIR filename\t:\t"<< DIR_filename <<"\n";
	cout <<"\tWM\t\t:\t"<< MASK_filename <<"\n";
	cout <<"\tTRK filename\t:\t"<< TRK_filename <<"\n\n";



/*----------------------------*/
/*  Read all needed datasets  */
/*----------------------------*/
	clock_t start_time = time(NULL);

	/* READING 'DIR' dataset */
	cout <<"-> Reading 'DIR' dataset...\n";

	NIFTI<FLOAT32> niiDIR( DIR_filename, true );
	if ( !niiDIR.isValid() )
		{ cerr << "\n[ERROR] Unable to open file '"<< DIR_filename <<"'!\n\n"; exit(1); }
	if ( niiDIR.hdr->datatype != DT_FLOAT32 )
		{ cerr << "\n[ERROR] File '"<< DIR_filename <<"' has a WRONG DATA TYPE! It should be FLOAT32!\n\n"; exit(1); }

	printf("      dim   : %d x %d x %d x %d\n", niiDIR.hdr->dim[1], niiDIR.hdr->dim[2], niiDIR.hdr->dim[3], niiDIR.hdr->dim[4]);
	printf("      pixdim: %.4f x %.4f x %.4f\n", niiDIR.hdr->pixdim[1], niiDIR.hdr->pixdim[2], niiDIR.hdr->pixdim[3]);

	cout <<"   [ OK ]\n\n";


	/* READING 'MASK' image */
	cout <<"-> Reading 'MASK' image...\n";

	NIFTI<UINT8> niiMASK( MASK_filename, true );
	if ( !niiMASK.isValid() )
		{ cerr << "\n[ERROR] Unable to open file '"<< MASK_filename <<"'!\n\n"; exit(1); }
	if ( niiMASK.hdr->datatype != DT_UINT8 )
		{ cerr << "\n[ERROR] File '"<< MASK_filename <<"' has a WRONG DATA TYPE! It should be UINT8!\n\n"; exit(1); }

	printf("      dim   : %d x %d x %d\n", niiMASK.hdr->dim[1], niiMASK.hdr->dim[2], niiMASK.hdr->dim[3]);
	printf("      pixdim: %.4f x %.4f x %.4f\n", niiMASK.hdr->pixdim[1], niiMASK.hdr->pixdim[2], niiMASK.hdr->pixdim[3]);

	cout <<"   [ OK ]\n\n";


	/* READING 'SEED' image */
 	NIFTI<UINT8> niiSEED;

	if ( !SEED_filename.empty() )
	{
		cout <<"-> Reading 'SEED' image...\n";

		niiSEED.open( SEED_filename, true );
		if ( !niiSEED.isValid() )
			{ cerr << "\n[ERROR] Unable to open file '"<< SEED_filename <<"'!\n\n"; exit(1); }
		if ( niiSEED.hdr->datatype != DT_UINT8 )
			{ cerr << "\n[ERROR] File '"<< SEED_filename <<"' has a WRONG DATA TYPE! It should be UINT8!\n\n"; exit(1); }

		printf("      dim   : %d x %d x %d\n", niiSEED.hdr->dim[1], niiSEED.hdr->dim[2], niiSEED.hdr->dim[3]);
		printf("      pixdim: %.4f x %.4f x %.4f\n", niiSEED.hdr->pixdim[1], niiSEED.hdr->pixdim[2], niiSEED.hdr->pixdim[3]);

		cout <<"   [ OK ]\n\n";
	}



/*------------------------*/
/*  Perform TRACTOGRAPHY  */
/*------------------------*/
	cout <<"-> Performing FIBER-TRACKING...\n";

	streamline TRACKER = streamline( &niiDIR );

	TRACKER.setConfig( &CONFIG );
	TRACKER.setWhiteMatterMask( &niiMASK );
	TRACKER.setSeedMask( !SEED_filename.empty() ? &niiSEED : NULL );

 	unsigned int tot_fibers = TRACKER.doTracking( TRK_filename );

	double elapsed_time = (time(NULL)-start_time);
	cout <<"\n-> "<< tot_fibers <<" fibers found.\n";

	cout <<"   [ time elapsed: "<< int(elapsed_time/3600.0) <<"h "<< (int)(elapsed_time/60.0) <<"' "<< (int)fmod(elapsed_time,60.0) <<"'' ]\n\n";

	return 0;
}
