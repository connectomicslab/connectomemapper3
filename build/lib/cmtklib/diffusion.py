# Copyright (C) 2009-2015, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" CMTK Diffusion functions
""" 

import os
import numpy as np
import nibabel.trackvis as tv

from util import length

def compute_length_array(trkfile=None, streams=None, savefname = 'lengths.npy'):
    if streams is None and not trkfile is None:
        print("Compute length array for fibers in %s" % trkfile)
        streams, hdr = tv.read(trkfile, as_generator = True)
        n_fibers = hdr['n_count']
        if n_fibers == 0:
            msg = "Header field n_count of trackfile %s is set to 0. No track seem to exist in this file." % trkfile
            print(msg)
            raise Exception(msg)
    else:
        n_fibers = len(streams)
        
    leng = np.zeros(n_fibers, dtype = np.float)
    for i,fib in enumerate(streams):
        leng[i] = length(fib[0])
    
    # store length array
    np.save(savefname, leng)
    print("Store lengths array to: %s" % savefname)
    
    return leng
    

def filter_fibers(intrk, outtrk='', fiber_cutoff_lower=20, fiber_cutoff_upper=500):
    
    print("Cut Fiber Filtering")
    print("===================")
        
    print("Input file for fiber cutting is: %s" % intrk)
    
    if outtrk == '':
        path, filename = os.path.split(intrk)
        base, ext = os.path.splitext(filename)
        outtrk = os.path.abspath(base + '_cutfiltered' + ext)
    
    # compute length array
    le = compute_length_array(intrk)
    
    # cut the fibers smaller than value
    reducedidx = np.where((le>fiber_cutoff_lower) & (le<fiber_cutoff_upper))[0]
    
    # load trackfile (downside, needs everything in memory)
    fibold, hdrold = tv.read(intrk)
    
    # rewrite the track vis file with the reduced number of fibers
    outstreams = []
    for i in reducedidx:
        outstreams.append( fibold[i] )
    
    n_fib_out = len(outstreams)
    hdrnew = hdrold.copy()
    hdrnew['n_count'] = n_fib_out
    
    #print("Compute length array for cutted fibers")
    #le = compute_length_array(streams=outstreams)
    print("Write out file: %s" % outtrk)
    print("Number of fibers out : %d" % hdrnew['n_count'])
    tv.write(outtrk, outstreams, hdrnew)
    print("File wrote : %d" % os.path.exists(outtrk))
    
    # ----
    # extension idea
    
    # find a balance between discarding spurious fibers and still
    # keep cortico-cortico ones, amidst of not having ground-truth
    
    # compute a downsampled version of the fibers using 4 points
    
    # discard smaller than x mm fibers
    # and which have a minimum angle smaller than y degrees
