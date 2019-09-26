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
myrsources script

@author: Samuel Moors, Vrije Universiteit Brussel (VUB)
"""

from __future__ import division, print_function
from argparse import ArgumentParser, RawDescriptionHelpFormatter
import datetime as dt
import re
from subprocess import Popen, PIPE, CalledProcessError
import sys
import xml.etree.cElementTree as ET


VERSION = 2.1


# globals
reslist = ['walltime', 'mem', 'ncore']
res_names = dict(zip(reslist, ['walltime', 'memory', 'cores']))
mem_units = {'b': 1, 'kb': 2**10, 'mb': 2**20, 'gb': 2**30, 'tb': 2**40}
time_units = {'s': 1, 'm': 60, 'h': 3600, 'd': 3600 * 24}
units = dict(zip(reslist, ['h', 'gb', '']))
# for_free = the amount of a given resource that we give 'for free': counted as used for the rating
# the for_free value of 'mem' is per core
for_free = dict(zip(reslist, [0.0, 2.0, 0.0]))
levels = dict(zip(reslist, [(50, 75, 99), (50, 75, 95), (70, 85, 101)]))  # usage levels in %: (medium, good, danger)
noalert = False
nocolor = False
waittime = 1.0 / 12  # do not show ncore usage before this time
colorcode = {'good': 'green', 'medium': 'yellow', 'bad': 'red', '-': 'blue', 'danger': 'magenta'}
fgcol = {
    'green': u'\u001b[32m',
    'yellow': u'\u001b[33m',
    'red': u'\u001b[31m',
    'blue': u'\u001b[34m',
    'magenta': u'\u001b[35m',
    'reset': u'\u001b[0m',
}


def run_cmd(cmd):
    """ execute a shell command and return the stdout output """
    cmdlist = cmd.split()
#     p = Popen(' '.join(cmdlist), stdout=PIPE, stderr=PIPE, shell=True)
    p = Popen(cmdlist, stdout=PIPE, stderr=PIPE)
    (out, err) = p.communicate()
    if err:
        sys.stderr.write('Error: failed to execute command "%s" (%s)\n' % (cmd, err))
        sys.exit(1)
    return out


def convert_mem(mem):
    """
    convert memory string eg. '200mb' into a value in units of units['mem']
    """
    if mem is None:
        return None
    value, unit = re.split(r'(\d+)', mem)[1:]
    value = float(value)
    unit = unit.lower()
    if unit not in mem_units.keys():
        sys.stderr.write(
            'Error: memory unit %s not supported. Use one of %s instead.\n' % (unit, mem_units.keys())
        )
        sys.exit(1)
    return (value * mem_units[unit]) / mem_units[units['mem']]


def convert_time(time):
    """
    convert time string 'h:m:s' into a value in units of units['walltime']
    torque always reports time in the format hh:mm:ss
    """
    if time is None:
        return None
    h, m, s = [float(i) for i in time.split(':')]
    seconds = h * time_units['h'] + m * time_units['m'] + s * time_units['s']
    return seconds / time_units[units['walltime']]


def get_elem_text(tree, elemstr):
    """ get the text of an element in an xml element tree """
    elem = tree.find(elemstr)
    if elem is not None:
        return elem.text
    else:
        return None


def new_job():
    """ generate a new job dictionary with all values = None """
    job = dict.fromkeys(['jobid', 'jobname', 'state', 'queue', 'exit_status', 'ppn', 'nodes', 'cput'])
    for res in reslist:
        job[res] = dict.fromkeys(['avail', 'used', 'usage', 'usage_for_free'])
    return job


def parse_xml(jobdata):
    """
    parse an xml sub-tree containing data of 1 job
    returns: job dictionary
    """
    job = new_job()
    jobid = jobdata.find('Job_Id').text
    job['jobid'] = re.match(r'[0-9]*(\[[0-9]*\])?', jobid).group(0)
    job['jobname'] = jobdata.find('Job_Name').text
    job['state'] = jobdata.find('job_state').text  # ['Q', 'H', 'R', 'E', 'C']
    job['queue'] = jobdata.find('queue').text  # 'single_core', 'smp', 'mpi', 'gpu'

    if job['state'] in ('E', 'C'):
        job['exit_status'] = get_elem_text(jobdata, 'exit_status')

    # get the available resources
    avail = jobdata.find('Resource_List')
    if avail is not None:
        job['mem']['avail'] = convert_mem(get_elem_text(avail, 'mem'))
        job['walltime']['avail'] = convert_time(get_elem_text(avail, 'walltime'))
        job['nodes'] = get_elem_text(jobdata, 'Resource_List/nodes')

    # get the used resources:
    if job['state'] in ('R', 'E', 'C'):
        used = jobdata.find('resources_used')
        if used is not None:
            job['mem']['used'] = convert_mem(get_elem_text(used, 'mem'))
            job['walltime']['used'] = convert_time(get_elem_text(used, 'walltime'))
            job['cput'] = convert_time(get_elem_text(used, 'cput'))

    # calculate number of available cores
    if job['queue'] == 'single_core' or job['nodes'] is None:
        job['ncore']['avail'] = 1
        ppn_list = nodes_list = [1]
    else:
        job['ncore']['avail'] = 0
        ppn_list = nodes_list = [1]
        # parse all possible ways nodes and cores can be requested
        # examples: [1:ppn=8+1:ppn=8] [nic66:ppn=5+nic67:ppn=5] [1:ppn=8:enc8+1:ppn=8:enc8] [1:4]
        for nodecore in job['nodes'].split('+'):
            node, core = nodecore.split(':')[:2]
            try:
                nnode = int(node)
            except ValueError:
                nnode = 1
            ppn = int(core.strip('ppn='))
            nodes_list.append(nnode)
            ppn_list.append(ppn)
            job['ncore']['avail'] += nnode * ppn

    # calculate number of used cores
    if job['state'] in ('R', 'E', 'C'):
        if job['cput'] and job['walltime']['used'] is not None:
            job['ncore']['used'] = job['cput'] / job['walltime']['used']

    return job


def calc_usage(job):
    """ calculate resource usage """

    for res in reslist:
        if None not in (job[res]['avail'], job[res]['used']):
            usage = 100.0 * job[res]['used'] / job[res]['avail']
            job[res]['usage'] = round(usage)
            # do not show ncore usage if used walltime < waittime
            # None is smaller than any number
            if res == 'ncore' and job['walltime']['used'] < waittime:
                job[res]['usage'] = None
            job[res]['usage_for_free'] = 100.0 * for_free[res] / job[res]['avail']
            if res == 'mem':
                job[res]['usage_for_free'] *= job['ncore']['avail']

    return job


def usage_bar(usage, usage_for_free=0.0, lev=(50, 75, 95), show_rating=True, empty_bar=False, maxlen=20, nocol=False):
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
        empty_barstr = '|%20s|%9s' % (' ', ' ')
        return empty_barstr

    usage = min(usage, 100)
    usage_for_free = min(usage_for_free, 100)
    usage_level = max(usage, usage_for_free)

    # set rating
    if show_rating is False:
        rating = '-'
    elif usage >= lev[2]:
        rating = 'danger'
    elif usage_level >= lev[1]:
        rating = 'good'
    elif usage_level >= lev[0]:
        rating = 'medium'
    else:
        rating = 'bad'

    unusedchar = '-'
    usedchar = u'\u2588'  # closed block

    if nocol:
        fgcolor = ''
        fgreset = ''
    else:
        fgcolor = fgcol[colorcode[rating]]
        fgreset = fgcol['reset']

    # calculate bar lengths
    usedlen = int(round(maxlen * usage / 100.0))
    unusedlen = maxlen - usedlen

    # generate used and unused bar strings
    usedstr = usedchar * usedlen
    unusedstr = unusedchar * unusedlen

    bar = '|%s%s%s%s| (%s%s%s)' % (
        fgcolor,
        usedstr,
        fgreset,
        unusedstr,
        fgcolor,
        rating,
        fgreset,
    )
    bar = bar.ljust(49)
    if nocol:
        bar = bar[:31]
    return bar.encode('utf-8')


def usage_string(job):
    """ write memory, walltime, and ncore usage to stdout """

    jobstr = ' '.join([
        job['jobid'].rjust(13),
        job['state'],
        job['jobname'],
    ])
    res_extrastrings = dict(zip(reslist, [jobstr, '', '']))
    fresource = dict(zip(reslist, [
        {'avail': '%10.1f', 'used': '%10.1f'},
        {'avail': '%10.1f', 'used': '%10.1f'},
        {'avail': '%s  ', 'used': '%10.1f'},
    ]))

    res_fullstrings = dict.fromkeys(reslist, '')

    for res in reslist:
        empty_bar = False
        show_rating = True
        usage_for_free = job[res]['usage_for_free']

        a_ulist = ['avail', 'used']
        a_ustr = dict.fromkeys(a_ulist, '-  ')
        for a_u in a_ulist:
            if job[res][a_u] is not None:
                a_ustr[a_u] = fresource[res][a_u] % job[res][a_u]

        if (res == 'walltime' and job['state'] == 'R'):
            show_rating = False

        usagestr = '- '
        if job[res]['usage'] is not None:
            usagestr = '%s%%' % int(round(job[res]['usage']))

        ubar = usage_bar(
            job[res]['usage'],
            usage_for_free=usage_for_free,
            empty_bar=empty_bar,
            nocol=nocolor,
            show_rating=show_rating,
            lev=levels[res],
        )

        res_fullstrings[res] = ' '.join([
            res_names[res].rjust(12),
            a_ustr['used'].rjust(10),
            units[res].rjust(2),
            a_ustr['avail'].rjust(10),
            units[res].rjust(2),
            usagestr.rjust(6),
            ubar.rjust(31),
            res_extrastrings[res],
        ])

    return '\n'.join(res_fullstrings[res] for res in reslist)


def write_string(string):
    try:
        print(string)
    except IOError:
        # suppress broken pipe errors
        sys.exit()


def alert_mem(job):
    if job['mem']['usage'] > levels['mem'][2]:
        alert = ('Alert: memory close to the limit (%.0f %%). '
                 'If your job failed, request more memory.' % job['mem']['usage'])
        print(alert)
    if max(job['mem']['usage'], job['mem']['usage_for_free']) < levels['mem'][0]:
        alert = ('Alert: only %.1f gb of the requested %.1f gb memory used. '
                 'Please request less memory to avoid waisting resources.' % (job['mem']['used'], job['mem']['avail']))
        print(alert)


def alert_walltime(job):
    if job['walltime']['usage'] > levels['walltime'][2]:
        alert = ('Alert: walltime close to the limit (%.0f %%). '
                 'If your job failed, request more walltime.' % job['walltime']['usage'])
        print(alert)


def alert_ncore(job):
    if job['ncore']['usage'] is None:
        return
    if job['ncore']['avail'] > 1 and job['ncore']['usage'] + job['ncore']['usage_for_free'] < levels['ncore'][0]:
        alert = ('Alert: only %.1f of the requested %d cores used. '
                 'Please request less cores or make sure your program uses all cores to avoid waisting resources.' %
                 (job['ncore']['used'], job['ncore']['avail']))
        print(alert)


def alert_exit(job):
    if job['exit_status'] not in ('0', None):
        alert = 'Alert: job stopped with non-zero exit code (%s).' % job['exit_status']
        print(alert)


def write_alerts(job):
    alerts = {'mem': alert_mem, 'walltime': alert_walltime, 'ncore': alert_ncore}
    for res in alerts.keys():
        if job[res]['usage'] is not None:
            alerts[res](job)
    if job['exit_status'] is not None:
        alert_exit(job)


def write_header():
    fstring = '%12s %13s %13s %6s %31s %13s %1s %s'
    print(fstring % ('resource', 'used', 'requested', 'usage', ' ', 'jobID', 'S', 'jobname'))
    print(fstring % ('--------', '----', '---------', '-----', ' ', '-----', '-', '-------'))


def demo_usage_bar():
    for i in range(10, 101, 10):
        print(usage_bar(i, show_rating=False))
        print(usage_bar(i))


def demo_myresources():
    write_header()
    for i in range(1, 5):
        job = new_job()
        job.update({
            'jobid': str(i + 100000),
            'jobname': 'my_super_job%s' % i,
            'state': 'C',
        })
        job['mem'].update({'avail': 20, 'used': i * 5})
        job['walltime'].update({'avail': 16, 'used': i * 4})
        job['ncore'].update({'avail': 4, 'used': i})

        job = calc_usage(job)
        ustring = usage_string(job)
        write_string(ustring)

        if not noalert:
            write_alerts(job)
        print('')


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
 -red:        bad - waisting resources
 -magenta:    danger - close to the limit
 -blue:       no rating
        """,
        formatter_class=RawDescriptionHelpFormatter,
    )
    parser.add_argument('jobid', help='show only resources for given jobID(s) (default: show all)', nargs='*')
    parser.add_argument('-a', '--noalert', dest='noalert', help='do not show alert messages', action='store_true')
    parser.add_argument('-f', '--infile', dest='infile', help="xml file (output of 'qstat -xt')")
    parser.add_argument('-c', '--nocolor', dest='nocolor', help='do not use colors in the output', action='store_true')
    parser.add_argument(
        '-s', '--state', dest='state',
        help='show only jobs with given state(s) as comma-separated list: "Q,H,R,E,C" (default: show all)')
    parser.add_argument('-d', '--demo', dest='demo', help='show demo output and exit', action='store_true')
    parser.add_argument('-v', '--version', dest='version', help='show version and exit', action='store_true')

    args = parser.parse_args()

    if args.version:
        print('version: %s' % VERSION)
        sys.exit()

    if args.jobid:
        for i in args.jobid:
            try:
                int(i)
            except ValueError:
                raise ValueError('%s is not a valid jobID' % i)

    global noalert
    if args.noalert:
        noalert = True

    global nocolor
    if args.nocolor:
        nocolor = True

    if args.demo:
        demo_myresources()
        sys.exit()

    if args.infile:
        try:
            tree = ET.parse(args.infile)
        except (IOError, ET.ParseError):
            print('Error parsing xml file: %s' % args.infile)
            sys.exit()
    else:
        xmlstring = run_cmd('qstat -xt')
        tree = ET.ElementTree(ET.fromstring(xmlstring))

    root = tree.getroot()
    if not root:
        sys.exit()

    write_header()

    for jobdata in root:
        job = parse_xml(jobdata)
        if args.jobid:
            if job['jobid'] not in args.jobid:
                continue
        if args.state:
            states = args.state.split(',')
            if job['state'] not in states:
                continue

        job = calc_usage(job)
        ustring = usage_string(job)
        write_string(ustring)

        if not noalert:
            write_alerts(job)

        print('')


if __name__ == '__main__':
    main()
    """
    suppress the following error when piping the output:
        close failed in file object destructor:
        sys.excepthook is missing
        lost sys.stderr
    """
    try:
        sys.stdout.close()
    except IOError:
        pass
    try:
        sys.stderr.close()
    except IOError:
        pass
    sys.exit()
