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
Utilities for myresources
"""
from __future__ import division, print_function
import csv
import re
import sys

try:
    from StringIO import StringIO  # Python 2
except ImportError:
    from io import StringIO  # Python 3

from vsc.myresources.constants import (
    RESLIST,
    RES_NAMES,
    MEM_UNITS,
    TIME_UNITS,
    UNITS,
    FOR_FREE,
    LEVELS,
    WAITTIME,
    COLORCODE,
    FGCOL,
)


def convert_mem(mem):
    """
    convert memory string eg. '200mb' into a value in units of UNITS['mem']
    """
    if mem is None:
        return None
    value, unit = re.split(r"(\d+)", mem)[1:]
    value = float(value)
    unit = unit.lower()
    if unit not in MEM_UNITS.keys():
        sys.stderr.write("Error: memory unit %s not supported. Use one of %s instead.\n" % (unit, MEM_UNITS.keys()))
        sys.exit(1)
    return (value * MEM_UNITS[unit]) / MEM_UNITS[UNITS["mem"]]


def convert_time(time):
    """
    convert time string 'h:m:s' into a value in units of UNITS['walltime']
    torque always reports time in the format hh:mm:ss
    """
    if time is None:
        return None
    h, m, s = [float(i) for i in time.split(":")]
    seconds = h * TIME_UNITS["h"] + m * TIME_UNITS["m"] + s * TIME_UNITS["s"]
    return seconds / TIME_UNITS[UNITS["walltime"]]


def get_elem_text(tree, elemstr):
    """ get the text of an element in an xml element tree """
    elem = tree.find(elemstr)
    if elem is not None:
        return elem.text

    return None


def new_job():
    """ generate a new job dictionary with all values = None """
    job = dict.fromkeys(["jobid", "jobname", "state", "queue", "exit_status", "ppn", "nodes", "cput"])
    for res in RESLIST:
        job[res] = dict.fromkeys(["avail", "used", "usage", "usage_for_free"])
    return job


def parse_xml(jobdata):
    """
    parse an xml sub-tree containing data of 1 job
    returns: job dictionary
    """
    job = new_job()
    jobid = jobdata.find("Job_Id").text
    job["jobid"] = re.match(r"[0-9]*(\[[0-9]*\])?", jobid).group(0)
    job["jobname"] = jobdata.find("Job_Name").text
    job["state"] = jobdata.find("job_state").text  # ['Q', 'H', 'R', 'E', 'C']
    job["queue"] = jobdata.find("queue").text  # 'single_core', 'smp', 'mpi', 'gpu'

    if job["state"] in ("E", "C"):
        job["exit_status"] = get_elem_text(jobdata, "exit_status")

    # get the available resources
    avail = jobdata.find("Resource_List")
    if avail is not None:
        job["mem"]["avail"] = convert_mem(get_elem_text(avail, "mem"))
        job["walltime"]["avail"] = convert_time(get_elem_text(avail, "walltime"))
        job["nodes"] = get_elem_text(jobdata, "Resource_List/nodes")

    # get the used resources:
    if job["state"] in ("R", "E", "C"):
        used = jobdata.find("resources_used")
        if used is not None:
            job["mem"]["used"] = convert_mem(get_elem_text(used, "mem"))
            job["walltime"]["used"] = convert_time(get_elem_text(used, "walltime"))
            job["cput"] = convert_time(get_elem_text(used, "cput"))

    # calculate number of available cores
    if job["queue"] == "single_core" or job["nodes"] is None:
        job["ncore"]["avail"] = 1
        ppn_list = nodes_list = [1]
    else:
        job["ncore"]["avail"] = 0
        ppn_list = nodes_list = [1]
        # parse all possible ways nodes and cores can be requested
        # examples: '1:ppn=8+1:ppn=8' 'nic66:ppn=5+nic67:ppn=5' '1:ppn=8:enc8+1:ppn=8:enc8' '1:4' '1'
        for nodecore in job["nodes"].split("+"):
            nodecore = nodecore.split(":")
            node = nodecore[0]
            try:
                core = nodecore[1]
            except IndexError:
                core = "1"
            try:
                nnode = int(node)
            except ValueError:
                nnode = 1
            ppn = int(core.strip("ppn="))
            nodes_list.append(nnode)
            ppn_list.append(ppn)
            job["ncore"]["avail"] += nnode * ppn

    # calculate number of used cores
    if job["state"] in ("R", "E", "C"):
        if job["cput"] and job["walltime"]["used"] is not None:
            job["ncore"]["used"] = job["cput"] / job["walltime"]["used"]

    return job


def calc_usage(job):
    """ calculate resource usage """

    for res in RESLIST:
        if None not in (job[res]["avail"], job[res]["used"]):
            usage = 100.0 * job[res]["used"] / job[res]["avail"]
            job[res]["usage"] = round(usage)
            # do not show ncore usage if used walltime < WAITTIME
            # None is smaller than any number
            if res == "ncore" and job["walltime"]["used"] < WAITTIME:
                job[res]["usage"] = None
            job[res]["usage_for_free"] = 100.0 * FOR_FREE[res] / job[res]["avail"]
            if res == "mem":
                job[res]["usage_for_free"] *= job["ncore"]["avail"]

    return job


def usage_bar(usage, usage_for_free=0.0, lev=(50, 75, 95), show_rating=True, empty_bar=False, maxlen=20, color=True):
    """
    generate a color bar (string) showing resource usage and rating with color code: good/medium/bad
    arguments:
        usage: float between 0 and 100 (%)
        usage_for_free: usage that is counted as used for the rating, even if usage < usage_for_free
        lev: usage levels that determine the rating (medium, good, danger)
        show_rating: show rating and corresponding colors
        empty_bar: show an empty bar, no usage
        maxlen: total length of the color bar
        nocol: no colors, only black and white
    """

    if usage is None:
        empty_bar = True

    if empty_bar:
        empty_barstr = "|%20s|%9s" % (" ", " ")
        return empty_barstr

    usage = min(usage, 100)
    usage_for_free = min(usage_for_free, 100)
    usage_level = max(usage, usage_for_free)

    # set rating
    if show_rating is False:
        rating = "-"
    elif usage >= lev[2]:
        rating = "danger"
    elif usage_level >= lev[1]:
        rating = "good"
    elif usage_level >= lev[0]:
        rating = "medium"
    else:
        rating = "bad"

    unusedchar = "-"
    usedchar = u"\u2588"  # closed block

    if color:
        fgcolor = FGCOL[COLORCODE[rating]]
        fgreset = FGCOL["reset"]
    else:
        fgcolor = ""
        fgreset = ""

    # calculate bar lengths
    usedlen = int(round(maxlen * usage / 100.0))
    unusedlen = maxlen - usedlen

    # generate used and unused bar strings
    usedstr = usedchar * usedlen
    unusedstr = unusedchar * unusedlen

    bar_output = "|%s%s%s%s| (%s%s%s)" % (fgcolor, usedstr, fgreset, unusedstr, fgcolor, rating, fgreset,)
    bar_output = bar_output.ljust(49)
    if not color:
        bar_output = bar_output[:31]
    return bar_output.encode("utf-8")


def usage_string(job, color=True):
    """ write memory, walltime, and ncore usage to stdout """

    jobstr = " ".join([job["jobid"].rjust(13), job["state"], job["jobname"],])
    res_extrastrings = dict(zip(RESLIST, [jobstr, "", ""]))
    fresource = dict(
        zip(
            RESLIST,
            [
                {"avail": "%10.1f", "used": "%10.1f"},
                {"avail": "%10.1f", "used": "%10.1f"},
                {"avail": "%s  ", "used": "%10.1f"},
            ],
        )
    )

    res_fullstrings = dict.fromkeys(RESLIST, "")

    for res in RESLIST:
        empty_bar = False
        show_rating = True
        usage_for_free = job[res]["usage_for_free"]

        a_ulist = ["avail", "used"]
        a_ustr = dict.fromkeys(a_ulist, "-  ")
        for a_u in a_ulist:
            if job[res][a_u] is not None:
                a_ustr[a_u] = fresource[res][a_u] % job[res][a_u]

        if res == "walltime" and job["state"] == "R":
            show_rating = False

        usagestr = "- "
        if job[res]["usage"] is not None:
            usagestr = "%s%%" % int(round(job[res]["usage"]))

        ubar = usage_bar(
            job[res]["usage"],
            usage_for_free=usage_for_free,
            empty_bar=empty_bar,
            color=color,
            show_rating=show_rating,
            lev=LEVELS[res],
        )

        res_fullstrings[res] = " ".join(
            [
                RES_NAMES[res].rjust(12),
                a_ustr["used"].rjust(10),
                UNITS[res].rjust(2),
                a_ustr["avail"].rjust(10),
                UNITS[res].rjust(2),
                usagestr.rjust(6),
                ubar.rjust(31),
                res_extrastrings[res],
            ]
        )

    return "\n".join(res_fullstrings[res] for res in RESLIST)


def csv_string(job):
    full_list = [
        job["jobid"],
        job["state"],
        job["jobname"],
    ]
    for res in RESLIST:
        full_list.extend(
            [job[res]["avail"], job[res]["used"],]
        )
    csvstring = StringIO()
    writer = csv.writer(csvstring)
    writer.writerow(full_list)
    return csvstring.getvalue().rstrip()


def write_string(string):
    try:
        print(string)
    except IOError:
        # suppress broken pipe errors
        sys.exit()


def alert_mem(job):
    if job["mem"]["usage"] > LEVELS["mem"][2]:
        alert = (
            "Alert: memory close to the limit (%.0f %%). "
            "If your job failed, request more memory." % job["mem"]["usage"]
        )
        print(alert)
    if max(job["mem"]["usage"], job["mem"]["usage_for_free"]) < LEVELS["mem"][0]:
        alert = (
            "Alert: only %.1f gb of the requested %.1f gb memory used. "
            "Please request less memory to avoid wasting resources." % (job["mem"]["used"], job["mem"]["avail"])
        )
        print(alert)


def alert_walltime(job):
    if job["walltime"]["usage"] > LEVELS["walltime"][2]:
        alert = (
            "Alert: walltime close to the limit (%.0f %%). "
            "If your job failed, request more walltime." % job["walltime"]["usage"]
        )
        print(alert)


def alert_ncore(job):
    if job["ncore"]["usage"] is None:
        return
    if job["ncore"]["avail"] > 1 and job["ncore"]["usage"] + job["ncore"]["usage_for_free"] < LEVELS["ncore"][0]:
        alert = (
            "Alert: only %.1f of the requested %d cores used. "
            "Please request less cores or make sure your program uses all cores to avoid wasting resources."
            % (job["ncore"]["used"], job["ncore"]["avail"])
        )
        print(alert)


def alert_exit(job):
    if job["exit_status"] not in ("0", None):
        alert = "Alert: job stopped with non-zero exit code (%s)." % job["exit_status"]
        print(alert)


def write_alerts(job):
    alerts = {"mem": alert_mem, "walltime": alert_walltime, "ncore": alert_ncore}
    # Todo: this wrongly assumed that the order of keys in a dict is fixed
    # I've replace it with a list of the order it expects to not break any tests
    for res in ["mem", "walltime", "ncore"]:
        if job[res]["usage"] is not None:
            alerts[res](job)
    if job["exit_status"] is not None:
        alert_exit(job)


def write_header():
    fstring = "%12s %13s %13s %6s %31s %13s %1s %s"
    print(fstring % ("resource", "used", "requested", "usage", " ", "jobID", "S", "jobname"))
    print(fstring % ("--------", "----", "---------", "-----", " ", "-----", "-", "-------"))


def write_header_csv():
    print(
        ",".join(
            [
                "jobID",
                "state",
                "jobname",
                "walltime_avail",
                "walltime_used",
                "mem_avail",
                "mem_used",
                "ncore_avail",
                "ncore_used",
            ]
        )
    )
