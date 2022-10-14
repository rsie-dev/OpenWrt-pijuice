# OpenWrt-pijuice
[PiJuice](https://github.com/PiSupply/PiJuice) packages for OpenWrt

## Installation
Install: 
- python3-pijuice (basic PiJuice support)
- python3-pijuice_scripts (additional support and configuration scripts)

Additionally these OpenWrt packages need to be installed, too:
- kmod-i2c-smbus
- kmod-i2c-bcm2835

Enable i2c on the pi:

Set in config.txt:
```
dtparam=i2c_arm=on
dtparam=spi=on
dtparam=i2s=on
```

## Notes
Tested on an raspberry pi zero w with an PiJuice zero.
