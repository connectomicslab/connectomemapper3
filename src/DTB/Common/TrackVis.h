/**
 * Class for storing fibers in a file with TrackVis format (http://www.trackvis.org/docs/?subsect=fileformat)
 *
 * @author  alessandro.daducci@epfl.ch
 * @date, 08/03/2011
 */
#ifndef __TRACKVIS_H__
#define __TRACKVIS_H__


#define		TRACKVIS_SAVE_ALL		0
#define		TRACKVIS_SAVE_HALF		1
#define		TRACKVIS_SAVE_UNIQUE	2

#define		TRACKVIS_VOXEL_OFFSET	0



// Structure to hold metadata of a TrackVis file
// ---------------------------------------------
struct TrackVis_header
{
    char                id_string[6];
    short int           dim[3];
    float               voxel_size[3];
    float               origin[3];
    short int           n_scalars;
    char                scalar_name[10][20];
    short int           n_properties;
    char                property_name[10][20];
    char                reserved[508];
    char                voxel_order[4];
    char                pad2[4];
    float               image_orientation_patient[6];
    char                pad1[2];
    unsigned char       invert_x;
    unsigned char       invert_y;
    unsigned char       invert_z;
    unsigned char       swap_xy;
    unsigned char       swap_yz;
    unsigned char       swap_zx;
    int                 n_count;
    int                 version;
    int                 hdr_size;
};



// Class to handle TrackVis files.
// -------------------------------
class TrackVis
{
	private:
		string				filename;
		FILE* 				fp;
		int 				maxSteps;  // [TODO] should be related to the variable defined for fiber-tracking

	public:
		TrackVis_header		hdr;

		short 	create( string filename, short int* dim, float* pixdim );
		short 	open( string filename );
		short	append( blitz::Array<float,2>* fiber, int numPoints, short saveMethod=TRACKVIS_SAVE_UNIQUE );
		void	writeHdr();
		void	updateTotal( int totFibers );
		void	close();

		TrackVis();
		~TrackVis();
};


TrackVis::TrackVis()  { filename = ""; fp = NULL; maxSteps = 2000; }
TrackVis::~TrackVis() { if (fp) fclose( fp ); }



// Create a TrackVis file and store standard metadata. The file is ready to append fibers.
// ---------------------------------------------------------------------------------------
short TrackVis::create( string filename, short int* dim, float* pixdim )
{
	// prepare the header
	for(int i=0; i<3 ;i++)
	{
		if ( dim[i]<=0 || pixdim[i]<=0 ) return 0;
		hdr.dim[i] 			= dim[i];
		hdr.voxel_size[i] 	= pixdim[i];
		hdr.origin[i] 		= 0;
	}
    hdr.n_scalars = 0;
    hdr.n_properties = 0;
    sprintf(hdr.voxel_order,"LPS");
    sprintf(hdr.pad2,"LPS");
    hdr.image_orientation_patient[0] = 1.0;
	hdr.image_orientation_patient[1] = 0.0;
	hdr.image_orientation_patient[2] = 0.0;
	hdr.image_orientation_patient[3] = 0.0;
	hdr.image_orientation_patient[4] = 1.0;
	hdr.image_orientation_patient[5] = 0.0;
    hdr.pad1[0] = 0;
	hdr.pad1[1] = 0;
    hdr.invert_x = 0;
    hdr.invert_y = 0;
    hdr.invert_z = 0;
    hdr.swap_xy = 0;
    hdr.swap_yz = 0;
    hdr.swap_zx = 0;
    hdr.n_count = 0;
    hdr.version = 1;
    hdr.hdr_size = 1000;

	// write the header to the file
    fp = fopen(filename.c_str(),"w+b");
	if (fp == NULL) { printf("\n\n[ERROR] Unable to create file '%s'\n\n",filename.c_str()); return 0; }
	sprintf(hdr.id_string,"TRACK");
	fwrite((char*)&hdr, 1, 1000, fp);

	this->filename = filename;

	return 1;
}



