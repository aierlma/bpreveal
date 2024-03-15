#!/usr/bin/env python3
"""This little utility takes the hdf5 files generated by interpretFlat.py and renders them as
numpy arrays that can be fed to the tfmodisco-lite suite.
"""

import argparse
import numpy as np
import h5py
from bpreveal import logUtils
from bpreveal.internal.constants import IMPORTANCE_T, ONEHOT_T


def flipAndSave(inpAr: np.ndarray[IMPORTANCE_T] | np.ndarray[ONEHOT_T],
                fname: str, dtype: np.dtype):
    """Save the datasets in the format expected by modiscolite.

    The hdf5 file contains scores in the format
    ``(num-regions x input-length x 4)``, but modiscolite requires
    ``(num-regions x 4 x input-length)``.

    :param inpAr: The data to save out
    :param fname: The file to save. If it ends with ``npz``, it will be saved compressed.
    :param dtype: The numpy data type to use for the stored data.
    """
    ar = np.array(inpAr, dtype=dtype)
    transAr = np.transpose(ar, [0, 2, 1])
    logUtils.info(f"Saving {fname}")
    if fname[-3:] == "npz":
        np.savez(fname, transAr)
    else:
        np.save(fname, transAr)


def getParser() -> argparse.ArgumentParser:
    """Generate the parser

    :return: an ArgumentParser, ready to have parse_args() called.
    """
    parser = argparse.ArgumentParser(
        description="A little utility that takes the hdf5-format files generated by "
                    "interpretFlat.py and saves them as numpy arrays suitable for "
                    "tfmodisco-lite.")
    parser.add_argument("--h5",
        help="The name of the hdf5-format file generated by interpretFlat.py")
    parser.add_argument("--seqs",
        help="The name of the .npy/.npz-format file containing the one-hot-encoded sequences. "
             "This is an output.")
    parser.add_argument("--scores",
        help="The name of the .npy/.npz-format file containing the hypothetical importance "
             "scores. This is an output.")
    parser.add_argument("--verbose", help="Display progress messages.", action="store_true")
    return parser


def main():
    """Runs the program"""
    args = getParser().parse_args()
    logUtils.setBooleanVerbosity(args.verbose)
    logUtils.info(f"Loading input file {args.h5}.")
    inFile = h5py.File(args.h5, "r")
    if args.seqs is not None:
        flipAndSave(inFile["input_seqs"], args.seqs, ONEHOT_T)
        logUtils.info("Saved sequences.")
    logUtils.info("Saving scores.")
    flipAndSave(inFile["hyp_scores"], args.scores, IMPORTANCE_T)
    logUtils.info("Done.")


if __name__ == "__main__":
    main()
# Copyright 2022, 2023, 2024 Charles McAnany. This file is part of BPReveal. BPReveal is free software: You can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 2 of the License, or (at your option) any later version. BPReveal is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details. You should have received a copy of the GNU General Public License along with BPReveal. If not, see <https://www.gnu.org/licenses/>.  # noqa
