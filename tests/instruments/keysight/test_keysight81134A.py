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

import pytest

from pymeasure.instruments.keysight.keysight81134A import Keysight81134A
from pymeasure.test import expected_protocol


def test_init():
    with expected_protocol(Keysight81134A, []):
        pass


def test_id():
    with expected_protocol(
        Keysight81134A,
        [("*IDN?", "Agilent Technologies, 81134A, DE00000001, Ver 2.9.5")],
    ) as inst:
        assert inst.id == "Agilent Technologies, 81134A, DE00000001, Ver 2.9.5"


@pytest.mark.parametrize(
    "reply, error",
    [
        ("0", [0, "No error"]),
        ('+0,"No error"', [0, "No error"]),
        (
            "-221:Settings conflict:amplitude of channel 1 is too small",
            [-221, "Settings conflict:amplitude of channel 1 is too small"],
        ),
        ('-222,"Data out of range"', [-222, "Data out of range"]),
    ],
)
def test_next_error(reply, error):
    with expected_protocol(Keysight81134A, [("SYST:ERR?", reply)]) as inst:
        assert inst.next_error == error


def test_check_errors():
    with expected_protocol(
        Keysight81134A,
        [("SYST:ERR?", "-221:Settings conflict:pulsewidth of channel 2 is too small"),
         ("SYST:ERR?", "0")],
    ) as inst:
        assert inst.check_errors() == [
            [-221, "Settings conflict:pulsewidth of channel 2 is too small"]
        ]


@pytest.mark.parametrize("value", [15e6, 123456789, 3.35e9])
def test_frequency(value):
    with expected_protocol(
        Keysight81134A,
        [(f"FREQ {value:.10g}", None), ("FREQ?", f"{value:+.8E}")],
    ) as inst:
        inst.frequency = value
        assert inst.frequency == value


@pytest.mark.parametrize("value", [14.9e6, 3.36e9])
def test_frequency_out_of_range(value):
    with expected_protocol(Keysight81134A, []) as inst, pytest.raises(ValueError):
        inst.frequency = value


def test_period():
    with expected_protocol(
        Keysight81134A,
        [("PER 7.5e-10", None), ("PER?", "+7.50000000E-10")],
    ) as inst:
        inst.period = 750e-12
        assert inst.period == pytest.approx(750e-12)


def test_period_out_of_range():
    with expected_protocol(Keysight81134A, []) as inst, pytest.raises(ValueError):
        inst.period = 100e-9


@pytest.mark.parametrize("source", ["IMM", "EXT", "REF", "IDIR", "EDIR"])
def test_clock_source(source):
    with expected_protocol(
        Keysight81134A,
        [(f"TRIG:SOUR {source}", None), ("TRIG:SOUR?", source)],
    ) as inst:
        inst.clock_source = source
        assert inst.clock_source == source


def test_measured_frequency():
    with expected_protocol(Keysight81134A, [("MEAS:FREQ?", "+9.99999870E+08")]) as inst:
        assert inst.measured_frequency == pytest.approx(999999870)


def test_measured_period():
    with expected_protocol(Keysight81134A, [("MEAS:PER?", "+1.00000013E-09")]) as inst:
        assert inst.measured_period == pytest.approx(1.00000013e-9)


@pytest.mark.parametrize("reply, value", [("1", True), ("0", False), ("ON", True),
                                          ("OFF", False)])
def test_outputs_enabled(reply, value):
    with expected_protocol(
        Keysight81134A,
        [(f"OUTP:CENT {value:d}", None), ("OUTP:CENT?", reply)],
    ) as inst:
        inst.outputs_enabled = value
        assert inst.outputs_enabled is value


def test_display_enabled():
    with expected_protocol(
        Keysight81134A,
        [("DISP 0", None), ("DISP?", "0")],
    ) as inst:
        inst.display_enabled = False
        assert inst.display_enabled is False


def test_preset():
    with expected_protocol(Keysight81134A, [("SYST:PRES", None)]) as inst:
        inst.preset()


