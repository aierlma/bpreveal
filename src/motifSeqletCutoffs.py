#!/usr/bin/env python3
"""Reads in a modisco h5 and prepares to scan for seqlets.

In order to see where seqlets are found on the genome, we need to scan the cwms
derived from modiscolite.
The first step of this process is to look at the seqlets that MoDISco called for
each pattern it identified, and establish cutoff values.
This program does that.
It reads in a modiscolite hdf5 file and calculates cutoff values of seqlet
similarity for what constitutes a hit.
It requires one JSON-format input, and generates two outputs: First, it
generates a tsv file containing all of the seqlets in the modisco h5 with some
helpful metadata, like how well they match the pattern they are identified
as being a part of.
Second, it produces a JSON-format file that will be needed
by :py:mod:`motifScan<bpreveal.motifScan>`.

BNF
---

.. highlight:: none

.. literalinclude:: ../../doc/bnf/motifSeqletCutoffs.bnf


Parameter Notes
---------------

seqlets-tsv
    (Optional) The name of the file that should
    be written containing the scanned seqlets.
    See :py:mod:`motifAddQuantiles<bpreveal.motifAddQuantiles` for the structure of this file.

modisco-h5
    This is the hdf5 file generated by modisco.

modisco-contrib-h5
    (Optional) The contribution score file generated by
    :py:mod:`interpretFlat<bpreveal.interpretFlat>`, which is necessary to recover the genomic
    coordinates of the seqlets, since the Modisco hdf5 doesn't contain that
    info. The contribution scores are *not* extracted from this file, just
    coordinates.
    *THIS DOES NOT CURRENTLY WORK, SINCE SEQLET INDEXES ARE RESET
    BY MODISCO*

There are two ways of specifying patterns,
either by giving each
pattern and metacluster pair individually, or by listing multiple
patterns under a single metacluster.
The short-names, if provided, will be used to populate the name field in
the generated tsv.
You could use this to give a particular pattern the name of its binding
protein.

seq-match-quantile
    TODO MELANIE Document

contrib-match-quantile
    TODO MELANIE Document

contrib-magnitude-quantile
    TODO MELANIE Document

trim-threshold
    TODO MELANIE Document

trim-padding
    TODO MELANIE Document

background-probs
    Gives the genetic content of your genome.
    For example, if you had a genome with 60 percent GC content, this would
    be [0.2, 0.3, 0.3, 0.2].
    The order of the bases is A, C, G, and T.

patterns
    May be either a pattern spec (see below) or the string "all", in which case
    every pattern will be used to scan.

metacluster-name
    Will be something like ``pos_patterns`` or ``neg_patterns``.

pattern-name
    Will be something like ``pattern_0`` or ``pattern_6``.
    Note that this is the name in the modisco output file, not the actual name
    of the motif.

short-name
    (Optional) If provided, this gives a more human-readable name to a
    particular pattern. This is just used to annotate the output, it has no
    effect on the actual scanning or quantiling operation.

pattern-names, short-names
    Instead of providing a pattern-spec for each pattern, you may include a
    list of patterns within one metacluster. These are lists of strings.

Output Specification
--------------------

See :py:mod:`motifAddQuantiles<bpreveal.motifAddQuantiles>` for a description of the tsv file,
and :py:mod:`motifScan<bpreveal.motifScan>` for a description of the generated JSON.


API
---

"""
from bpreveal import logUtils
from bpreveal import motifUtils
import json


def main(config):
    """Determine the cutoffs based on modisco outputs.

    :param config: A JSON object based on the motifSeqletCutoffs specification.
    """
    logUtils.setVerbosity(config["verbosity"])
    logUtils.info("Starting seqlet analysis")
    # First, make the pattern objects.
    tsvFname = None
    if "seqlets-tsv" in config:
        tsvFname = config["seqlets-tsv"]
    scanPatternDict = motifUtils.seqletCutoffs(config["modisco-h5"],
                                               config["modisco-contrib-h5"],
                                               config["patterns"],
                                               config["seq-match-quantile"],
                                               config["contrib-match-quantile"],
                                               config["contrib-magnitude-quantile"],
                                               config["trim-threshold"],
                                               config["trim-padding"],
                                               config["background-probs"],
                                               tsvFname
                                               )
    logUtils.info("Analysis complete.")
    if "quantile-json" in config:
        logUtils.info("Saving pattern json.")
        with open(config["quantile-json"], "w", encoding='utf-8') as fp:
            json.dump(scanPatternDict, fp, indent=4)


if __name__ == "__main__":
    import sys
    with open(sys.argv[1], "r", encoding='utf-8') as configFp:
        configJson = json.load(configFp)
    import bpreveal.schema
    bpreveal.schema.motifSeqletCutoffs.validate(configJson)
    main(configJson)
