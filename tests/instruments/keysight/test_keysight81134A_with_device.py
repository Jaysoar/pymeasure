#
# This file is part of the PyMeasure package.
#
# Copyright (c) 2013-2026 PyMeasure Developers
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
#
# UNPLUG EVERYTHING FROM THE 81134A OUTPUTS BEFORE STARTING THIS TEST
# (or terminate them with 50 Ohm), the outputs are switched on.
#
# Tested over USB with firmware 2.9.5:
# $ pytest -k 81134A --device-address "USB0::2391::16392::<serial>::0::INSTR"
# Test using GPIB:
# $ pytest -k 81134A --device-address "GPIB0::13::INSTR"
# Test using LAN:
# $ pytest -k 81134A --device-address "TCPIP0::<ip>::inst0::INSTR"

import pytest

from pymeasure.instruments.keysight.keysight81134A import Keysight81134A

CHANNELS = [1, 2]
OUTPUTS = [0, 1, 2]


@pytest.fixture(scope="module")
def keysight81134a(connected_device_address):
    instr = Keysight81134A(connected_device_address)
    instr.clear()
    yield instr
    instr.reset()
    instr.adapter.close()


@pytest.fixture
def generator(keysight81134a):
    keysight81134a.reset()
    keysight81134a.clear()
    assert keysight81134a.check_errors() == []
    yield keysight81134a
    assert keysight81134a.check_errors() == []


def test_id(generator):
    assert "8113" in generator.id


def test_reset_state(generator):
    assert generator.frequency == pytest.approx(15e6)
    assert generator.clock_source == "IMM"
    assert generator.outputs_enabled is True
    for ch in OUTPUTS:
        assert generator.channels[ch].output_enabled is False
    for ch in CHANNELS:
        assert generator.channels[ch].mode == "PULS"
        assert generator.channels[ch].divider == 1
        assert generator.channels[ch].polarity == "NORM"
    assert generator.trigger_output.source == "PER"


@pytest.mark.parametrize("value", [15e6, 123.456789e6, 1e9, 3.35e9])
def test_frequency(generator, value):
    generator.frequency = value
    assert generator.frequency == pytest.approx(value)
    assert generator.period == pytest.approx(1 / value)


def test_period(generator):
    generator.period = 750e-12
    assert generator.period == pytest.approx(750e-12)


@pytest.mark.parametrize("source", ["IDIR", "IMM"])
def test_clock_source(generator, source):
    generator.clock_source = source
    assert generator.clock_source == source


def test_measured_frequency(generator):
    generator.frequency = 1e9
    assert generator.measured_frequency == pytest.approx(1e9, rel=1e-3)
    assert generator.measured_period == pytest.approx(1e-9, rel=1e-3)


@pytest.mark.parametrize("ch", OUTPUTS)
def test_levels(generator, ch):
    output = generator.channels[ch]
    output.voltage_low = 0
    output.voltage_high = 1
    assert output.voltage_low == pytest.approx(0)
    assert output.voltage_high == pytest.approx(1)
    assert output.amplitude == pytest.approx(1)
    assert output.offset == pytest.approx(0.5)
    output.amplitude = 0.5
    output.offset = -0.25
    assert output.voltage_high == pytest.approx(0)
    assert output.voltage_low == pytest.approx(-0.5)
    output.termination_voltage = 1
    assert output.termination_voltage == pytest.approx(1)


def test_level_conflict_error(generator):
    generator.ch_1.voltage_low = 1
    generator.ch_1.voltage_high = 1.01
    errors = generator.check_errors()
    assert len(errors) == 1
    assert errors[0][0] == -221
    assert "amplitude of channel 1 is too small" in errors[0][1]


@pytest.mark.parametrize("ch", CHANNELS)
def test_mode(generator, ch):
    for mode in ["SQU", "DAT", "PULS"]:
        generator.channels[ch].mode = mode
        assert generator.channels[ch].mode == mode


@pytest.mark.parametrize("ch", CHANNELS)
def test_divider(generator, ch):
    generator.frequency = 1e9
    generator.channels[ch].divider = 64
    assert generator.channels[ch].divider == 64


def test_divider_below_minimum_frequency(generator):
    generator.frequency = 20e6
    generator.ch_2.divider = 2
    errors = generator.check_errors()
    assert len(errors) == 1
    assert errors[0][0] == -221


@pytest.mark.parametrize("ch", CHANNELS)
def test_timing(generator, ch):
    channel = generator.channels[ch]
    generator.frequency = 100e6
    channel.mode = "PULS"
    channel.delay = 500e-12
    assert channel.delay == pytest.approx(500e-12)
    channel.deskew = -155e-12
    assert channel.deskew == pytest.approx(-155e-12)
    channel.width = 2e-9
    assert channel.width == pytest.approx(2e-9)
    channel.duty_cycle = 30
    assert channel.duty_cycle == pytest.approx(30)
    assert channel.width == pytest.approx(3e-9)
    channel.phase = 90
    assert channel.phase == pytest.approx(90)
    assert channel.delay == pytest.approx(2.5e-9)
    channel.polarity = "COMP"
    assert channel.polarity == "COMP"


@pytest.mark.parametrize("ch", CHANNELS)
def test_level_limits_enabled(generator, ch):
    assert generator.channels[ch].level_limits_enabled is False
    generator.channels[ch].level_limits_enabled = True
    assert generator.channels[ch].level_limits_enabled is True


@pytest.mark.parametrize("ch", OUTPUTS)
def test_output_enabled(generator, ch):
    generator.channels[ch].output_enabled = True
    try:
        assert generator.channels[ch].output_enabled is True
    finally:
        generator.channels[ch].output_enabled = False
    assert generator.channels[ch].output_enabled is False


@pytest.mark.parametrize("ch", CHANNELS)
def test_positive_negative_output_enabled(generator, ch):
    channel = generator.channels[ch]
    try:
        channel.positive_output_enabled = True
        assert channel.positive_output_enabled is True
        assert channel.negative_output_enabled is False
        assert channel.output_enabled is True
        channel.negative_output_enabled = True
        assert channel.negative_output_enabled is True
    finally:
        channel.output_enabled = False
    assert channel.positive_output_enabled is False
    assert channel.negative_output_enabled is False


def test_outputs_enabled(generator):
    generator.outputs_enabled = False
    assert generator.outputs_enabled is False
    generator.outputs_enabled = True
    assert generator.outputs_enabled is True


def test_trigger_output(generator):
    generator.trigger_output.divider = 1000
    assert generator.trigger_output.divider == 1000
    generator.trigger_output.source = "BITS"
    assert generator.trigger_output.source == "BITS"


def test_display_enabled(generator):
    generator.display_enabled = False
    assert generator.display_enabled is False
    generator.preset()
    assert generator.display_enabled is False
    generator.reset()
    assert generator.display_enabled is True