// Open an existing TrackVis file and read metadata information.
// The file pointer is positiond at the beginning of fibers data
// -------------------------------------------------------------
short TrackVis::open( string filename )
{
	size_t bytesRead;
    fp = fopen(filename.c_str(),"r+b");
	if (fp == NULL) { printf("\n\n[ERROR] Unable to open file '%s'\n\n",filename.c_str()); return 0; }
	this->filename = filename;

	return fread((char*)(&hdr), 1, 1000, fp);
}



// Append a fiber to the file
// --------------------------
short TrackVis::append( blitz::Array<float,2>* fiber, int numPoints, short saveMethod )
{
	int 	numSaved, pos = 0;
	float 	tmp[3*maxSteps];

	if ( numPoints > maxSteps )
	{
		cerr <<"[ERROR] Trying to write a fiber too long!\n\n";
		return 0;
	}


	if ( saveMethod == TRACKVIS_SAVE_HALF )
	{
		// Save only 1 POINT OUT OF 2 (in reversed order), but include always the endpoints
		numSaved = ceil((float)(numPoints-1)/2)+1;
		for(int i=numPoints-1; i>0 ;i-=2)
		{
			tmp[pos++] = ( (*fiber)(0,i)+TRACKVIS_VOXEL_OFFSET );
			tmp[pos++] = ( (*fiber)(1,i)+TRACKVIS_VOXEL_OFFSET );
			tmp[pos++] = ( (*fiber)(2,i)+TRACKVIS_VOXEL_OFFSET );
		}
		tmp[pos++] = ( (*fiber)(0,0)+TRACKVIS_VOXEL_OFFSET );
		tmp[pos++] = ( (*fiber)(1,0)+TRACKVIS_VOXEL_OFFSET );
		tmp[pos++] = ( (*fiber)(2,0)+TRACKVIS_VOXEL_OFFSET );
	}
	else if ( saveMethod == TRACKVIS_SAVE_UNIQUE )
	{
		// Save UNIQUE points (discard consecutive points inside the same voxel)
		numSaved = 0;
		int oldX = 0, oldY = 0, oldZ = 0;
		int    X = 0,    Y = 0,    Z = 0;
	 	for(int i=0; i<numPoints ;i++)
		{
			X = floor( (*fiber)(0,i) );
			Y = floor( (*fiber)(1,i) );
			Z = floor( (*fiber)(2,i) );
			if ( pos==0 || X!=oldX || Y!=oldY || Z!=oldZ )
			{
				tmp[pos++] = ( (*fiber)(0,i)+TRACKVIS_VOXEL_OFFSET );
				tmp[pos++] = ( (*fiber)(1,i)+TRACKVIS_VOXEL_OFFSET );
				tmp[pos++] = ( (*fiber)(2,i)+TRACKVIS_VOXEL_OFFSET );
				oldX = X; oldY = Y; oldZ = Z;
				numSaved++;
			}
		}
	}
	else
	{
		// Save ALL points
		numSaved = numPoints;
	 	for(int i=0; i<numSaved ;i++)
		{
			tmp[pos++] = ( (*fiber)(0,i)+TRACKVIS_VOXEL_OFFSET );
			tmp[pos++] = ( (*fiber)(1,i)+TRACKVIS_VOXEL_OFFSET );
			tmp[pos++] = ( (*fiber)(2,i)+TRACKVIS_VOXEL_OFFSET );
		}
	}

	// write the coordinates to the file
	if ( fwrite((char*)&numSaved, 1, 4, fp) != 4 )
	{
		cerr<< "[ERROR] Problems saving the fiber!\n";
		return 1;
	}
	if ( fwrite((char*)&tmp, 1, 4*pos, fp) != 4*pos )
	{
		cerr<< "[ERROR] Problems saving the fiber!\n";
		return 1;
	}

	return 0;
}



// Update the field in the header to the new FIBER TOTAL.
// ------------------------------------------------------
void TrackVis::updateTotal( int totFibers )
{
	fseek(fp, 1000-12, SEEK_SET);
	fwrite((char*)&totFibers, 1, 4, fp);
}


void TrackVis::writeHdr()
{
	fseek(fp, 0, SEEK_SET);
	fwrite((char*)&hdr, 1, 1000, fp);
}


// Close the TrackVis file, but keep the metadata in the header.
// -------------------------------------------------------------
void TrackVis::close()
{
	fclose(fp);
	fp = NULL;
}

#endif