def test_save_recall_state():
    with expected_protocol(
        Keysight81134A,
        [("*SAV 1", None), ("*RCL 0", None), ("*RCL 9", None)],
    ) as inst:
        inst.save_state(1)
        inst.recall_state(0)
        inst.recall_state(9)


@pytest.mark.parametrize("method, location", [("save_state", 0), ("save_state", 10),
                                              ("recall_state", -1), ("recall_state", 10),
                                              ("recall_state", 1.4)])
def test_state_invalid_location(method, location):
    with expected_protocol(Keysight81134A, []) as inst, pytest.raises(ValueError):
        getattr(inst, method)(location)


@pytest.mark.parametrize("ch", [0, 1, 2])
@pytest.mark.parametrize("reply, value", [("1", True), ("0", False), ("ON", True),
                                          ("OFF", False)])
def test_output_enabled(ch, reply, value):
    with expected_protocol(
        Keysight81134A,
        [(f"OUTP{ch} {value:d}", None), (f"OUTP{ch}?", reply)],
    ) as inst:
        inst.channels[ch].output_enabled = value
        assert inst.channels[ch].output_enabled is value


@pytest.mark.parametrize(
    "prop, command, value",
    [
        ("amplitude", "VOLT", 2),
        ("amplitude", "VOLT", 0.05),
        ("offset", "VOLT{ch}:OFFS", -1.975),
        ("offset", "VOLT{ch}:OFFS", 2.975),
        ("voltage_high", "VOLT{ch}:HIGH", 3),
        ("voltage_high", "VOLT{ch}:HIGH", -1.95),
        ("voltage_low", "VOLT{ch}:LOW", -2),
        ("voltage_low", "VOLT{ch}:LOW", 2.95),
        ("termination_voltage", "VOLT{ch}:TERM", -2),
        ("termination_voltage", "VOLT{ch}:TERM", 3),
    ],
)
@pytest.mark.parametrize("ch", [0, 1, 2])
def test_levels(ch, prop, command, value):
    command = command.format(ch=ch) if "{ch}" in command else f"{command}{ch}"
    with expected_protocol(
        Keysight81134A,
        [(f"{command} {value:g}", None), (f"{command}?", f"{value:+.8E}")],
    ) as inst:
        setattr(inst.channels[ch], prop, value)
        assert getattr(inst.channels[ch], prop) == value


@pytest.mark.parametrize(
    "prop, value",
    [
        ("amplitude", 0.04),
        ("amplitude", 2.1),
        ("offset", -2),
        ("offset", 3),
        ("voltage_high", -2),
        ("voltage_high", 3.1),
        ("voltage_low", -2.1),
        ("voltage_low", 3),
        ("termination_voltage", -2.1),
        ("termination_voltage", 3.1),
    ],
)
@pytest.mark.parametrize("ch", [0, 1, 2])
def test_levels_out_of_range(ch, prop, value):
    with expected_protocol(Keysight81134A, []) as inst, pytest.raises(ValueError):
        setattr(inst.channels[ch], prop, value)


@pytest.mark.parametrize("prop, command", [("positive_output_enabled", "POS"),
                                           ("negative_output_enabled", "NEG")])
def test_positive_negative_output_enabled(prop, command):
    with expected_protocol(
        Keysight81134A,
        [(f"OUTP2:{command} 1", None), (f"OUTP2:{command}?", "1")],
    ) as inst:
        setattr(inst.ch_2, prop, True)
        assert getattr(inst.ch_2, prop) is True


@pytest.mark.parametrize("mode, reply", [("SQU", "SQUAR"), ("PULS", "PULSE"), ("DAT", "DATA")])
def test_mode(mode, reply):
    with expected_protocol(
        Keysight81134A,
        [(f"FUNC:MOD1 {mode}", None), ("FUNC:MOD1?", reply)],
    ) as inst:
        inst.ch_1.mode = mode
        assert inst.ch_1.mode == mode


def test_mode_prbs_reply():
    with expected_protocol(Keysight81134A, [("FUNC:MOD2?", "PRBS,23")]) as inst:
        assert inst.ch_2.mode == "PRBS,23"


