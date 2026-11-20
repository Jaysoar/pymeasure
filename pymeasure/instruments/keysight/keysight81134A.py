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

import logging
import re

from pymeasure.instruments import AdapterType, Channel, Instrument, SCPIMixin
from pymeasure.instruments.common_base import InstrumentProperty
from pymeasure.instruments.validators import strict_discrete_set, strict_range

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

CHANNEL_DIVIDERS = [1, 2, 4, 8, 16, 32, 64, 128]
PATTERN_MODES = ["SQU", "PULS", "DAT"]


def _to_bool(reply: str) -> bool:
    """Convert a boolean reply, which may be '1'/'0' or 'ON'/'OFF', to a bool."""
    return reply.strip().lstrip("+").upper() in {"1", "ON"}


def _to_error(reply: str) -> list[int | str]:
    """Convert an error queue reply to [code, message].

    Firmware 2.9.5 replies '<code>,"<message>"', for example '+0,"No error"'. The
    programming guide also shows '0' and '<code>:<message>', which are accepted too.
    """
    match = re.match(r"\s*([+-]?\d+)\s*[:,]?\s*(.*)", reply, re.DOTALL)
    if match is None:
        return [-1, reply.strip()]
    code = int(match.group(1))
    message = match.group(2).strip().strip('"')
    return [code, message or ("No error" if code == 0 else "")]


def _to_mode(reply: str) -> str:
    """Convert a pattern mode reply (for example 'SQUAR') to the short form it is set with."""
    reply = reply.strip().upper()
    for mode in PATTERN_MODES:
        if reply.startswith(mode):
            return mode
    return reply


class Keysight81134AOutput(Channel):
    """Base class of the outputs of the Keysight 81134A, with the settings they share.

    The levels are specified into a 50 Ohm load terminated to :attr:`termination_voltage`.
    """

    output_enabled: InstrumentProperty[bool] = Channel.control(
        "OUTP{ch}?",
        "OUTP{ch} %d",
        """Control whether the output is enabled (bool).

        For channels 1 and 2 this switches the normal and the complement output together and
        reads False only if both are off.
        """,
        validator=strict_discrete_set,
        values=[True, False],
        cast=str,
        get_process=_to_bool,
    )

    amplitude = Channel.control(
        "VOLT{ch}?",
        "VOLT{ch} %g",
        """Control the amplitude in Volts (float strictly from 0.05 to 2).

        Changing it keeps :attr:`offset` and changes :attr:`voltage_high` and
        :attr:`voltage_low`.
        """,
        validator=strict_range,
        values=[0.05, 2],
    )

    offset = Channel.control(
        "VOLT{ch}:OFFS?",
        "VOLT{ch}:OFFS %g",
        """Control the offset in Volts (float strictly from -1.975 to 2.975).

        Changing it keeps :attr:`amplitude` and changes :attr:`voltage_high` and
        :attr:`voltage_low`.
        """,
        validator=strict_range,
        values=[-1.975, 2.975],
    )

    voltage_high = Channel.control(
        "VOLT{ch}:HIGH?",
        "VOLT{ch}:HIGH %g",
        """Control the high level in Volts (float strictly from -1.95 to 3).

        The instrument also requires the resulting amplitude to be from 0.05 to 2 V.
        """,
        validator=strict_range,
        values=[-1.95, 3],
    )

    voltage_low = Channel.control(
        "VOLT{ch}:LOW?",
        "VOLT{ch}:LOW %g",
        """Control the low level in Volts (float strictly from -2 to 2.95).

        The instrument also requires the resulting amplitude to be from 0.05 to 2 V.
        """,
        validator=strict_range,
        values=[-2, 2.95],
    )

    termination_voltage = Channel.control(
        "VOLT{ch}:TERM?",
        "VOLT{ch}:TERM %g",
        """Control the voltage in Volts the 50 Ohm load is terminated to (float strictly from
        -2 to 3).""",
        validator=strict_range,
        values=[-2, 3],
    )


