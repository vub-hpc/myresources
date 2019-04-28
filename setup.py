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
installation script

@author: Samuel Moors, Vrije Universiteit Brussel (VUB)
"""

from setuptools import setup
from myresources import VERSION

setup(
    name='myresources',
    version=VERSION,
    description='myresources calculates job resource usage for running or recently finished jobs',
    url='https://github.com/sisc-hpc/myresources',
    classifiers=[
        'Programming Language :: Python :: 2.7',
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
    ],
    scripts=['myresources'],
    keywords='job resource usage torque HPC',
)

