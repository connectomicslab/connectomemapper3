# $Id: Makefile,v 1.6 2008/10/29 01:01:35 ghantoos Exp $
#

PYTHON=python
DESTDIR=/
BUILDIR=$(CURDIR)/debian/cmp
PROJECT=cmp
VERSION=3.0.0-beta

all:
		@echo "make source - Create source package"
		@echo "make install - Install on local system"
		@echo "make buildrpm - Generate a rpm package"
		@echo "make builddeb - Generate a deb package"
		@echo "make clean - Get rid of scratch and byte files"

source:
		$(PYTHON) setup_core.py sdist $(COMPILE)
		$(PYTHON) setup_gui.py sdist $(COMPILE)

install:
		$(PYTHON) setup_core.py install --root $(DESTDIR) $(COMPILE)
		$(PYTHON) setup_gui.py install --root $(DESTDIR) $(COMPILE)

buildrpm:
		$(PYTHON) setup_core.py bdist_rpm --post-install=rpm/postinstall --pre-uninstall=rpm/preuninstall
		$(PYTHON) setup_gui.py bdist_rpm --post-install=rpm/postinstall --pre-uninstall=rpm/preuninstall

builddeb:
		# build the source package in the parent directory
		# then rename it to project_version.orig.tar.gz
		$(PYTHON) setup_core.py sdist $(COMPILE) --dist-dir=../ --prune
		rename -f 's/$(PROJECT)-(.*)\.tar\.gz/$(PROJECT)_$$1\.orig\.tar\.gz/' ../*
		# build the package
		dpkg-buildpackage -A -i -I -rfakeroot

		$(PYTHON) setup_gui.py sdist $(COMPILE) --dist-dir=../ --prune
		rename -f 's/$(PROJECT)-(.*)\.tar\.gz/$(PROJECT)_$$1\.orig\.tar\.gz/' ../*
		# build the package
		dpkg-buildpackage -A -i -I -rfakeroot

clean:
		$(PYTHON) setup.py clean
		$(MAKE) -f $(CURDIR)/debian/rules clean
		rm -rf build/ MANIFEST
		find . -name '*.pyc' -delete
