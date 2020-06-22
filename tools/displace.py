#!/usr/bin/env python
#
# displace.py
#
# Simple script to generate input files of given displacement patterns.
# Currently, VASP, Quantum-ESPRESSO, and xTAPP are supported.
#
# Copyright (c) 2014 Terumasa Tadano
#
# This file is distributed under the terms of the MIT license.
# Please see the file 'LICENCE.txt' in the root directory
# or http://opensource.org/licenses/mit-license.php for information.
#

"""
Input file generator for displaced configurations.
"""

from __future__ import print_function
import optparse
import numpy as np
import interface.VASP as vasp
import interface.QE as qe
import interface.xTAPP as xtapp
import interface.OpenMX as openmx
import interface.LAMMPS as lammps

usage = "usage: %prog [options] file.pattern_HARMONIC file.pattern_ANHARM3 ... \n \
      file.pattern_* can be generated by 'alm' with MODE = suggest."
parser = optparse.OptionParser(usage=usage)
parser.add_option('--mag',
                  help="Magnitude of displacement in units of \
                        Angstrom (default: 0.02)")

parser.add_option('--prefix',
                  help="Prefix of the files to be created. ")

parser.add_option('--QE',
                  metavar='orig.pw.in',
                  help="Quantum-ESPRESSO input file with equilibrium atomic positions (default: None)")
parser.add_option('--VASP',
                  metavar='orig.POSCAR',
                  help="VASP POSCAR file with equilibrium atomic \
                        positions (default: None)")
parser.add_option('--xTAPP',
                  metavar='orig.cg',
                  help="xTAPP CG file with equilibrium atomic \
                        positions (default: None)")
parser.add_option('--LAMMPS',
                  metavar='orig.lammps',
                  help="LAMMPS structure file with equilibrium atomic positions (default: None)")

parser.add_option('--OpenMX',
                  metavar='orig.dat',
                  help="dat file with equilibrium atomic \
                        positions (default: None)")


def parse_displacement_patterns(files_in):

    pattern = []

    for file in files_in:
        pattern_tmp = []

        f = open(file, 'r')
        tmp, basis = f.readline().rstrip().split(':')
        if basis == 'F':
            print("Warning: DBASIS must be 'C'")
            exit(1)

        while True:
            line = f.readline()

            if not line:
                break

            line_split_by_colon = line.rstrip().split(':')
            is_entry = len(line_split_by_colon) == 2

            if is_entry:
                pattern_set = []
                natom_move = int(line_split_by_colon[1])
                for i in range(natom_move):
                    disp = []
                    line = f.readline()
                    line_split = line.rstrip().split()
                    disp.append(int(line_split[0]))
                    for j in range(3):
                        disp.append(float(line_split[j + 1]))

                    pattern_set.append(disp)
                pattern_tmp.append(pattern_set)

        print("File %s containts %i displacement patterns"
              % (file, len(pattern_tmp)))

        for entry in pattern_tmp:
            if entry not in pattern:
                pattern.append(entry)

        f.close()

        print("")
    print("Number of unique displacement patterns = %d" % len(pattern))

    return pattern


def char_xyz(entry):

    if entry % 3 == 0:
        return 'x'
    elif entry % 3 == 1:
        return 'y'
    elif entry % 3 == 2:
        return 'z'


def gen_displacement(counter_in, pattern, disp_mag, nat, invlavec):

    poscar_header = "Disp. Num. %i" % counter_in
    poscar_header += " ( %f Angstrom" % disp_mag

    disp = np.zeros((nat, 3))

    for displace in pattern:
        atom = displace[0] - 1

        poscar_header += ", %i : " % displace[0]

        str_direction = ""

        for i in range(3):
            if abs(displace[i + 1]) > 1.0e-10:
                if displace[i + 1] > 0.0:
                    str_direction += "+" + char_xyz(i)
                else:
                    str_direction += "-" + char_xyz(i)

            disp[atom][i] += displace[i + 1] * disp_mag

        poscar_header += str_direction

    poscar_header += ")"

    if invlavec is not None:
        for i in range(nat):
            disp[i] = np.dot(disp[i], invlavec.T)

    return poscar_header, disp


def get_number_of_zerofill(npattern):

    nzero = 1

    while True:
        npattern //= 10

        if npattern == 0:
            break

        nzero += 1

    return nzero