@pytest.mark.parametrize("value", [1, 2, 128])
def test_channel_divider(value):
    with expected_protocol(
        Keysight81134A,
        [(f"OUTP2:DIV {value}", None), ("OUTP2:DIV?", f"{value}")],
    ) as inst:
        inst.ch_2.divider = value
        assert inst.ch_2.divider == value


@pytest.mark.parametrize("value", [0, 3, 256])
def test_channel_divider_invalid(value):
    with expected_protocol(Keysight81134A, []) as inst, pytest.raises(ValueError):
        inst.ch_1.divider = value


@pytest.mark.parametrize("value", [1, 3, 2**31 - 1])
def test_trigger_output_divider(value):
    with expected_protocol(
        Keysight81134A,
        [(f"OUTP0:DIV {value}", None), ("OUTP0:DIV?", f"{value}")],
    ) as inst:
        inst.trigger_output.divider = value
        assert inst.trigger_output.divider == value


@pytest.mark.parametrize("value", [0, 2**31])
def test_trigger_output_divider_invalid(value):
    with expected_protocol(Keysight81134A, []) as inst, pytest.raises(ValueError):
        inst.trigger_output.divider = value


@pytest.mark.parametrize("source", ["PER", "BITS"])
def test_trigger_output_source(source):
    with expected_protocol(
        Keysight81134A,
        [(f"OUTP0:SOUR {source}", None), ("OUTP0:SOUR?", source)],
    ) as inst:
        inst.trigger_output.source = source
        assert inst.trigger_output.source == source


def test_polarity():
    with expected_protocol(
        Keysight81134A,
        [("POL1 COMP", None), ("POL1?", "COMP")],
    ) as inst:
        inst.ch_1.polarity = "COMP"
        assert inst.ch_1.polarity == "COMP"


@pytest.mark.parametrize(
    "prop, command, value",
    [
        ("delay", "DEL", 500e-12),
        ("delay", "DEL", -5e-9),
        ("delay", "DEL", 230e-9),
        ("deskew", "DESK", -155e-12),
        ("deskew", "DESK", 10e-9),
        ("phase", "PHAS", -180),
        ("width", "WIDT", 1e-9),
        ("width", "WIDT", 100e-12),
        ("duty_cycle", "DCYC", 66),
    ],
)
def test_timing(prop, command, value):
    with expected_protocol(
        Keysight81134A,
        [(f"{command}2 {value:.10g}", None), (f"{command}2?", f"{value:+.8E}")],
    ) as inst:
        setattr(inst.ch_2, prop, value)
        assert getattr(inst.ch_2, prop) == pytest.approx(value)


@pytest.mark.parametrize(
    "prop, value",
    [
        ("delay", -6e-9),
        ("delay", 231e-9),
        ("deskew", 11e-9),
        ("phase", 280000),
        ("width", 50e-12),
        ("duty_cycle", 101),
    ],
)
def test_timing_out_of_range(prop, value):
    with expected_protocol(Keysight81134A, []) as inst, pytest.raises(ValueError):
        setattr(inst.ch_1, prop, value)


def test_level_limits_enabled():
    with expected_protocol(
        Keysight81134A,
        [("VOLT1:LIM:STAT 1", None), ("VOLT1:LIM:STAT?", "ON")],
    ) as inst:
        inst.ch_1.level_limits_enabled = True
        assert inst.ch_1.level_limits_enabled is True


@pytest.mark.parametrize(
    "channel, prop, value",
    [
        ("ch_1", "mode", "PRBS"),
        ("ch_1", "polarity", "INV"),
        ("trigger_output", "source", "DATA"),
    ],
)
def test_discrete_setting_invalid(channel, prop, value):
    with expected_protocol(Keysight81134A, []) as inst, pytest.raises(ValueError):
        setattr(getattr(inst, channel), prop, value)


def test_clock_source_invalid():
    with expected_protocol(Keysight81134A, []) as inst, pytest.raises(ValueError):
        inst.clock_source = "INT"
