Description
===========

myresources calculates job resource usage for running or recently finished jobs.
It takes as input the output of the 'qstat' command, part of the TORQUE resource manager.
This script can be used to check if requested resources are/were used optimally.


Dependencies
============

* TORQUE resource manager
* Python 2.7


Install
=======

    git clone https://github.com/sisc-hpc/myresources
    cd myresources
    ./setup.py install
