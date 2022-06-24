PyOscilloskop_MSO5104
=============

This python library/application is a fork of [pklaus/PyOscilloskop](https://github.com/pklaus/PyOscilloskop), which allows control of Rigol MSO5104 Oscilloscope / Function Generator. As there's less usefullness of automating the control of an oscilloscope, oscilloscope control parts are lifted off, but those functions could also be enabled on MSO5104 without much alteration. Likewise the origianl project, it uses [universal_usbtmc][] for the communication with the device.


Installation
------------
First, install *universal_usbtmc*

	python3 -m pip install https://github.com/pklaus/universal_usbtmc/archive/master.zip
	
* Dring installation an error will occur in the middle: "Building wheel for universal-usbtmc (setup.py) ... error"
* However, if see the message---Successfully installed install-1.3.5 universal-usbtmc-0.3.dev0---in the end the installation is complete

Then install *PyOscilloskop_MSO5104*

    python3 -m pip install https://github.com/hcshin/PyOscilloskop_MSO5104/archive/master.zip

* During installation an error will occur in the middle: "Building wheel for PyOscilloskop (setup.py) ... error"
* However, if you can see the message---Successfully installed PyOscilloskop-0.2.0---in the end the installation is complete

Depending on the backend you want to use, you may have to install additional software.
Read the [universal_usbtmc README file](https://github.com/pklaus/universal_usbtmc/blob/master/README.md) for more information.

Configuring the udev rules
--------------
This step enables normal users to have access to the equipment, otherwise you have to change the ownership of the device on every boot

1. Connect the oscilloscope or function generator by a USB cable
	* Rigol equipment is recognised as a USBTMC device: a device file like /dev/usbtmc0 will be created
1. Query the udev attribute of /dev/usbtmc0 to to make a udev rule
	1. `$ sudo udevadm info -a /dev/usbtmc0 | grep -iC15 'rigol'`
	1. Check the values of `SUBSYSTEMS` and `ATTRS{manufacturer}` items
		* At the time of writing this guide
			* `SUBSYSTEMS=="usb"` (N.B. SUBSYSTEM"S" NOT SUBSYSTEM)
			* `ATTRS{manufacturer}=="Rigol"`
			* `ATTRS{idVendor}=="1ab1"`
1. Create a file named "rigol.rules" file with a text editor under `/etc/udev/rules.d/` and enter the following: `SUBSYSTEMS="usb", ATTRS{manufacturer}=="Rigol", MODE:="0666"`
	* Frist two items identifies a Rigol equipment
	* Last item gives a non-root user have read/write permission
1. Save the .rules file and apply the rule: $ sudo udevadm control --reload && udevadm trigger


Usage
-----

Import the modules in the installed Python package to automate function generator control.
Example code
```
import sys
import logging
import time

from pyoscilloskop import RigolFunctionGenerator
from universal_usbtmc.backends.linux_kernel import Instrument

dev_name = '/dev/usbtmc1'
device = Instrument(dev_name)

fg = RigolFunctionGenerator(device)

# sweep 1000Hz to 2000Hz of a sine wave with an increment of 5Hz
for freq in range(1000, 2000, 5):
    # fg.sine just changes the configuration of the function generator
    # it alone does not turn on the generator
    fg.sine(frequency=freq,
            channel=1,
            amplitude=1,
            offset=0,
            phase=0)
    fg.activate(channel=1) # this will turn on the generator
    time.sleep(1.0)
fg.deactivate(channel=1) # this will turn off the generator
```

Not Working Functions 
-----
Arbitrary waveform generation does not work for MSO5104. It has a syntax for arbitrary waveform output but the FG does not respond.


Author
------

This software started as a fork of [sbrinkmann / PyOscilloskop](https://github.com/sbrinkmann/PyOscilloskop).

* Hocheol Shin (2022)
* Philipp Klaus (2012-2015)
* Sascha Brinkmann (2011)

Resources
---------

* [Rigol MSO5000 Series Digital Oscilloscope](https://www.rigolna.com/products/digital-oscilloscopes/MSO5000/)

[universal_usbtmc]: https://github.com/pklaus/universal_usbtmc
[python-usbtmc]: https://github.com/python-ivi/python-usbtmc
[rpi-usbtmc-gateway]: https://github.com/pklaus/rpi-usbtmc-gateway
