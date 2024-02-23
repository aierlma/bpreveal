#!/usr/bin/env python3
"""A script to make predictions using a list of sequences.

This program streams input from disk and writes output as it calculates, so
it can run with very little memory even for extremely large prediction tasks.


BNF
---

.. highlight:: none

.. literalinclude:: ../../doc/bnf/makePredictionsFasta.bnf


Parameter Notes
---------------

heads
    Gives the number of output heads for your model.
    You don't need to tell this program how many tasks there are for each
    head, since it just blindly sticks whatever the model outputs into the
    hdf5 file.

output-h5
    The name of the output file that will contain the predictions.

batch-size
    How many samples should be run simultaneously? I recommend 64 or so.

model-file
    The name of the Keras model file on disk.

input-length, output-length
    The input and output lengths of your model.

fasta-file
    A file containing the sequences for which you'd like predictions. Each sequence in
    this bed file must be ``input-length`` long.

num-threads
    (Optional) How many parallel predictors should be run? Unless you're really taxed
    for performance, leave this at 1.

bed-file, genome
    These are optional. If provided, then the output hdf5 will contain ``chrom_names``,
    ``chrom_sizes``, ``coords_chrom``, ``coords_start``, and ``coords_end`` datasets,
    in addition to the descriptions dataset. This way, you can make predictions from a
    fasta but then easily convert it to a bigwig.

Output Specification
--------------------
This program will produce an hdf5-format file containing the predicted values.
It is organized as follows:

descriptions
    A list of strings of length (numRegions,).
    Each string corresponds to one description line (i.e., a line starting
    with ``>``).

head_0, head_1, head_2, ...
    You get a subgroup for each output head of the model. The subgroups are named
    ``head_N``, where N is 0, 1, 2, etc.
    Each head contains:

    logcounts
        A vector of shape (numRegions,) that gives
        the logcounts value for each region.

    logits
        The array of logit values for each track for
        each region.
        The shape is (numRegions x outputWidth x numTasks).
        Don't forget that you must calculate the softmax on the whole
        set of logits, not on each task's logits independently.
        (Use :py:func:`bpreveal.utils.logitsToProfile` to do this.)

chrom_names, chrom_sizes, coords_chrom, coords_start, coords_stop
    If you provided ``bed-file`` and ``genome`` entries in your json,
    these datasets will be populated. They mirror their meaning in the
    output from :py:mod:`makePredictionsBed<bpreveal.makePredictionsBed>`.

API
---

"""


import json
from bpreveal import utils
import bpreveal.internal.disableTensorflowLogging  # pylint: disable=unused-import # noqa
from bpreveal import logUtils
from bpreveal.logUtils import wrapTqdm
from bpreveal.internal import predictUtils


def main(config):
    """Run the predictions.

    :param config: is taken straight from the json specification.
    """
    logUtils.setVerbosity(config["verbosity"])
    fastaFname = config["fasta-file"]
    batchSize = config["settings"]["batch-size"]
    modelFname = config["settings"]["architecture"]["model-file"]
    numHeads = config["settings"]["heads"]
    logUtils.debug("Opening output hdf5 file.")
    outFname = config["settings"]["output-h5"]

    # Before we can build the output dataset in the hdf5 file, we need to
    # know how many fasta regions we will be asked to predict.
    fastaReader = predictUtils.FastaReader(fastaFname)
    if "num-threads" in config:
        batcher = utils.ThreadedBatchPredictor(modelFname, batchSize,
                                               numThreads=config["num-threads"])
    else:
        batcher = utils.BatchPredictor(modelFname, batchSize)
    if "coordinates" in config:
        writer = predictUtils.H5Writer(outFname, numHeads, fastaReader.numPredictions,
                                       config["coordinates"]["bed-file"],
                                       config["coordinates"]["genome"])
    else:
        writer = predictUtils.H5Writer(outFname, numHeads, fastaReader.numPredictions)
    logUtils.info("Entering prediction loop.")
    # Now we just iterate over the fasta file and submit to our batcher.
    with batcher:
        pbar = wrapTqdm(fastaReader.numPredictions)
        for _ in range(fastaReader.numPredictions):
            batcher.submitString(fastaReader.curSequence, fastaReader.curLabel)
            fastaReader.pop()
            while batcher.outputReady():
                # We've just run a batch. Write it out.
                ret = batcher.getOutput()
                pbar.update()
                writer.addEntry(ret)
        # Done with the main loop, clean up the batcher.
        logUtils.debug("Done with main loop.")
        while not batcher.empty():
            # We've just run a batch. Write it out.
            ret = batcher.getOutput()
            pbar.update()
            writer.addEntry(ret)
        writer.close()


if __name__ == "__main__":
    import sys
    with open(sys.argv[1], "r") as configFp:
        configJson = json.load(configFp)
    import bpreveal.schema
    bpreveal.schema.makePredictionsFasta.validate(configJson)
    main(configJson)