class Keysight81134AChannel(Keysight81134AOutput):
    """A channel output (1 or 2) of the Keysight 81134A pulse/pattern generator.

    Each channel has a normal (OUTPUT) and a complement output.
    """

    positive_output_enabled: InstrumentProperty[bool] = Channel.control(
        "OUTP{ch}:POS?",
        "OUTP{ch}:POS %d",
        """Control whether the normal output is enabled (bool).""",
        validator=strict_discrete_set,
        values=[True, False],
        cast=str,
        get_process=_to_bool,
    )

    negative_output_enabled: InstrumentProperty[bool] = Channel.control(
        "OUTP{ch}:NEG?",
        "OUTP{ch}:NEG %d",
        """Control whether the complement output is enabled (bool).""",
        validator=strict_discrete_set,
        values=[True, False],
        cast=str,
        get_process=_to_bool,
    )

    mode: InstrumentProperty[str] = Channel.control(
        "FUNC:MOD{ch}?",
        "FUNC:MOD{ch} %s",
        """Control the pattern mode (str strictly in 'SQU', 'PULS', 'DAT').

        'SQU' is a clock with 50 % duty cycle, 'PULS' are pulses of selectable :attr:`width` or
        :attr:`duty_cycle`, 'DAT' is a data pattern.
        """,
        validator=strict_discrete_set,
        values=PATTERN_MODES,
        cast=str,
        maxsplit=0,
        get_process=_to_mode,
    )

    divider = Channel.control(
        "OUTP{ch}:DIV?",
        "OUTP{ch}:DIV %d",
        """Control the frequency divider of the channel (int strictly in 1, 2, 4, 8, 16, 32,
        64, 128).

        The divided frequency must not be lower than 15 MHz.
        """,
        validator=strict_discrete_set,
        values=CHANNEL_DIVIDERS,
        cast=int,
    )

    polarity: InstrumentProperty[str] = Channel.control(
        "POL{ch}?",
        "POL{ch} %s",
        """Control the output polarity (str strictly in 'NORM', 'COMP').

        'COMP' swaps the normal and the complement output.
        """,
        validator=strict_discrete_set,
        values=["NORM", "COMP"],
        cast=str,
    )

    delay = Channel.control(
        "DEL{ch}?",
        "DEL{ch} %.10g",
        """Control the delay in seconds (float strictly from -5e-9 to 230e-9).

        Delay plus :attr:`deskew` must also be within these limits.
        """,
        validator=strict_range,
        values=[-5e-9, 230e-9],
    )

    deskew = Channel.control(
        "DESK{ch}?",
        "DESK{ch} %.10g",
        """Control the deskew in seconds, which is added to :attr:`delay` (float strictly from
        -10e-9 to 10e-9).""",
        validator=strict_range,
        values=[-10e-9, 10e-9],
    )

    phase = Channel.control(
        "PHAS{ch}?",
        "PHAS{ch} %.10g",
        """Control the phase in degrees (float strictly from -6000 to 279000).

        The instrument also limits it by the :attr:`delay` limits.
        """,
        validator=strict_range,
        values=[-6000, 279000],
    )

    width = Channel.control(
        "WIDT{ch}?",
        "WIDT{ch} %.10g",
        """Control the pulse width in seconds (float strictly from 100e-12 to 66.56667e-9).

        The instrument also limits it to the period minus 100 ps.
        """,
        validator=strict_range,
        values=[100e-12, 66.56667e-9],
    )

    duty_cycle = Channel.control(
        "DCYC{ch}?",
        "DCYC{ch} %.10g",
        """Control the duty cycle in percent (float strictly from 0 to 100).

        The instrument also limits it by the :attr:`width` limits. It cannot be set in the
        direct clock modes or with the NRZ data format.
        """,
        validator=strict_range,
        values=[0, 100],
    )

    level_limits_enabled: InstrumentProperty[bool] = Channel.control(
        "VOLT{ch}:LIM:STAT?",
        "VOLT{ch}:LIM:STAT %d",
        """Control whether the levels are limited to the current high and low levels (bool).

        While enabled, no level can be programmed beyond them.
        """,
        validator=strict_discrete_set,
        values=[True, False],
        cast=str,
        get_process=_to_bool,
    )


class Keysight81134ATriggerOutput(Keysight81134AOutput):
    """The trigger output (channel 0) of the Keysight 81134A pulse/pattern generator."""

    source: InstrumentProperty[str] = Channel.control(
        "OUTP{ch}:SOUR?",
        "OUTP{ch}:SOUR %s",
        """Control the trigger output mode (str strictly in 'PER', 'BITS').

        'PER' outputs a pulse every :attr:`divider` clock periods, 'BITS' once per data pattern.
        """,
        validator=strict_discrete_set,
        values=["PER", "BITS"],
        cast=str,
    )

    divider = Channel.control(
        "OUTP{ch}:DIV?",
        "OUTP{ch}:DIV %d",
        """Control the frequency divider of the trigger output (int strictly from 1 to
        2147483647).

        It only has an effect if :attr:`source` is 'PER'.
        """,
        validator=strict_discrete_set,
        values=range(1, 2**31),
        cast=int,
    )


