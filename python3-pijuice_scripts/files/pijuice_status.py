#!/usr/bin/python3 -OO

from datetime import datetime

from pijuice import PiJuice

def getPiTemp():
    with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
        raw = f.readline()
        rawTemp = int(raw)
        return rawTemp / 1000

def main():
    pijuice = PiJuice(1, 0x14)
    status = pijuice.status.GetStatus()
    #print("status: %s" % status)
    #print(json.dumps(status, sort_keys=True, indent=4))
    batteryStatus = status['data']['battery']
    powerInput = status['data']['powerInput']

    faultStatus = pijuice.status.GetFaultStatus()['data']
    #print("status: %s" % faultStatus)

    chargeLevel = pijuice.status.GetChargeLevel()['data']
    batteryTemp = pijuice.status.GetBatteryTemperature()['data']
    batteryVoltage = pijuice.status.GetBatteryVoltage()['data']
    batteryCurrent = pijuice.status.GetBatteryCurrent()['data']
    
    ioVoltage= pijuice.status.GetIoVoltage()['data']
    ioCurrent = pijuice.status.GetIoCurrent()['data']

    now = datetime.now()
    piTemp = getPiTemp()

    timeStr = now.strftime("%d.%m.%Y, %H:%M:%S")
    print("Status:")
    print("date:        %s" % timeStr)
    print("PI:          %.2f°C" % piTemp)
    print("GPIO input:  %.3fV, %.3fA" % (ioVoltage / 1000, ioCurrent / 1000))
    print("Battery:     %.3fV, %.3fA, %d%%, %d°C" % (batteryVoltage / 1000, batteryCurrent / 1000, chargeLevel, batteryTemp))
    print("Charge:      %s" % batteryStatus)
    print("Power input: %s" % powerInput)
    print("Faults:      %s" % faultStatus)

if __name__ == '__main__':
    main()
