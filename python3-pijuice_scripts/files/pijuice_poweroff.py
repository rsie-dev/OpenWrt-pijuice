#!/usr/bin/python3 -OO

import subprocess

from pijuice import PiJuice

def systemHalt(pijuice):
    pijuice.status.SetLedBlink('D2', 3, [150, 0, 0], 200, [0, 100, 0], 200)
    # Setting halt flag for 'pijuice_sys.py stop'
    #with open(HALT_FILE, 'w') as f:
    #    pass
    subprocess.call(["sudo", "halt"])

def triggerPowerOff(pijuice):
    pijuice.power.SetSystemPowerSwitch(0)
    pijuice.power.SetPowerOff(20)

def main():
    pijuice = PiJuice(1, 0x14)
    print("halt and completely power of")

    triggerPowerOff(pijuice)
    systemHalt(pijuice)


if __name__ == '__main__':
    main()
