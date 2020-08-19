# -*- coding: utf-8 -*-
#
# Copyright 2017-2020 Vrije Universiteit Brussel
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
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation v2.
#
# myresources is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with myresources.  If not, see <http://www.gnu.org/licenses/>.
#
"""
test script

@author: Samuel Moors, Vrije Universiteit Brussel (VUB)
"""

from __future__ import print_function
import os
import sys
try:
    from StringIO import StringIO  # Python 2
except ImportError:
    from io import StringIO  # Python 3

import xml.etree.cElementTree as ET

from vsc.install.testing import TestCase
from vsc.myresources.utils import (
    write_header, write_alerts, write_string,
    calc_usage, parse_xml, usage_string
)


def read_file(filename):
    with open(filename, 'r') as f:
        return f.read()


def dummy_main(inputfile):
    try:
        tree = ET.parse(inputfile)
    except (IOError, ET.ParseError):
        print('Error parsing xml file: %s' % inputfile)

    root = tree.getroot()
    write_header()

    for jobdata in root:
        job = parse_xml(jobdata)
        job = calc_usage(job)
        ustring = usage_string(job)
        write_string(ustring)
        write_alerts(job)
        print('')


class Testing(TestCase):
    def test_qstat_xml_files(self):
        test_dir = os.path.dirname(os.path.abspath(__file__))
        stdout_orig = sys.stdout

        for i in range(1, 19):
            ref_out = read_file(os.path.join(test_dir, 'ref_output', 'qstat%s.out' % i))
            output = StringIO()
            sys.stdout = output
            dummy_main(os.path.join(test_dir, 'qstat_xml', 'qstat%s.xml' % i))
            sys.stdout = stdout_orig
            self.assertEqual(ref_out, output.getvalue(), "test %d failed" % i)
