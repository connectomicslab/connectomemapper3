#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: sebastientourbier
# @Date:   2019-01-04 08:58:38
import sys
import os.path as op


def main():
    sys.path.insert(0, op.abspath('.'))
    from cmp.multiscalebrainparcellator.info import __version__
    print(__version__)


if __name__ == '__main__':
    main()
