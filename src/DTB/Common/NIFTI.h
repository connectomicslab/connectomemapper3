/**
 * Class for handling multimensional NIFTI data.
 *
 * @author  alessandro.daducci@epfl.ch
 * @date, 08/03/2011
 */
#ifndef __NIFTI_H__
#define __NIFTI_H__

#include <blitz/array.h>
using namespace blitz;
#include <nifti1_io.h>


#ifdef INT_2_BYTES
	typedef	char				INT8;
	typedef	unsigned char		UINT8;
	typedef	int					INT16;
	typedef	unsigned int		UINT16;
	typedef	long				INT32;
	typedef	unsigned long		UINT32;
	typedef	double				FLOAT32;
#else
	typedef	char				INT8;
	typedef	unsigned char		UINT8;
	typedef	short				INT16;
	typedef	unsigned short		UINT16;
	typedef	int					INT32;
	typedef	unsigned int		UINT32;
	typedef	float				FLOAT32;
#endif


/* Errorcode used for the field "errorCode" */
#define		NIFTI_ERROR_NOERROR				0
#define		NIFTI_ERROR_WRONGFILETYPE		1
#define		NIFTI_ERROR_DATANOTLOADED		2
#define		NIFTI_ERROR_WRONGDATATYPE		3
#define		NIFTI_ERROR_UNKNOWN				9



/*****************************************************
  *****               NIFTI class                *****
  ****************************************************/
template <class T>
class NIFTI
{
	public:
		nifti_image* 	hdr;
		Array<T,7>*		img;

		short			isValid() { return errorCode==NIFTI_ERROR_NOERROR; };
		short			getErrorCode() { return errorCode; };

		short			make( const int ndims, const int* dim, const float* pixdim );
		short			open( string filename, bool loadData = true );
		short			load();
		short			unload();
		short			save( string NEW_filename = "" );
		void			copyHeader( const nifti_image* src );

		NIFTI( string filename, bool loadData = true );
		NIFTI();
		~NIFTI();

	private:
		short			errorCode;
		short			getDatatypeCode();
		short 			check_datatype( int dt );
};


/* Constructor/destructor */
template <class T>
NIFTI<T>::NIFTI( void )
{
	img			= NULL;
	hdr			= NULL;
	errorCode 	= NIFTI_ERROR_NOERROR;
};


template <class T>
NIFTI<T>::NIFTI( string filename, bool loadData )
{
	img		= NULL;
	hdr		= NULL;
	this->open( filename, loadData );
}


template <class T>
NIFTI<T>::~NIFTI()
{
 	if ( hdr ) nifti_image_unload( hdr );
 	if ( img ) img->free();
}


/* OPEN a nifti file (only the header is loaded) */
template <class T>
short NIFTI<T>::open( string filename, bool loadData )
{
	if ( img ) img->free();

	try
	{
		// not a NIFTI file
		if ( is_nifti_file(filename.c_str()) < 1 ) { errorCode = NIFTI_ERROR_WRONGFILETYPE; return 0; }

		hdr = nifti_image_read( filename.c_str(), 0);
		if ( hdr==NULL ) { errorCode = NIFTI_ERROR_DATANOTLOADED; return 0; }

		// wrong datatype chosen
		if ( !check_datatype( hdr->datatype ) ) { errorCode = NIFTI_ERROR_WRONGDATATYPE; return 0; }
	}
	catch(exception& ex)
    {
		errorCode = NIFTI_ERROR_UNKNOWN;
		return 0;
    }

	errorCode = NIFTI_ERROR_NOERROR;
	if ( loadData ) return this->load();
	return 1;
}


/*  MAKE a new dataset  */
template <class T>
short NIFTI<T>::make( const int ndims, const int* dim, const float* pixdim )
{
	if ( ndims<1 || ndims>7 ) return 0;

	int   d[8] = {0,1,1,1,1,1,1,1};
	float p[8] = {1,1,1,1,1,1,1,1};
	for(int i=0; i<ndims ;i++)
		{ d[i+1] = dim[i]; p[i+1] = pixdim[i]; }
	d[0] = ndims;

	nifti_image_unload( hdr );
	hdr = nifti_make_new_nim(d, this->getDatatypeCode(), 1);
	for(int i=0; i<ndims ;i++)
		hdr->pixdim[i+1] = p[i+1];
 	nifti_update_dims_from_array( hdr );

	try
	{
		if ( img ) img->free();
		img = new Array<T,7>( (T*)(hdr->data),
			shape(hdr->dim[1], hdr->dim[2], hdr->dim[3], hdr->dim[4], hdr->dim[5], hdr->dim[6], hdr->dim[7]),
			neverDeleteData, ColumnMajorArray<7>()
		);
	}
	catch(exception& ex)
    {
		return 0;
    }

 	return (img==NULL?0:1);
}



/*  LOAD/UNLOAD data  */
template <class T>
short NIFTI<T>::load()
{
	if ( errorCode>0 ) return 0;
 	if ( nifti_image_load(hdr) < 0 ) return 0;

	try
	{
		if ( img ) img->free();
		img = new Array<T,7>( (T*)(hdr->data),
			shape(hdr->dim[1], hdr->dim[2], hdr->dim[3], hdr->dim[4], hdr->dim[5], hdr->dim[6], hdr->dim[7]),
			neverDeleteData, ColumnMajorArray<7>()
		);
	}
	catch(exception& ex)
    {
		return 0;
    }

 	return (img==NULL?0:1);
}


template <class T>
short NIFTI<T>::unload( )
{
 	nifti_image_unload( hdr );
	if ( img ) img->free();
 	return 1;
}


/*  SAVE data  */
template <class T>
short NIFTI<T>::save( string NEW_filename )
{
	if ( !nifti_validfilename( NEW_filename.c_str() ) ) return 0;

	nifti_set_filenames( hdr, NEW_filename.c_str(), 0, hdr->byteorder);
	nifti_image_write( hdr );
 	return 1;
}



template <class T>
void NIFTI<T>::copyHeader( const nifti_image* src )
{
	if ( !src ) return;

	void* tmp = hdr->data;
	hdr = nifti_copy_nim_info( src );
	hdr->data = tmp;
}



/* valid datatypes */
template <class T>	short NIFTI<T      >::getDatatypeCode() { return DT_UNKNOWN; };
template <> 		short NIFTI<INT8   >::getDatatypeCode() { return DT_INT8;    };
template <> 		short NIFTI<UINT8  >::getDatatypeCode() { return DT_UINT8;   };
template <> 		short NIFTI<INT16  >::getDatatypeCode() { return DT_INT16;   };
template <> 		short NIFTI<UINT16 >::getDatatypeCode() { return DT_UINT16;  };
template <> 		short NIFTI<INT32  >::getDatatypeCode() { return DT_INT32;   };
template <> 		short NIFTI<UINT32 >::getDatatypeCode() { return DT_UINT32;  };
template <> 		short NIFTI<FLOAT32>::getDatatypeCode() { return DT_FLOAT32; };

template <class T>
short NIFTI<T>::check_datatype( int dt ) { return dt==this->getDatatypeCode(); };

#endif
