#
# Copyright 2020-2020 Vrije Universiteit Brussel
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
a bunch of constants
"""
VERSION = 3.2

# globals
RESLIST = ["walltime", "mem", "ncore"]
RES_NAMES = dict(zip(RESLIST, ["walltime", "memory", "cores"]))
MEM_UNITS = {"b": 1, "kb": 2 ** 10, "mb": 2 ** 20, "gb": 2 ** 30, "tb": 2 ** 40}
TIME_UNITS = {"s": 1, "m": 60, "h": 3600, "d": 3600 * 24}
UNITS = dict(zip(RESLIST, ["h", "gb", ""]))
# FOR_FREE = the amount of a given resource that we give 'for free': counted as used for the rating
# the FOR_FREE value of 'mem' is per core
FOR_FREE = dict(zip(RESLIST, [0.0, 2.0, 0.0]))
LEVELS = dict(zip(RESLIST, [(50, 75, 99), (50, 75, 95), (70, 85, 101)]))  # usage levels in %: (medium, good, danger)
WAITTIME = 1.0 / 12  # do not show ncore usage before this time
COLORCODE = {"good": "green", "medium": "yellow", "bad": "red", "-": "blue", "danger": "magenta"}
FGCOL = {  # foreground colors
    "green": u"\u001b[32m",
    "yellow": u"\u001b[33m",
    "red": u"\u001b[31m",
    "blue": u"\u001b[34m",
    "magenta": u"\u001b[35m",
    "reset": u"\u001b[0m",
}
