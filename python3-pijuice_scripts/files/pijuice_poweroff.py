#!/usr/bin/python3 -OO
import os
import subprocess

from pijuice import PiJuice

HALT_FILE = '/tmp/pijuice_poweroff.flag'

def systemHalt(pijuice):
    pijuice.status.SetLedBlink('D2', 3, [150, 0, 0], 200, [0, 100, 0], 200)
    # Setting halt flag 
    with open(HALT_FILE, 'w') as f:
        pass
    subprocess.call(["sudo", "halt"])

def triggerPowerOff(pijuice):
    pijuice.power.SetSystemPowerSwitch(0)
    pijuice.power.SetPowerOff(20)

def main():
    if os.path.exists(HALT_FILE):
        print("halt already triggered -> ignore")

    print("halt and completely power of")
    pijuice = PiJuice(1, 0x14)
    triggerPowerOff(pijuice)
    systemHalt(pijuice)


if __name__ == '__main__':
    main()
