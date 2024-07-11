"""Custom layers that are needed for the various models."""
from collections.abc import Callable
from keras.layers import Conv1D, Reshape, Layer  # type: ignore
from keras import ops
from bpreveal import logUtils


def linearRegression(**kwargs) -> Callable:
    """A linear regression layer that's compatible with shap.

    .. highlight:: none

    Implements the following formula::

        out = input * slope + offset

    where slope and offset are two (scalar) parameters.

    .. highlight:: python

    Note that although this is a function, it behaves like a normal Keras layer class
    and you create it like this::

        regression = bpreveal.layers.LinearRegression(name="oct4_regression")(regressionInput)


    :param kwargs: Passed to the keras Layer initializer.
    :return: A function that you can call with a Keras layer as input, like a normal
        Keras Layer class.
    :rtype: A function taking a tensor and returning a tensor.
    """
    def layer(inputs):  # noqa
        regName = kwargs.get("name", "linReg")
        # Make the layer a (none, length, 1) shape tensor. # noqa
        reshaped = Reshape((-1, 1), name=regName + "_r1")(inputs)
        # A convolution is a multiplication if you think about it wrong enough.
        # x ★ y = x * y if y ∈ R¹
        # and the Conv1D layer includes bias, so that's where the +b comes from.
        convolved = Conv1D(filters=1,
                           kernel_size=1,
                           kernel_initializer="Ones",
                           name=regName + "_conv")(reshaped)
        # Restore the original shape.
        unreshaped = Reshape(inputs.shape[1:], name=regName + "_r2")(convolved)
        logUtils.debug(f"Built regression layer '{regName}' with output shape {inputs.shape[1:]}.")
        return unreshaped
    return layer


class CountsLogSumExp(Layer):
    """A simple layer that wraps keras.ops.logaddexp."""

    def call(self, inp1, inp2):  # noqa
        """return log(exp(inp1) + exp(inp2))."""
        return ops.logaddexp(inp1, inp2)

# Copyright 2022, 2023, 2024 Charles McAnany. This file is part of BPReveal. BPReveal is free software: You can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 2 of the License, or (at your option) any later version. BPReveal is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details. You should have received a copy of the GNU General Public License along with BPReveal. If not, see <https://www.gnu.org/licenses/>.  # noqa