if __name__ == '__main__':

    options, args = parser.parse_args()
    file_pattern = args[0:]

    print("*****************************************************************")
    print("             displace.py -- Input file generator                 ")
    print("*****************************************************************")
    print("")

    if len(file_pattern) == 0:
        print("Usage: displace.py [options] file1.pattern_HARMONIC\
 file2.pattern_ANHARM3 ...")
        print("file.pattern_* can be generated by 'alm' with MODE = suggest.")
        print("")
        print("For details of available options, \
 please type\n$ python displace.py -h")
        exit(1)

    conditions = [options.VASP is None,
                  options.QE is None,
                  options.xTAPP is None,
                  options.LAMMPS is None,
                  options.OpenMX is None]

    if conditions.count(True) == len(conditions):
        print(
            "Error : Either --VASP, --QE, --xTAPP, --LAMMPS, --OpenMX option must be given.")
        exit(1)

    elif len(conditions) - conditions.count(True) > 1:
        print("Error : --VASP, --QE, --xTAPP, --LAMMPS, and --OpenMX cannot be given simultaneously.")
        exit(1)

    elif options.VASP:
        code = "VASP"
        print("--VASP option is given: Generate POSCAR files for VASP")
        print("")

    elif options.QE:
        code = "QE"
        print("--QE option is given: Generate input files for Quantum-ESPRESSO.")
        print("")

    elif options.xTAPP:
        code = "xTAPP"
        print("--xTAPP option is given: Generate input files for xTAPP.")
        print("")

    elif options.LAMMPS:
        code = "LAMMPS"
        print("--LAMMPS option is given: Generate input files for LAMMPS.")
        print("")

    elif options.OpenMX:
        code = "OpenMX"
        print("--OpenMX option is given: Generate dat files for OpenMX")
        print("")

    # Assign the magnitude of displacements
    if options.mag is None:
        options.mag = "0.02"
        disp_length = 0.02
        print("--mag option not given. Substituted by the default (0.02 Angstrom)")
        print("")

    else:
        disp_length = float(options.mag)

    if options.prefix is None:
        prefix = "disp"
        print("--prefix option not given. Substituted by the default (\"disp\"). ")
        print("")
    else:
        prefix = options.prefix

    print("-----------------------------------------------------------------")
    print("")

    if code == "VASP":
        str_outfiles = "%s{counter}.POSCAR" % prefix
        file_original = options.VASP

    elif code == "QE":
        str_outfiles = "%s{counter}.pw.in" % prefix
        file_original = options.QE
        suffix = "pw.in"

    elif code == "xTAPP":
        str_outfiles = "%s{counter}.cg" % prefix
        file_original = options.xTAPP

    elif code == "LAMMPS":
        str_outfiles = "%s{counter}.lammps" % prefix
        file_original = options.LAMMPS

    elif code == "OpenMX":
        str_outfiles = "%s{counter}.dat" % prefix
        file_original = options.OpenMX

    # Read the original file
    if code == "VASP":
        aa, aa_inv, elems, nats, x_frac = vasp.read_POSCAR(file_original)
        nat = np.sum(nats)

    elif code == "QE":
        list_namelist, list_ATOMIC_SPECIES, \
            list_K_POINTS, list_CELL_PARAMETERS, list_OCCUPATIONS, \
            nat, lavec, kd_symbol, x_frac, aa_inv = qe.read_original_QE(
                file_original)

    elif code == "xTAPP":
        str_header, nat, nkd, aa, aa_inv, x_frac, kd \
            = xtapp.read_CG(file_original)
        suffix = "cg"

    elif code == "LAMMPS":
        common_settings, nat, x_cart, kd, charge \
            = lammps.read_lammps_structure(file_original)
        aa_inv = None

    elif code == "OpenMX":
        aa, aa_inv, nat, x_frac = openmx.read_OpenMX_input(file_original)

    print("Original file                  : %s" % file_original)
    print("Output file format             : %s" % str_outfiles)
    print("Magnitude of displacements     : %s Angstrom" % disp_length)
    print("Number of atoms                : %i" % nat)
    print("")

    disp_pattern = parse_displacement_patterns(args[:])
    nzerofills = get_number_of_zerofill(len(disp_pattern))
    counter = 0

    for pattern in disp_pattern:
        counter += 1
        header, disp = gen_displacement(counter, pattern, disp_length,
                                        nat, aa_inv)

        if code == "VASP":
            vasp.write_POSCAR(prefix, counter, header, nzerofills,
                              aa, elems, nats, disp, x_frac)

        elif code == "QE":
            qe.generate_QE_input(prefix, suffix, counter, nzerofills, list_namelist,
                                 list_ATOMIC_SPECIES, list_K_POINTS,
                                 list_CELL_PARAMETERS, list_OCCUPATIONS,
                                 nat, kd_symbol, x_frac, disp)

        elif code == "xTAPP":
            nsym = 1
            symop = []
            symop.append([1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0])
            denom_tran = 1
            has_inv = 0

            xtapp.gen_CG(prefix, suffix, counter, nzerofills, str_header, nat, kd,
                         x_frac, disp, nsym, symop, denom_tran, has_inv)

        elif code == "LAMMPS":
            lammps.write_lammps_structure(prefix, counter, header, nzerofills,
                                          common_settings, nat, kd, x_cart, disp, charge)

        elif code == "OpenMX":
            openmx.write_OpenMX_input(
                prefix, counter,  nzerofills, disp, aa, file_original)

    print("")
    print("All input files are created.")
