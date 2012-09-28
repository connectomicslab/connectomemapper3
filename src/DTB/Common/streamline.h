/**
 * Class to perform standard streamline fiber-tracking.
 *
 * @author  alessandro.daducci@epfl.ch
 * @date, 08/03/2011
 */
#ifndef __STREAMLINE_H__
#define __STREAMLINE_H__


#include <random/uniform.h>
#include <blitz/array.h>
#include "NIFTI.h"
#include "TrackVis.h"
#include "utils.h"
using namespace blitz;
using namespace std;


typedef Array<float,2> FIBER;


/**********************************************/
/*  PARAMETERS for streamline fiber-tracking  */
/**********************************************/
class tracking_config
{
	public:
		int 	seeds, minLength, maxLength;
		float	stepSize, volFracThr, maxAngle;

		tracking_config();
};

tracking_config::tracking_config()
{
	seeds		= 1;
	minLength	= 10;
	maxLength	= 1000;
 	stepSize	= 1;
 	volFracThr	= 0;
 	maxAngle	= 45;
}



/*****************************************/
/*  STREAMLINE fiber-tracking algorithm  */
/*****************************************/
class streamline
{
	private:
		float					ANGLE_thr;
		Vec3Df					COORD_seed, COORD, dir;
		Vec3Di 					VOXEL_dsi, VOXEL_wm;
		FIBER					tmp;

		ranlib::Uniform<float> 	uniformGenerator;


	public:
		tracking_config* 	CONFIG;
		NIFTI<FLOAT32>* 	niiDIR;
		NIFTI<UINT8>* 		niiMASK;
		NIFTI<UINT8>* 		niiSEED;

		Array<FIBER,1>			FIBERs;
		Array<unsigned int,1>	LENGTHs;


		void			setConfig( tracking_config* CONFIG );
		void			setWhiteMatterMask( NIFTI<UINT8>* nii );
		void			setSeedMask( NIFTI<UINT8>* nii );

		bool 			pickBestDir( const Vec3Di &VOXEL_dsi, Vec3Df &vec );

		short			trackFromXYZ( int x, int y, int z );
		unsigned int	doTracking( string TRK_filename );


		streamline( NIFTI<FLOAT32>* nii );
		~streamline();
};


streamline::streamline( NIFTI<FLOAT32>* nii )
{
	this->niiDIR = nii;
	uniformGenerator.seed( (unsigned int)time(0) );
}


streamline::~streamline()
{
	this->niiDIR->img->free();
}


void streamline::setConfig( tracking_config* CONFIG )
{
	this->CONFIG = CONFIG;
	ANGLE_thr = cos(CONFIG->maxAngle/180.0*3.14159265);
	FIBERs.resize(  CONFIG->seeds*3 );
	LENGTHs.resize( CONFIG->seeds*3 );
	for(int i=0; i<CONFIG->seeds*3 ;i++)
		FIBERs(i).resize(3,CONFIG->maxLength);
}


void streamline::setWhiteMatterMask( NIFTI<UINT8>* nii )
{
	/* check for the FOV between MASK and DIR datasets */
	if ( nii->hdr->dim[1]*nii->hdr->pixdim[1] != niiDIR->hdr->dim[1]*niiDIR->hdr->pixdim[1] ||
		 nii->hdr->dim[2]*nii->hdr->pixdim[2] != niiDIR->hdr->dim[2]*niiDIR->hdr->pixdim[2] ||
		 nii->hdr->dim[3]*nii->hdr->pixdim[3] != niiDIR->hdr->dim[3]*niiDIR->hdr->pixdim[3] )
	{
		cout<<"\n[WARNING] The FOV doesn't match between WM MASK and DIR! The software could CRASH or give weird results!\n";
	}

	niiMASK = nii;
}


void streamline::setSeedMask( NIFTI<UINT8>* nii )
{
	niiSEED = nii;
	if ( nii==NULL ) return;		// it means it will try all possible diffusion voxels

	if (
		nii->hdr->pixdim[1] != niiDIR->hdr->pixdim[1] ||
		nii->hdr->pixdim[2] != niiDIR->hdr->pixdim[2] ||
		nii->hdr->pixdim[3] != niiDIR->hdr->pixdim[3] ||
		nii->hdr->dim[1] != niiDIR->hdr->dim[1] ||
		nii->hdr->dim[2] != niiDIR->hdr->dim[2] ||
		nii->hdr->dim[3] != niiDIR->hdr->dim[3]
		)
	{
		cerr<<"\n[ERROR] the SEED MASK must have the same geometry of DIR dataset!\n";
		exit(1);
	}

	niiSEED = nii;
}



