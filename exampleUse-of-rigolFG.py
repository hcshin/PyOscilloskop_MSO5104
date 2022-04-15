import sys
import logging
import time

from pyoscilloskop import RigolFunctionGenerator
from universal_usbtmc.backends.linux_kernel import Instrument

dev_name = '/dev/usbtmc0'
device = Instrument(dev_name)

fg = RigolFunctionGenerator(device)

# sweep 1000Hz to 2000Hz of a sine wave with an increment of 5Hz
for freq in range(1000, 2000, 5):
    # fg.sine just changes the configuration of the function generator
    # it alone does not turn on the generator
    fg.sine(frequency=freq,
            channel=1,
            amplitude=0.5,
            offset=0,
            phase=90)
    fg.activate(channel=1) # this will turn on the generator
    time.sleep(1.0)
fg.deactivate(channel=1) # this will turn off the generator

## Generate an arbitrary function: a sinc function with 4000 samples
#fg.arbitrary(RigolFunctionGenerator.getSinc(2**12), 100000)
## Generate an arbitrary function: a sin function with 4000 samples
#fg.arbitrary(RigolFunctionGenerator.getSin(2**12), 100000)