class Keysight81134A(SCPIMixin, Instrument):
    """Represent the Keysight 81134A 3.35 GHz dual channel pulse/pattern generator.

    The channel outputs are available as :attr:`ch_1` and :attr:`ch_2` of type
    :class:`~pymeasure.instruments.keysight.keysight81134A.Keysight81134AChannel`, the trigger
    output as :attr:`trigger_output` of type
    :class:`~pymeasure.instruments.keysight.keysight81134A.Keysight81134ATriggerOutput`.

    The frequency is common to all outputs. The levels are specified into a 50 Ohm load, into
    a high impedance load the voltage is up to twice as large.

    .. code-block:: python

        generator = Keysight81134A("GPIB0::13::INSTR")
        generator.reset()
        generator.frequency = 500e6
        generator.ch_1.mode = "SQU"
        generator.ch_1.voltage_low = 0
        generator.ch_1.voltage_high = 1
        generator.ch_1.output_enabled = True
    """

    ch_1 = Instrument.ChannelCreator(Keysight81134AChannel, 1)

    ch_2 = Instrument.ChannelCreator(Keysight81134AChannel, 2)

    trigger_output = Instrument.ChannelCreator(Keysight81134ATriggerOutput, 0)

    def __init__(self, adapter: AdapterType, name: str = "Keysight 81134A", **kwargs):
        super().__init__(
            adapter,
            name,
            tcpip={"read_termination": "\n"},
            **kwargs,
        )

    next_error = Instrument.measurement(
        "SYST:ERR?",
        """Get the next error in the queue as [code, message].

        If you want to read and log all errors, use :meth:`check_errors` instead.
        """,
        cast=str,
        maxsplit=0,
        get_process=_to_error,
    )

    frequency = Instrument.control(
        "FREQ?",
        "FREQ %.10g",
        """Control the internal clock frequency in Hz (float strictly from 15e6 to 3.35e9).

        Setting it selects the internal clock if it is not selected already.
        """,
        validator=strict_range,
        values=[15e6, 3.35e9],
    )

    period = Instrument.control(
        "PER?",
        "PER %.10g",
        """Control the internal clock period in seconds (float strictly from 297.61905e-12 to
        66.66667e-9).""",
        validator=strict_range,
        values=[297.61905e-12, 66.66667e-9],
    )

    clock_source: InstrumentProperty[str] = Instrument.control(
        "TRIG:SOUR?",
        "TRIG:SOUR %s",
        """Control the clock source (str strictly in 'IMM', 'EXT', 'REF', 'IDIR', 'EDIR').

        'IMM' is the internal clock, 'EXT' the clock input, 'REF' the internal clock locked to a
        10 MHz reference at the clock input. The direct modes 'IDIR' (internal) and 'EDIR'
        (external) change the frequency without dropouts within one octave.
        """,
        validator=strict_discrete_set,
        values=["IMM", "EXT", "REF", "IDIR", "EDIR"],
        cast=str,
    )

    measured_frequency = Instrument.measurement(
        "MEAS:FREQ?",
        """Measure the clock frequency in Hz (float).

        The outputs stop during the measurement, which takes about 0.5 s. With an external clock
        it is the frequency at the clock input, 0 if there is no valid signal.
        """,
    )

    measured_period = Instrument.measurement(
        "MEAS:PER?",
        """Measure the clock period in seconds (float).

        The outputs stop during the measurement, which takes about 0.5 s. With an external clock
        it is the period at the clock input, 0 if there is no valid signal.
        """,
    )

    outputs_enabled: InstrumentProperty[bool] = Instrument.control(
        "OUTP:CENT?",
        "OUTP:CENT %d",
        """Control whether the outputs are enabled centrally (bool).

        If False, all outputs are off. If True, the outputs enabled individually are on.
        """,
        validator=strict_discrete_set,
        values=[True, False],
        cast=str,
        get_process=_to_bool,
    )

    display_enabled: InstrumentProperty[bool] = Instrument.control(
        "DISP?",
        "DISP %d",
        """Control whether the front panel display is on (bool).

        Turning it off speeds up programming. :meth:`reset` turns it on again, :meth:`preset`
        does not.
        """,
        validator=strict_discrete_set,
        values=[True, False],
        cast=str,
        get_process=_to_bool,
    )

    def preset(self) -> None:
        """Reset the instrument like :meth:`reset`, without turning on the display."""
        self.write("SYST:PRES")

    def save_state(self, location: int) -> None:
        """Save the instrument state to memory, overwriting the location.

        :param location: Memory location (int strictly from 1 to 9).
        """
        location = strict_discrete_set(location, range(1, 10))
        self.write(f"*SAV {location}")

    def recall_state(self, location: int) -> None:
        """Recall an instrument state from memory.

        :param location: Memory location (int strictly from 0 to 9). Location 0 holds the
            standard settings.
        """
        location = strict_discrete_set(location, range(10))
        self.write(f"*RCL {location}")
