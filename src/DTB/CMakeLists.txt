CMAKE_MINIMUM_REQUIRED(VERSION 2.8)

PROJECT( DTB )

IF(CMAKE_INSTALL_PREFIX_INITIALIZED_TO_DEFAULT)
	SET( CMAKE_INSTALL_PREFIX "${PROJECT_BINARY_DIR}/bin" CACHE PATH "where binaries will be installed" FORCE)
ENDIF( CMAKE_INSTALL_PREFIX_INITIALIZED_TO_DEFAULT )


#####################################################################################
########################  FIND PACKAGES USED  #######################################
#####################################################################################
set( CMAKE_MODULE_PATH "${PROJECT_SOURCE_DIR}/CMake" )

FIND_PACKAGE ( BLITZ REQUIRED )
FIND_PACKAGE ( NIFTI REQUIRED )
FIND_PACKAGE( Boost 1.40.0 REQUIRED COMPONENTS program_options )
SET(Boost_USE_STATIC_LIBS ON)
SET(Boost_USE_MULTITHREAD OFF)


#####################################################################################
###############################  SUBPROJECTS  #######################################
#####################################################################################
INCLUDE_DIRECTORIES ("${PROJECT_SOURCE_DIR}/Common")

ADD_SUBDIRECTORY( Applications )
