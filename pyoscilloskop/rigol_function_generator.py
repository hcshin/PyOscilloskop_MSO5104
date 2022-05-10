# -*- encoding: UTF8 -*-
#
# pyOscilloskop
#
# Copyright (2012) Philipp Klaus
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import time
import re
import sys
from math import sin

from .rigol_device import RigolDevice, RigolError, RigolUsageError, RigolTimeoutError

# The class RigolFunctionGenerator is able to control the
# function generator Rigol DG1022. Read more on
# http://goo.gl/byJvk

class RigolFunctionGenerator(RigolDevice):
    ### device dependent constatants:
    DAC_MIN = 0
    DAC_MAX = 2**14-1 # 14 bit precision: 0-16383
    MAX_DAC_VALUES = 2**12
    MAX_DAC_VALUES_AT_ONCE = 512

    ## valid responses for commands sent to the function generator:
    VALID_RESPONSES = {
      '*IDN?': {
        'full': r'(?P<manufacturer>[a-zA-Z0-9 ]+),(?P<model>[a-zA-Z0-9 ]+),(?P<serial>[A-Z0-9]+),(?P<edition>[0-9\.]+)',
        'groups' : {
          'manufacturer' : 'RIGOL TECHNOLOGIES',
          'model' : ['MSO5104'] # Add models here to work with multiple models (but only tested on MSO5104, and the instructions might differ)
        }
      },
      'SYSTem:ERRor?': {
        'full': r'(?P<errno>[+-][0-9]+),"(?P<errdesc>[a-zA-Z0-9 ]+)"'
      }
    }

    """Class to control a Rigol DS1000 series oscilloscope"""
    def __init__(self, device = None):
        RigolDevice.__init__(self, device)
        
        # check identification
        info = RigolFunctionGenerator.validate('*IDN?', self.dev.idn)
        print("Discovered a %s from %s." % (info["model"], info["manufacturer"]))

    def clear_error(self):
        """ Fetches error messages from the device and clears them from the queue.

          Some known error messages:
          +0,"No Error"                        Returned when everything is fine.
          -116,"Program mnemonic too long"
          -113,"Parameter not allowed"         Happens when sending more than 2^12 DAC values.
        """
        self.write("SYSTem:ERRor?")
        try:
            response = self.read()[:-1] # the subselection removes the trailing newline char
        except RigolTimeoutError:
            # a timeout seems to happen when the error queue just got empty
            return None
        if response == '+0,"No Error"': return None
        response = RigolFunctionGenerator.validate("SYSTem:ERRor?", response)
        return (int(response['errno']), response['errdesc'])

    def clear_errors(self):
        error = self.clear_error()
        if not error: return None
        errors = []
        while error:
            errors.append(error)
            error = self.clear_error()
        return errors

    def set_display_luminance(self, luminance = 5):
        ## Display backlight brightness (manual p. 2-69)
        ## The manual says the values can be between 0 and 31, but 0 seems to be invalid.
        if luminance not in range(1,32):
            raise RigolUsageError("The display luminance has to be in the limits of 1-31!")
        self.write("DISPlay:LUMInance %d" % luminance)

    def set_display_contrast(self, contrast = 5):
        ## Display contrast (manual p. 2-69)
        if contrast not in range(0,32):
            raise RigolUsageError("The display contrast has to be in the limits of 0-31!")
        self.write("DISPlay:CONTRAST %d" % contrast)

    def set_clock_source(self, internal = True):
        """ Set the clock source of the function generator
          either to internal or to external.
          When setting to the external source,
          the back 10MHz connector has to be used. (p.2-66 of the manual) """
        self.write("SYSTem:CLKSRC " + ("INT" if internal else "EXT") )

    def activate(self, channel=1):
        assert channel in (1, 2), f"channel must be either 1 or 2"
        self.write(f"source{channel}:output 1")

    def deactivate(self, channel: int = 1):
        assert channel in (1, 2), f"channel must be either 1 or 2"
        self.write(f"source{channel}:output 0")

    def deactivate_all(self):
        deactivate(1)
        deactivate(2)

    def sine(self, 
            frequency: float, 
            channel: int = 1, 
            amplitude: float = 0.1, 
            offset: float = 0, 
            phase: float = 0,
            impedance: int = -1):
        # value checking
        VOL_MAX_50 = 2.5
        AMP_MIN_50 = 10e-3
        assert impedance in (50, -1), "output impedance has to either 50Ohm or High Z (-1)"
        assert frequency <= 25e6 and frequency >= 100e-3, "frequency must meet 100e-3 <= frequency <= 25e6"
        assert channel in (1, 2), "channel must be either 1 or 2"
        if impedance == 50:
            assert amplitude >= AMP_MIN_50, f"amplitude must be larger than or equal to {AMP_MIN_50}"
            assert amplitude + offset < VOL_MAX_50, f"amplitude + offset should not exceed {VOL_MAX_50}"
        else:
            assert amplitude >= 2*AMP_MIN_50, f"amplitude must be larger than or equal to {2*AMP_MIN_50}"
            assert amplitude + offset < 2*VOL_MAX_50, f"amplitude + offset should not exceed {2*VOL_MAX_50}"
        assert offset >= 0, "offset must be zero or positive"
        assert phase <= 360 and phase >= 0, "phase must meet 0 <= phase <= 360"

        self.deactivate(channel)
        self.write(f"source{channel}:function sinusoid")
        self.write(f"source{channel}:frequency {frequency}")
        self.write(f"source{channel}:voltage {amplitude}")
        self.write(f"source{channel}:voltage:offset {offset}")
        self.write(f"source{channel}:phase {phase}")
        imp_str = "fifty" if impedance == 50 else "omeg"
        self.write(f"source{channel}:output:impedance {imp_str}")

    @staticmethod
    def validate(request, response):
        m = re.match( RigolFunctionGenerator.VALID_RESPONSES[request]['full'], response)
        if not m:
            raise RigolError('Response "%s" for the request "%s" was not expected and may be invalid.' % (response, request) )
        if not 'groups' in RigolFunctionGenerator.VALID_RESPONSES[request].keys(): return m.groupdict()
        for group in RigolFunctionGenerator.VALID_RESPONSES[request]['groups'].keys():
            matched_string = m.groupdict()[group]
            groupElem = RigolFunctionGenerator.VALID_RESPONSES[request]['groups'][group]
            matchSuccess = False
            if isinstance(groupElem, list):
                for groupSubElem in groupElem:
                    if re.match(groupSubElem.strip(), matched_string.strip()): matchSuccess = True
            else:
                if re.match(groupElem.strip(), matched_string.strip()): matchSuccess = True

            if not matchSuccess:
                raise RigolError('This software does not yet support products with %s as %s name so far.' % (matched_string, group) )
        return m.groupdict()

    @staticmethod
    def rescale(seq, low, high):
        cur_low = min(seq)
        # shift the sequence to positive values
        if cur_low < 0.0: seq = [val - cur_low for val in seq]
        cur_low = min(seq)
        cur_high = max(seq)
        ## rescale the values (multiplication with 0.999 seems to be necessary due to float inaccuracies).
        seq = [int(val*(high-low)*0.999/(cur_high-cur_low)) for val in seq]
        if min(seq) < low or max(seq) > high:
            print(seq)
            raise NameError("Something went wrong when rescaling values: min: %d, max: %d." % (min(seq), max(seq)))
        return seq

    @staticmethod
    def get_sin(samples, periods = 1):
        ## create a list containing  0, 1, 2, ... , samples-1
        sequence = range(0,samples)
        ## rescale the list to values from 0 to 1
        sequence = [x/float(samples) for x in sequence]
        ## create a sine function
        sequence = [sin(x*2*3.14*periods) for x in sequence]
        return sequence
    
    @staticmethod
    def get_sinc(samples, periods = 10):
        ## create a list containing  -samples/2, -samples/2+1, ..., -1, 0, 1, ... , samples/2-2, samples/2-1
        sequence = range(-samples/2,samples/2)
        ## rescale the list to values from -0.5 to .5
        sequence = [x/float(samples) for x in sequence]
        ## protect against division by 0 and scale to periods:
        sequence = [(x+0.0001/float(samples))*2*3.14*periods for x in sequence]
        ## calculate sin(x)/x
        sequence = [sin(x)/x for x in sequence]
        return sequence
