DTB
===

For DTB compilation, you need the following development packages::

    sudo apt-get install cmake-curses-gui libboost1.40-all-dev libnifti-dev libblitz0-dev

The compiled binaries should be put into cmp/binary/ folders accordingly.

To compile, go to DTB/ and type

    ccmake .

Then configure and save and type to build the binaries

    make
