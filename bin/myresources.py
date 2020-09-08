#!/usr/bin/env python
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
myrsources script

@author: Samuel Moors, Vrije Universiteit Brussel (VUB)
"""

from __future__ import division, print_function
from argparse import ArgumentParser, RawDescriptionHelpFormatter
import sys
import xml.etree.cElementTree as ET

from vsc.utils.run import asyncloop

from vsc.myresources.constants import VERSION
from vsc.myresources.utils import (
    write_header,
    write_header_csv,
    write_alerts,
    write_string,
    calc_usage,
    parse_xml,
    csv_string,
    usage_string,
    new_job,
)


def demo_myresources(alerts=True, colors=True):
    write_header()
    for i in range(1, 5):
        job = new_job()
        job.update(
            {"jobid": str(i + 100000), "jobname": "my_super_job%s" % i, "state": "C",}
        )
        job["mem"].update({"avail": 20, "used": i * 5})
        job["walltime"].update({"avail": 16, "used": i * 4})
        job["ncore"].update({"avail": 4, "used": i})

        job = calc_usage(job)
        ustring = usage_string(job, colors=colors)
        write_string(ustring)

        if alerts:
            write_alerts(job)
        print("")


def main():
    """ main function """

    parser = ArgumentParser(
        description="""
Calculate job resource usage for running or recently finished jobs
This script can be used to check if requested resources are/were used optimally.

Resources:
 -memory:     random access memory
 -walltime:   wall-clock time
 -cores:      number of CPU cores are doing actual work

Color codes corresponding to ratings:
 -green:      good
 -yellow:     medium
 -red:        bad - wasting resources
 -magenta:    danger - close to the limit
 -blue:       no rating
        """,
        formatter_class=RawDescriptionHelpFormatter,
    )
    parser.add_argument("jobid", help="show only resources for given jobID(s) (default: show all)", nargs="*")
    parser.add_argument(
        "-a", "--noalert", dest="alerts", help="do not show alert messages", action="store_false", default=True)
    parser.add_argument("-f", "--infile", dest="infile", help="xml file (output of 'qstat -xt')")
    parser.add_argument(
        "-c", "--nocolor", dest="colors", help="do not use colors in the output", action="store_false", default=True)
    parser.add_argument("--csv", dest="csv", help="print as csv", action="store_true")
    parser.add_argument(
        "-s",
        "--state",
        dest="state",
        help='show only jobs with given state(s) as comma-separated list: "Q,H,R,E,C" (default: show all)',
    )
    parser.add_argument("-d", "--demo", dest="demo", help="show demo output and exit", action="store_true")
    parser.add_argument("-v", "--version", dest="version", help="show version and exit", action="store_true")

    args = parser.parse_args()

    if args.version:
        print("version: %s" % VERSION)
        sys.exit()

    if args.jobid:
        for i in args.jobid:
            try:
                int(i)
            except ValueError:
                raise ValueError("%s is not a valid jobID" % i)

    if args.demo:
        demo_myresources(alerts=args.alerts)
        sys.exit()

    if args.infile:
        try:
            tree = ET.parse(args.infile)
        except (IOError, ET.ParseError):
            print("Error parsing xml file: %s" % args.infile)
            sys.exit()
    else:
        _, xmlstring = asyncloop("qstat -xt")
        tree = ET.ElementTree(ET.fromstring(xmlstring))

    root = tree.getroot()
    if not root:
        sys.exit()

    if args.csv:
        write_header_csv()
    else:
        write_header()

    for jobdata in root:
        job = parse_xml(jobdata)
        if args.jobid:
            if job["jobid"] not in args.jobid:
                continue
        if args.state:
            states = args.state.split(",")
            if job["state"] not in states:
                continue

        job = calc_usage(job)
        if args.csv:
            csvstring = csv_string(job)
            write_string(csvstring)
        else:
            ustring = usage_string(job, colors=args.colors)
            write_string(ustring)
            if args.alerts:
                write_alerts(job)
            print("")


if __name__ == "__main__":
    main()
    #    suppress the following error when piping the output:
    #        close failed in file object destructor:
    #        sys.excepthook is missing
    #        lost sys.stderr
    try:
        sys.stdout.close()
    except IOError:
        pass
    try:
        sys.stderr.close()
    except IOError:
        pass