/************************************************************************************************/
/******                                    doTracking()                                    ******/
/************************************************************************************************/
unsigned int streamline::doTracking( string TRK_filename )
{
	if ( !CONFIG || !niiMASK ) return 0;

	// create ".trk" file(s)
	TrackVis TRK_file = TrackVis();
	short dim[3] 	= {niiMASK->hdr->dim[1], niiMASK->hdr->dim[2], niiMASK->hdr->dim[3]};
	float pixdim[3] = {niiMASK->hdr->pixdim[1], niiMASK->hdr->pixdim[2], niiMASK->hdr->pixdim[3]};
	TRK_file.create( TRK_filename, dim, pixdim );


	/* cycle on each voxel = 1 of the SEED mask (or ALL if this mask is NULL) */
	float VOXELS_percent = 0, VOXELS_tot = niiDIR->hdr->dim[1]*niiDIR->hdr->dim[2]*niiDIR->hdr->dim[3];
	unsigned short foundAtXYZ;
	int tot_fibers = 0;

  	for(int z=0; z < niiDIR->hdr->dim[3] ;z++)
  	for(int y=0; y < niiDIR->hdr->dim[2] ;y++)
  	for(int x=0; x < niiDIR->hdr->dim[1] ;x++)
	{
		VOXELS_percent++;
		if ( niiSEED && (*niiSEED->img)(x,y,z)==0 ) continue;

		foundAtXYZ = trackFromXYZ( x, y, z );

		/* SAVE found fibers to .trk file */
		FIBER* fiber;
		for(int i=0; i<foundAtXYZ ;i++)
		{
			fiber = &FIBERs(i);

			// GLOBAL FILTER based on some properties of fibers (length etc)
			if	(
					(LENGTHs(i)-1)*CONFIG->stepSize*niiDIR->hdr->pixdim[1] >= CONFIG->minLength
				)
			{
				TRK_file.append( fiber, LENGTHs(i), TRACKVIS_SAVE_UNIQUE );
				tot_fibers++;
			}
		}

  		printf("\r   [ %5.1f%% ]", 100.0 * VOXELS_percent / VOXELS_tot);

	} // niiSEED loop
	printf("\r   [ 100.0%% ]\n");


	// write the TOTAL number of found fibers
	TRK_file.updateTotal( tot_fibers );
	TRK_file.close();

	return tot_fibers;
}



