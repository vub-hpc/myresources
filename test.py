#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright 2017-2019 Vrije Universiteit Brussel
#
# This file is part of myresources,
# originally created by the HPC team of Vrije Universiteit Brussel (https://hpc.vub.be),
# with support of Vrije Universiteit Brussel (https://www.vub.be),
# the Flemish Supercomputer Centre (VSC) (https://www.vscentrum.be),
# the Flemish Research Foundation (FWO) (http://www.fwo.be/en)
# and the Department of Economy, Science and Innovation (EWI) (http://www.ewi-vlaanderen.be/en).
#
# https://github.com/sisc-hpc/myresources
#
# myresources is free software: you can redistribute it and/or modify
# it under the terms of the GNU Library General Public License as
# published by the Free Software Foundation, either version 2 of
# the License, or (at your option) any later version.
#
# myresources is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU Library General Public License
# along with myresources. If not, see <http://www.gnu.org/licenses/>.
#
"""
test script

@author: Samuel Moors, Vrije Universiteit Brussel (VUB)
"""

from __future__ import print_function
import errno
from myresources import *
import os
import unittest


def read_file(filename):
    with open(filename, 'r') as f:
        return f.read()


def write_file(filename, data):
    with open(filename, 'w') as f:
        f.write(data)


def mkdir_p(path):
  try:
    os.makedirs(path)
  except OSError as exc:
    if exc.errno == errno.EEXIST:
      pass
    else: raise


class Testing(unittest.TestCase):
    def test_qstat_xml_files(self):
        ref_outlist = []
        outlist = []
        refdir = 'ref_output'
        testdir = 'test_output'
        mkdir_p(testdir)

        for i in range(1, 18):
            ref_out = read_file('%s/qstat%s.out' % (refdir, i))
            out = run_cmd('./myresources -f qstat_xml/qstat%s.xml' % i)
            write_file('%s/qstat%s.out' % (testdir, i), out)
            ref_outlist.append(ref_out)
            outlist.append(out)

        self.assertEqual(outlist, ref_outlist)


if __name__ == "__main__":
    unittest.main()
