#!/usr/bin/env python3
import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "1"
import json
import bpreveal.utils as utils
import h5py
from tensorflow import keras
from tensorflow.keras.backend import int_shape
from keras.models import load_model
import bpreveal.generators as generators
import bpreveal.losses as losses
from bpreveal.callbacks import getCallbacks
import bpreveal.models as models
import logging
import tensorflow as tf


def trainModel(model, inputLength, outputLength, trainBatchGen, valBatchGen, epochs, earlyStop,
               outputPrefix, plateauPatience, heads, tensorboardDir=None):
    callbacks = getCallbacks(earlyStop, outputPrefix, plateauPatience, heads)
    if (tensorboardDir is not None):
        logging.info("Including logging.")
        from callbacks import tensorboardCallback
        callbacks.append(tensorboardCallback(tensorboardDir))
    history = model.fit(trainBatchGen, epochs=epochs, validation_data=valBatchGen,
                        callbacks=callbacks, max_queue_size=1000)
    # Turn the learning rates into native python float values so they can be saved to json.
    history.history['lr'] = [float(x) for x in history.history['lr']]
    lossCallback = callbacks[3]
    history.history["counts-loss-weight"] = lossCallback.λHistory
    return history


def main(config):
    utils.setVerbosity(config["verbosity"])
    utils.setMemoryGrowth()
    inputLength = config["settings"]["architecture"]["input-length"]
    outputLength = config["settings"]["architecture"]["output-length"]
    numHeads = len(config["heads"])
    regressionModel = load_model(
        config["settings"]["transformation-model"]["transformation-model-file"],
        custom_objects={'multinomialNll': losses.multinomialNll,
                        'reweightableMse': losses.dummyMse})
    regressionModel.trainable = False
    logging.debug("Loaded regression model.")
    combinedModel, residualModel, transformationModel = models.combinedModel(
        inputLength, outputLength,
        config["settings"]["architecture"]["filters"],
        config["settings"]["architecture"]["layers"],
        config["settings"]["architecture"]["input-filter-width"],
        config["settings"]["architecture"]["output-filter-width"],
        config["heads"], regressionModel)
    logging.debug("Created combined model.")
    profileLosses = [losses.multinomialNll] * numHeads
    countsLosses = []
    profileWeights = []
    countsWeights = []
    for head in config['heads']:
        profileWeights.append(head["profile-loss-weight"])
        # For adaptive loss weights, make the counts loss a keras variable so I
        # can update it during training.
        λInit = head["counts-loss-weight"] if "counts-loss-weight" in head else 1
        λ = tf.Variable(λInit, dtype=tf.float32)
        # Store the (keras) variable with the loss weight in the head dictionary.
        # We'll need it in the callbacks, and this is a reasonable place to store it.
        head["INTERNAL_λ-variable"] = λ
        countsWeights.append(1)
        countsLosses.append(losses.weightedMse(λ))

    residualModel.compile(
        optimizer=keras.optimizers.Adam(learning_rate=config["settings"]["learning-rate"]),
        jit_compile=True,
        loss=profileLosses + countsLosses,
        loss_weights=profileWeights + countsWeights)  # + is list concatenation, not addition!

    combinedModel.compile(
        optimizer=keras.optimizers.Adam(learning_rate=config["settings"]["learning-rate"]),
        jit_compile=True,
        loss=profileLosses + countsLosses,
        loss_weights=profileWeights + countsWeights)  # + is list concatenation, not addition!
    logging.debug("Models compiled.")
    trainH5 = h5py.File(config["train-data"], "r")
    valH5 = h5py.File(config["val-data"], "r")

    trainGenerator = generators.H5BatchGenerator(config["heads"], trainH5,
                                                 inputLength, outputLength,
                                                 config["settings"]["max-jitter"],
                                                 config["settings"]["batch-size"])
    valGenerator = generators.H5BatchGenerator(config["heads"], valH5,
                                               inputLength, outputLength,
                                               config["settings"]["max-jitter"],
                                               config["settings"]["batch-size"])
    logging.info("Generators initialized. Training.")

    tensorboardDir = None
    if ("tensorboard-log-dir" in config):
        tensorboardDir = config["tensorboard-log-dir"]

    history = trainModel(combinedModel, inputLength, outputLength, trainGenerator,
                         valGenerator, config["settings"]["epochs"],
                         config["settings"]["early-stopping-patience"],
                         config["settings"]["output-prefix"],
                         config["settings"]["learning-rate-plateau-patience"],
                         config["heads"],
                         tensorboardDir)
    combinedModel.save(config["settings"]["output-prefix"] + "_combined" + ".model")
    residualModel.save(config["settings"]["output-prefix"] + "_residual" + ".model")
    with open("{0:s}.history.json".format(config["settings"]["output-prefix"]), "w") as fp:
        json.dump(history.history, fp, ensure_ascii=False, indent=4)


if (__name__ == "__main__"):
    import sys
    with open(sys.argv[1], "r") as configFp:
        config = json.load(configFp)
    main(config)