short streamline::trackFromXYZ( int x, int y, int z )
{
	if (
		x < 0 || x > niiDIR->hdr->dim[1]-1 ||
		y < 0 || y > niiDIR->hdr->dim[2]-1 ||
		z < 0 || z > niiDIR->hdr->dim[3]-1
	) return 0;

	static int		found, step;
	static bool 	dirFound;

	found = 0;
	for(int seedNum=0; seedNum<CONFIG->seeds ;seedNum++)
	{
		// SETUP a new seed point inside the DIFFUSION VOXEL
		COORD_seed.x = ((float)x + uniformGenerator.random()) * niiDIR->hdr->pixdim[1];
		COORD_seed.y = ((float)y + uniformGenerator.random()) * niiDIR->hdr->pixdim[2];
		COORD_seed.z = ((float)z + uniformGenerator.random()) * niiDIR->hdr->pixdim[3];

		// check whether this point is INSIDE the WM MASK
		VOXEL_wm.x = floor( COORD_seed.x/niiMASK->hdr->pixdim[1] );
		VOXEL_wm.y = floor( COORD_seed.y/niiMASK->hdr->pixdim[2] );
		VOXEL_wm.z = floor( COORD_seed.z/niiMASK->hdr->pixdim[3] );
		if (
			VOXEL_wm.x < 0 || VOXEL_wm.x > niiMASK->hdr->dim[1]-1 ||
			VOXEL_wm.y < 0 || VOXEL_wm.y > niiMASK->hdr->dim[2]-1 ||
			VOXEL_wm.z < 0 || VOXEL_wm.z > niiMASK->hdr->dim[3]-1 ||
			(*niiMASK->img)(VOXEL_wm.x,VOXEL_wm.y,VOXEL_wm.z) == 0
		) break;


		/* try with EACH POSSIBLE DIRECTION in the seed voxel */
		for(int seedDir=0; seedDir<3 ;seedDir++)
		{
			if ( (*niiDIR->img)(x,y,z, seedDir*4) <= CONFIG->volFracThr ) continue;

			// propagate a new trajectory until any STOP CRITERION is matched
			dir.x = (*niiDIR->img)(x,y,z, seedDir*4+1);
			dir.y = (*niiDIR->img)(x,y,z, seedDir*4+2);
			dir.z = (*niiDIR->img)(x,y,z, seedDir*4+3);

			FIBERs(found)(0,0) = COORD_seed.x;
			FIBERs(found)(1,0) = COORD_seed.y;
			FIBERs(found)(2,0) = COORD_seed.z;

			FIBERs(found)(0,1) = COORD_seed.x + CONFIG->stepSize*dir.x;
			FIBERs(found)(1,1) = COORD_seed.y + CONFIG->stepSize*dir.y;
			FIBERs(found)(2,1) = COORD_seed.z + CONFIG->stepSize*dir.z;
			// [TODO] should this point be ckecked if it is inside the WM??

			COORD.x = FIBERs(found)(0,1);
			COORD.y = FIBERs(found)(1,1);
			COORD.z = FIBERs(found)(2,1);

			step = 2;
			for(int semi_step=0; semi_step<2 ;semi_step++)
			{
				dir.x = FIBERs(found)(0,step-1) - FIBERs(found)(0,step-2);
				dir.y = FIBERs(found)(1,step-1) - FIBERs(found)(1,step-2);
				dir.z = FIBERs(found)(2,step-1) - FIBERs(found)(2,step-2);
				Normalize( dir );

				while( step<CONFIG->maxLength )
				{
					// stop the fiber if it is outside the WM MASK
					VOXEL_wm.x = floor( COORD.x/niiMASK->hdr->pixdim[1] );
					VOXEL_wm.y = floor( COORD.y/niiMASK->hdr->pixdim[2] );
					VOXEL_wm.z = floor( COORD.z/niiMASK->hdr->pixdim[3] );
					if (
						VOXEL_wm.x < 0 || VOXEL_wm.x > niiMASK->hdr->dim[1]-1 ||
						VOXEL_wm.y < 0 || VOXEL_wm.y > niiMASK->hdr->dim[2]-1 ||
						VOXEL_wm.z < 0 || VOXEL_wm.z > niiMASK->hdr->dim[3]-1 ||
						(*niiMASK->img)(VOXEL_wm.x,VOXEL_wm.y,VOXEL_wm.z) == 0
					) break;

					// find NEXT DIRECTION to follow
					VOXEL_dsi.x = floor( COORD.x/niiDIR->hdr->pixdim[1] );
					VOXEL_dsi.y = floor( COORD.y/niiDIR->hdr->pixdim[2] );
					VOXEL_dsi.z = floor( COORD.z/niiDIR->hdr->pixdim[3] );

					dirFound = pickBestDir( VOXEL_dsi, dir );
					if ( !dirFound ) break; // NO COMPATIBLE DIRECTIONS

					COORD.x = COORD.x + CONFIG->stepSize * dir.x;
					COORD.y = COORD.y + CONFIG->stepSize * dir.y;
					COORD.z = COORD.z + CONFIG->stepSize * dir.z;

					FIBERs(found)(0,step) = COORD.x;
					FIBERs(found)(1,step) = COORD.y;
					FIBERs(found)(2,step) = COORD.z;
					step++;
				}


				/* reverse the first part of the fiber and run the second part (opposite dir) */
				if (semi_step==0)
				{
					COORD.x = FIBERs(found)(0,0);
					COORD.y = FIBERs(found)(1,0);
					COORD.z = FIBERs(found)(2,0);

					tmp.resize(3,step);
					tmp = FIBERs(found)(Range(0,2),Range(0,step-1));
					tmp.reverseSelf(1);
					FIBERs(found)(Range(0,2),Range(0,step-1)) = tmp;
				}
			}

			LENGTHs(found++) = step;
		}
	}

	return found;
}



/* Pick up the closest direction to "vec" inside the present voxel */
bool streamline::pickBestDir( const Vec3Di & voxel, Vec3Df & vec )
{
	static int idx, i;
	static float max, DOT, DOTabs;

	idx = max = 0;
	for(i=0; i<3 ;i++)
	{
		if ( (*niiDIR->img)( voxel.x, voxel.y, voxel.z, i*4) <= CONFIG->volFracThr ) continue;

		DOT =
			vec.x * (*niiDIR->img)( voxel.x, voxel.y, voxel.z, i*4+1) +
			vec.y * (*niiDIR->img)( voxel.x, voxel.y, voxel.z, i*4+2) +
			vec.z * (*niiDIR->img)( voxel.x, voxel.y, voxel.z, i*4+3);
		DOTabs = abs(DOT);
		if ( DOTabs > ANGLE_thr && DOTabs > max )
		{
			max = DOTabs;
			idx = ( DOT>0 ? i+1: -(i+1) );
		}
	}
	if ( idx==0 ) return false;

	i = (idx<0?-1:+1);
	idx = (abs(idx)-1)*4;
	vec.x = i * (*niiDIR->img)( voxel.x, voxel.y, voxel.z, idx+1);
	vec.y = i * (*niiDIR->img)( voxel.x, voxel.y, voxel.z, idx+2);
	vec.z = i * (*niiDIR->img)( voxel.x, voxel.y, voxel.z, idx+3);
	return true;
}


#endif
