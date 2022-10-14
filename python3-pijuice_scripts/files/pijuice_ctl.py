#!/usr/bin/python3

import os
import sys
import re
import argparse
import logging
import json
import time
import datetime
import subprocess

from pijuice import PiJuice, PiJuiceConfig
from pijuice import pijuice_hard_functions, pijuice_sys_functions, pijuice_user_functions

class CommandBase:
    def __init__(self, pijuice):
        self._pijuice = pijuice

    def _formateDateTime(self, dt):
        dt_fmt = "%a %Y-%m-%d %H:%M:%S"
        timeStr = dt.strftime(dt_fmt)
        return timeStr

    def _getFunction(self, function):
        if not function:
            return None
        upperFunctions = [name.upper() for name in pijuice_sys_functions]
        if function.upper() in upperFunctions:
            i = upperFunctions.index(function.upper())
            return pijuice_sys_functions[i]
        upperFunctions = [name.upper() for name in pijuice_user_functions[1:]]
        if function.upper() in upperFunctions:
            i = upperFunctions.index(function.upper())
            return pijuice_user_functions[i + 1]
        return None

    def _validateFunction(self, configData, function):
        if function in pijuice_sys_functions:
            return True
        if not 'user_functions' in configData:
            return False
        if not function in configData['user_functions']:
            return False
        return True

class BatteryCommand(CommandBase):
    def __init__(self, pijuice, current_fw_version):
        super().__init__(pijuice)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.current_fw_version = current_fw_version

    def getBattery(self, args):
        profile_name, profile_status, status_text = self._read_battery_profile_status()
        profile_data, ext_profile_data = self._read_battery_profile_data()
        temp_sense = self._read_temp_sense()
        self.logger.info("battery status:           " + status_text)
        self.logger.info("profile:                  " + profile_name)
        if profile_data == 'INVALID':
            self.logger.info("profile data:                  " + "invalid")
        else:
            self.logger.info("Capacity [mAh]:           %s" % profile_data['capacity'])
            self.logger.info("Charge current [mA]:      %s" % profile_data['chargeCurrent'])
            self.logger.info("Termination current [mA]: %s" % profile_data['terminationCurrent'])
            self.logger.info("Regulation voltage [mV]:  %s" % profile_data['regulationVoltage'])
            self.logger.info("Cutoff voltage [mV]:      %s" % profile_data['cutoffVoltage'])
            self.logger.info("Cold temperature [C]:     %s" % profile_data['tempCold'])
            self.logger.info("Cool temperature [C]:     %s" % profile_data['tempCool'])
            self.logger.info("Warm temperature [C]:     %s" % profile_data['tempWarm'])
            self.logger.info("Hot temperature [C]:      %s" % profile_data['tempHot'])
            self.logger.info("NTC B constant [1k]:      %s" % profile_data['ntcB'])
            self.logger.info("NTC resistance [ohm]:     %s" % profile_data['ntcResistance'])
            if self.current_fw_version >= 0x13:
                self.logger.info("Chemistry:                %s" % ext_profile_data['chemistry'])
        self.logger.info("Temperature sense:        %s" % temp_sense)

    def setBattery(self, args):
        self.logger.info("set battery")
        self._pijuice.config.SelectBatteryProfiles(self.current_fw_version)
        batteryProfiles = self._pijuice.config.batteryProfiles# + ['CUSTOM', 'DEFAULT']
        if not args.profile in batteryProfiles:
            self.logger.error("unknown or missing profile: %s" % args.profile)
        self.logger.info("new profile: %s" % args.profile)
        self._apply_settings(None, args.profile)

    def listBattery(self, args):
        self.logger.info("available battery profiles:")
        self._pijuice.config.SelectBatteryProfiles(self.current_fw_version)
        batteryProfiles = self._pijuice.config.batteryProfiles# + ['CUSTOM', 'DEFAULT']
        for profile in batteryProfiles:
            self.logger.info(" - %s" % profile)

    def _read_battery_profile_data(self):
        config = self._pijuice.config.GetBatteryProfile()
        if config['error'] != 'NO_ERROR':
            raise IOError("Unable to read battery data: %s" % config['error'])
        profile_data = config['data']

        if self.current_fw_version >= 0x13:
            extconfig = self._pijuice.config.GetBatteryExtProfile()
            if extconfig['error'] != 'NO_ERROR':
                raise IOError("Unable to read battery data: %s" % extconfig['error'])
            ext_profile_data = extconfig['data']
        else:
            ext_profile_data = None
        return profile_data, ext_profile_data

    def _read_battery_profile_status(self):
        profile_name = 'CUSTOM'
        status_text = ''
        status = self._pijuice.config.GetBatteryProfileStatus()
        if status['error'] != 'NO_ERROR':
            raise IOError("Unable to read battery status: %s" % status['error'])

        profile_status = status['data']

        if profile_status['validity'] == 'VALID':
            if profile_status['origin'] == 'PREDEFINED':
                profile_name = profile_status['profile']
        else:
            status_text = 'Invalid battery profile'
            return profile_name, profile_status, status_text

        self._pijuice.config.SelectBatteryProfiles(self.current_fw_version)
        batteryProfiles = self._pijuice.config.batteryProfiles# + ['CUSTOM', 'DEFAULT']
        if profile_status['source'] == 'DIP_SWITCH' and profile_status['origin'] == 'PREDEFINED' and batteryProfiles.index(profile_name) == 1:
            status_text = 'Default profile'
        else:
            status_text = 'Custom profile by: ' if profile_status['origin'] == 'CUSTOM' else 'Profile selected by: '
            status_text += profile_status['source']

        return profile_name, profile_status, status_text

    def _read_temp_sense(self):
        temp_sense_config = self._pijuice.config.GetBatteryTempSenseConfig()
        if temp_sense_config['error'] != 'NO_ERROR':
            raise IOError("Unable to read battery temp sense: %s" % temp_sense_config['error'])
        return temp_sense_config['data']

    def _apply_settings(self, temp_sense, profile_name):
        if temp_sense:
            status = self._pijuice.config.SetBatteryTempSenseConfig(temp_sense)
            if status['error'] != 'NO_ERROR':
                raise IOError("Unable to set battery temp sense: %s" % status['error'])

        #status = pijuice.config.SetRsocEstimationConfig(self.RSOC_ESTIMATION_OPTIONS[self.rsoc_estimation_profile_idx])
        #if status['error'] != 'NO_ERROR':
        #    confirmation_dialog('Failed to apply rsoc estimation options. Error: {}'.format(
        #        status['error']), next=main_menu, single_option=True)

        if profile_name:
            status = self._pijuice.config.SetBatteryProfile(profile_name)
            if status['error'] != 'NO_ERROR':
                raise IOError("Unable to set battery profile: %s" % status['error'])
        self.logger.info("settings successfully updated")

class FirmwareCommand(CommandBase):
    PiJuiceFirmwarePath = '/usr/share/pijuice/data/firmware/'
    FWRegex = re.compile(r"PiJuice-V(\d+)\.(\d+)_(\d+_\d+_\d+).elf.binary")
    VersionRegex = re.compile(r"V(\d+)\.(\d+)")
    FIRMWARE_UPDATE_ERRORS = ['NO_ERROR', 'I2C_BUS_ACCESS_ERROR', 'INPUT_FILE_OPEN_ERROR', 'STARTING_BOOTLOADER_ERROR', 'FIRST_PAGE_ERASE_ERROR',
                              'EEPROM_ERASE_ERROR', 'INPUT_FILE_READ_ERROR', 'PAGE_WRITE_ERROR', 'PAGE_READ_ERROR', 'PAGE_VERIFY_ERROR', 'CODE_EXECUTE_ERROR']

    def __init__(self, pijuice, current_fw_version):
        super().__init__(pijuice)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.current_fw_version = current_fw_version

    def get_current_fw_version(self):
        # Returns current version as int (first 4 bits - minor, second 4 bits - major)
        status = self._pijuice.config.GetFirmwareVersion()
        if status['error'] == 'NO_ERROR':
            major, minor = status['data']['version'].split('.')
        else:
            major = minor = 0
        current_version = (int(major) << 4) + int(minor)
        return current_version

    def getFirmware(self, args):
        current_version_txt = self.version_to_str(self.current_fw_version)
        self.logger.info("current firmware version: V%s" % current_version_txt)
        latest_version = self._getLatestVersion()
        status = self._get_fw_status(latest_version)
        self.logger.info("Status:                   %s" % status)

    def listFirmware(self, args):
        self.logger.info("available firmware versions:")
        versions = self._getAvailableVersions()
        for version in versions:
            version_txt = self.version_to_str(version[0])
            self.logger.info(" - V%s (%s)" % (version_txt, version[1]))

    def updateFirmware(self, args):
        self.logger.info("update firmware")
        if args.version:
            match = self.VersionRegex.match(args.version)
            if not match:
                raise ValueError("version does not conform to schema: %s" % args.version)
            major = int(match.group(1))
            minor = int(match.group(2))
            new_version = (major << 4) + minor
            versions = self._getAvailableVersions()
            for version in versions:
                if version[0] == new_version:
                    fwFile = os.path.join(self.PiJuiceFirmwarePath, version[1])
                    break
            else:
                raise ValueError("No firmware file for this version found: %s" % args.version)

        elif args.file:
            fwFile = os.path.join(self.PiJuiceFirmwarePath, args.file)
            match = self.FWRegex.match(args.file)
            if not match:
                raise ValueError("file name does not conform to schema: %s" % args.file)
            major = int(match.group(1))
            minor = int(match.group(2))
            new_version = (major << 4) + minor
        else:
            raise ValueError("version or file must be given")

        if new_version == self.current_fw_version:
            self.logger.error("Firmware version already installed")
            return
        new_version_txt = self.version_to_str(new_version)

        if not os.path.isfile(fwFile):
            raise ValueError("file does not exist: %s" % fwFile)
        
        self.logger.info("update firmware to: V%s" % new_version_txt)
        self.logger.info("new firmware file:  %s" % fwFile)
        if not self._checkDevicePower():
            self.logger.error("Charge level is too low")
            return

        #self._update_firmware(fwFile)

    def _checkDevicePower(self):
        device_status = self._pijuice.status.GetStatus()
        if device_status['error'] != 'NO_ERROR':
            raise IOError("Unable to get device status: %s" % device_status['error'])

        if device_status['data']['powerInput'] != 'PRESENT' and \
            device_status['data']['powerInput5vIo'] != 'PRESENT' and \
            self._pijuice.status.GetChargeLevel().get('data', 0) < 20:
            # Charge level is too low
            return False
        return True

    def _update_firmware(self, firmware_path):
        current_addr = self._pijuice.config.interface.GetAddress()
        if not current_addr:
            error_status = "UNKNOWN_ADDRESS"
        else:
            # Start the firmware update in a subprocess
            error_status = None
            addr = format(current_addr, 'x')
            with open('/dev/null','w') as f:    # Suppress pijuiceboot output
                p = subprocess.Popen(['pijuiceboot', addr, firmware_path], stdout=f, stderr=subprocess.STDOUT)
            # Show the 'Wait for update' screen  with a rotating spinner
            finished = False
            while not finished:
                try:
                    finished = True
                    p.communicate(timeout=0.3)
                except subprocess.TimeoutExpired:
                    finished = False
                if not finished:
                    i = (i+1)%4
                    #waittext.set_text("Updating firmware, Wait " + spinner[i])
                    self.logger.debug("Updating firmware, Wait ...")
                    #loop.draw_screen()
            # Check the result
            result = 256 - p.returncode
            if result != 256:
                error_status = self.FIRMWARE_UPDATE_ERRORS[result] if result < 11 else 'UNKNOWN'

        if error_status:
            messages = {
                "I2C_BUS_ACCESS_ERROR": 'Check if I2C bus is enabled.',
                "INPUT_FILE_OPEN_ERROR": 'Firmware binary file might be missing or damaged.',
                "STARTING_BOOTLOADER_ERROR": 'Try to start bootloader manually. Press and hold button SW3 while powering up RPI and PiJuice.',
                "UNKNOWN_ADDRESS": "Unknown PiJuice I2C address",
            }
            resolution = messages.get(error_status, '')
            self.logger.error("Firmware update failed: %s" % error_status)
            self.logger.info("Possible resolution:    %s" % resolution)
            return False

        # Wait till firmware has restarted (current_version != 0)
        self.logger.info("Waiting for firmware restart...")
        current_version = 0
        while current_version == 0:
            current_version = self.get_current_fw_version()
            time.sleep(0.2)
        current_fw_version = current_version
        self.logger.info("Firmware update successful: V%s" % self.version_to_str(current_fw_version))
        return True

    def _get_fw_status(self, latest_version):
        current_version = self.current_fw_version
        if current_version and latest_version:
            if latest_version > current_version:
                version_txt = self.version_to_str(latest_version)
                firmware_status = 'New firmware (V' + version_txt + ') is available'
            else:
                firmware_status = 'up to date'
        elif not current_version:
            firmware_status = 'unknown'
        else:
            firmware_status = 'Missing/wrong firmware file'
        return firmware_status
    
    def _getLatestVersion(self):
        latest_version = 0
        versions = self._getAvailableVersions()
        for version in versions:
            if version[0] >= latest_version:
                latest_version = version[0]
        return latest_version

    def _getAvailableVersions(self):
        binDir = self.PiJuiceFirmwarePath
        files = [f for f in os.listdir(binDir) if os.path.isfile(os.path.join(binDir, f))]
        files = sorted(files)
        versions = []
        for fileName in files:
            match = self.FWRegex.match(fileName)
            if match:
                major = int(match.group(1))
                minor = int(match.group(2))
                version = (major << 4) + minor
                entry = version, fileName
                versions.append(entry)
        return versions

    def version_to_str(self, number):
        # Convert int version to str {major}.{minor}
        return "{}.{}".format(number >> 4, number & 15)

class ConfigCommand(CommandBase):
    SERVICE_CTL = "/etc/init.d/pijuice"
    PiJuiceConfigDataPath = '/etc/pijuice/pijuice_config.JSON'

    def __init__(self, pijuice):
        super().__init__(pijuice)
        self.logger = logging.getLogger(self.__class__.__name__)

    def loadPiJuiceConfig(self):
        with open(self.PiJuiceConfigDataPath, 'r') as outputConfig:
            pijuiceConfigData = json.load(outputConfig)
            return pijuiceConfigData

    def savePiJuiceConfig(self, pijuiceConfigData):
        with open(self.PiJuiceConfigDataPath, 'w+') as outputConfig:
            json.dump(pijuiceConfigData, outputConfig, indent=2)
        #ret = self.notify_service()
        #if ret != 0:
        #    self.logger.error("failed to communicate with PiJuice service")
        #else:
        #    self.logger.info("settings saved")

    def notify_service(self):
        ret = -1
        try:
            with open(self.PID_FILE, 'r') as r:
                pid = int(r.read())
                ret = os.system("kill -SIGHUP " + str(pid) + " > /dev/null 2>&1")
        except:
            pass
        return ret

class ServiceCommand(ConfigCommand):
    PID_FILE = '/tmp/pijuice_sys.pid'

    def __init__(self, pijuice):
        super().__init__(pijuice)
        self.logger = logging.getLogger(self.__class__.__name__)

    def getService(self, args):
        status = subprocess.run([self.SERVICE_CTL, "enabled"])
        enabled = status.returncode == 0
        self.logger.info("service enabled:               %s" % enabled)
        status = subprocess.run([self.SERVICE_CTL, "running"])
        running = status.returncode == 0
        self.logger.info("service running:               %s" % running)
    
        configData = self.loadPiJuiceConfig()
        serviceEnabled = configData.get('system_task', {}).get('enabled')
        self.logger.info("service config enabled:        %s" % serviceEnabled)
            
        minChargeEnabled = False
        minChargeThreshold = 0
        if 'system_task' in configData:
            if 'min_charge' in configData['system_task']:
                minChargeEnabled = configData['system_task']['min_charge'].get('enabled', False)
                minChargeThreshold= configData['system_task']['min_charge'].get('threshold', 0)
        self.logger.info("min. charge detection enabled: %s (%s%%)" % (minChargeEnabled, minChargeThreshold))

    def enableService(self, args, enable):
        self.logger.info("enable service:     %s" % enable)
        configData = self.loadPiJuiceConfig()
        configData['system_task']['enabled'] = enable
        if enable:
            action = "enable"
        else:
            action = "disable"
        self.savePiJuiceConfig(configData)
        subprocess.run([self.SERVICE_CTL, action], check=True)

    def setMinCharge(self, args):
        if args.threshold is None:
            raise ValueError("no threshold given")

        enabled = args.threshold != 0
        configData = self.loadPiJuiceConfig()
        if not 'system_task' in configData:
            configData['system_task'] = {}
        if not 'min_charge' in configData['system_task']:
            configData['system_task']['min_charge'] = {}

        if enabled:
            self.logger.info("enable min. charge detection threshold %s" % args.threshold)
            configData['system_task']['min_charge']['threshold'] = args.threshold
        else:
            self.logger.info("disable min. charge detection")
        configData['system_task']['min_charge']['enabled'] = enabled
        self.savePiJuiceConfig(configData)

class EventCommand(ConfigCommand):
    EVENTS = ['low_charge', 'low_battery_voltage', 'no_power', 'power', 'watchdog_reset', 'button_power_off', 'forced_power_off',
              'forced_sys_power_off', 'sys_start', 'sys_stop']
    EVTTXT = ['Low charge', 'Low battery voltage', 'No power', 'Power present', 'Watchdog reset', 'Button power off', 'Forced power off',
              'Forced sys power off', 'System start', 'System stop']

    def __init__(self, pijuice):
        super().__init__(pijuice)
        self.logger = logging.getLogger(self.__class__.__name__)

    def getEvents(self, args):
        self.logger.info("events:")
        configData = self.loadPiJuiceConfig()
        for idx, event in enumerate(self.EVENTS):
            enabled, function = self._getEventStatus(configData, event)
            self.logger.info(" - %-20s: %-5s (%s)" % (self.EVTTXT[idx], enabled, function))

    def enableEvent(self, args):
        i = self._getEvent(args.event)
        event = self.EVENTS[i]
        function = self._getFunction(args.function)
        if not function:
            raise ValueError("no function given")
        configData = self.loadPiJuiceConfig()
        if not self._validateFunction(configData, function):
            raise ValueError("function not active: %s" % args.function)
        self.logger.info("enable event %s with: %s" % (self.EVTTXT[i], function))
        self._setEvent(configData, event, True, function)
        self.savePiJuiceConfig(configData)

    def disableEvent(self, args):
        i = self._getEvent(args.event)
        event = self.EVENTS[i]
        self.logger.info("disable event: %s" % self.EVTTXT[i])
        configData = self.loadPiJuiceConfig()
        self._setEvent(configData, event, False, None)
        self.savePiJuiceConfig(configData)

    def _setEvent(self, configData, event, enabled, function):
        if not 'system_events' in configData:
            configData['system_events'] = {}
        if not event in configData['system_events']:
            configData['system_events'][event] = {}
        configData['system_events'][event]['enabled'] = enabled
        if function:
            configData['system_events'][event]['function'] = function

    def _getEvent(self, event):
        if not event:
            raise ValueError("no event given")
        upperEvents = [name.upper() for name in self.EVTTXT]
        if not event.upper() in upperEvents:
            raise ValueError("unknown event: " % event)
        i = upperEvents.index(event.upper())
        return i

    def _getEventStatus(self, configData, event):
        enabled = False
        function = 'NO_FUNC'
        if 'system_events' in configData:
            if event in configData['system_events']:
                if 'enabled' in configData['system_events'][event]:
                    enabled = configData['system_events'][event]['enabled']
                if 'function' in configData['system_events'][event]:
                    function = configData['system_events'][event]['function']
        return enabled, function

class FunctionsCommand(ConfigCommand):
    def __init__(self, pijuice):
        super().__init__(pijuice)
        self.logger = logging.getLogger(self.__class__.__name__)

    def getFunctions(self, args):
        if not args.kind:
            raise ValueError("function kind must be given")

        if args.kind in ['all', 'hard']:
            self.logger.info("hardware functions:")
            for function in pijuice_hard_functions:
                self.logger.info(" - %s" % function)

        if args.kind in ['all', 'sys']:
            self.logger.info("system functions:")
            for function in pijuice_sys_functions:
                self.logger.info(" - %s" % function)

        if args.kind in ['all', 'user']:
            self.logger.info("user functions:")
            configData = self.loadPiJuiceConfig()
            for idx, function in enumerate(pijuice_user_functions[1:]):
                fkey = 'USER_FUNC%s' % (idx + 1)
                func = ""
                if 'user_functions' in configData:
                    if fkey in configData['user_functions']:
                        func = configData['user_functions'][fkey]
                self.logger.info(" - %-11s: %s" % (fkey, func))

    def setFunction(self, args):
        if not args.nr or not args.script:
            raise ValueError("both nr and script must be given")
        if not os.path.isfile(args.script):
            raise ValueError("file not found: %s" % args.script)
        if not os.access(args.script, os.X_OK):
            raise ValueError("file not executable: %s" % args.script)

        configData = self.loadPiJuiceConfig()
        if not 'user_functions' in configData:
            configData['user_functions'] = {}
        fkey = 'USER_FUNC%s' % args.nr
        configData['user_functions'][fkey] = args.script
        self.logger.info("set user function %s to: %s" % (fkey, args.script))
        self.savePiJuiceConfig(configData)

class RealTimeClockCommand(CommandBase):
    def __init__(self, pijuice):
        super().__init__(pijuice)
        self.logger = logging.getLogger(self.__class__.__name__)

    def getRTC(self, args):
        st = datetime.datetime.now()
        utcST = st.astimezone(tz=datetime.timezone.utc)
        system_time = self._formateDateTime(st)
        utc_system_time = self._formateDateTime(utcST)
        device_time = self._get_device_time()
        self.logger.info("system Time:     %s" % system_time)
        self.logger.info("system UTC Time: %s" % utc_system_time)
        self.logger.info("device UTC Time: %s" % device_time)

    def setRTC(self, args):
        st = datetime.datetime.utcnow()
        self._set_device_time(st)

    def _get_device_time(self):
        device_time = ''
        t = self._pijuice.rtcAlarm.GetTime()
        if t['error'] != 'NO_ERROR':
            raise IOError("Unable to get device time: %s" % t['error'])
        t = t['data']
        dt = datetime.datetime(t['year'], t['month'], t['day'], t['hour'], t['minute'], t['second'])
        device_time = self._formateDateTime(dt)
        return device_time

    def _set_device_time(self, st):
        system_time = self._formateDateTime(st)
        self.logger.info("set device UTC Time to: " + system_time)
        s = self._pijuice.rtcAlarm.SetTime({
            'second': st.second,
            'minute': st.minute,
            'hour': st.hour,
            'weekday': st.weekday() + 1,
            'day': st.day,
            'month': st.month,
            'year': st.year,
            'subsecond': st.microsecond // 1000000
        })
        if s['error'] != 'NO_ERROR':
            raise IOError("Unable to set device RTC time: %s" % s['error'])
    

class WakeupCommand(ConfigCommand):
    def __init__(self, pijuice, current_fw_version):
        super().__init__(pijuice)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.current_fw_version = current_fw_version

    def getStatus(self, args):
        wakeupAlarmEnabled, alarm_status = self._getAlarmStatus()
        self.logger.info("Wakeup alarm enabled:  %s" % wakeupAlarmEnabled)
        if self.current_fw_version >= 0x15:
            wakeupChargeEnabled, trigger_level = self._getChargeStatus()
            self.logger.info("Wakeup charge enabled: %s" % wakeupChargeEnabled)

    def getAlarm(self, args):
        wakeup_enabled, alarm_status = self._getAlarmStatus()
        self.logger.info("Wakeup enabled:  %s" % wakeup_enabled)
        self.logger.info("Alarm status:    %s" % alarm_status)
        alarm = self._getAlarm()
        alarmStr = self._formatAlarm(alarm)
        self.logger.info("Alarm:           %s" % alarmStr)

    def setAlarm(self, args):
        if not args.hour:
            raise ValueError("hour missing")

        if args.utc:
            alarmTime = datetime.time(hour=args.hour, minute=args.minute)
            effectiveAlarmTime = alarmTime
        else:
            if time.daylight:
                tz = time.altzone
                tzname = time.tzname[1]
            else:
                tz = time.timezone
                tzname = time.tzname[0]
            self.logger.debug("timezone:           %s s" % tz)
            utcOffset = datetime.timedelta(seconds=-tz)
            self.logger.debug("UTC offset:         %s" % utcOffset)
            timeZone = datetime.timezone(utcOffset, tzname)
            self.logger.debug("timezone:           %s" % timeZone)
            alarmTime = datetime.time(hour=args.hour, minute=args.minute, tzinfo=timeZone)
            dt = datetime.datetime.combine(datetime.date.today(), alarmTime)
            utcDT = dt.astimezone(tz=datetime.timezone.utc)
            effectiveAlarmTime = utcDT.time()

        self.logger.info("alarm time:         %s" % alarmTime)
        self.logger.info("UTC alarm time:     %s" % effectiveAlarmTime)

        alarm = {}
        alarm['hour'] = effectiveAlarmTime.hour
        alarm['day'] = 'EVERY_DAY'
        alarm['minute'] = effectiveAlarmTime.minute
        alarmStr = self._formatAlarm(alarm)
        self.logger.info("Set UTC alarm time: %s" % alarmStr)
        self._setAlarm(alarm)

    def enableAlarm(self, args):
        self._setAlarmEnable(True)

    def disableAlarm(self, args):
        self._setAlarmEnable(False)

    def getCharge(self, args):
        if self.current_fw_version < 0x15:
            self.logger.error("Wakeup on charge not supported by firmware version")
            return
        wakeupChargeEnabled, trigger_level = self._getChargeStatus()
        self.logger.info("Wakeup charge enabled: %s" % wakeupChargeEnabled)
        self.logger.info("Trigger level:         %s%%" % trigger_level)
    
    def enableCharge(self, args):
        if self.current_fw_version < 0x15:
            self.logger.error("Wakeup on charge not supported by firmware version")
            return
        if args.chargeLevel:
            chargeLevel = args.chargeLevel
        else:
            wakeupChargeEnabled, trigger_level = self._getChargeStatus()
            chargeLevel = trigger_level
        self.logger.info("Enable wakeup on charge at: %s%%" % chargeLevel)
        configData = self.loadPiJuiceConfig()
        self._configChargeWakeup(configData, True, chargeLevel)
        self._setChargeWakeup(True, chargeLevel)
        self.savePiJuiceConfig(configData)

    def disableCharge(self, args):
        if self.current_fw_version < 0x15:
            self.logger.error("Wakeup on charge not supported by firmware version")
            return
        configData = self.loadPiJuiceConfig()
        self.logger.info("Disable wakeup on charge")
        self._configChargeWakeup(configData, False, None)
        self._setChargeWakeup(False, None)
        self.savePiJuiceConfig(configData)

    def _getChargeStatus(self):
        ret = self._pijuice.power.GetWakeUpOnCharge()
        if ret['error'] != 'NO_ERROR':
            raise IOError("Unable to get wakeup on charge status: %s" % ret['error'])
        wkupenabled = ret['non_volatile']
        trigger_level = 50
        if wkupenabled:
           trigger_level = ret['data']
        return wkupenabled, trigger_level

    def _configChargeWakeup(self, pijuiceConfigData, wkupenabled, chargeLevel):
        if not 'wakeup_on_charge' in pijuiceConfigData['system_task']:
            pijuiceConfigData['system_task']['wakeup_on_charge'] = {}
        pijuiceConfigData['system_task']['wakeup_on_charge']['enabled'] = wkupenabled
        if chargeLevel:
            pijuiceConfigData['system_task']['wakeup_on_charge']['trigger_level'] = chargeLevel
        
    def _setChargeWakeup(self, wkupenabled, triggerLevel):
        if wkupenabled:
            levelStr = triggerLevel
        else:
            levelStr = 'DISABLED'
        ret = self._pijuice.power.SetWakeUpOnCharge(levelStr, True)
        if ret['error'] != 'NO_ERROR': 
            raise IOError("Unable to set wakeup on charge status: %s" % ret['error'])

    def _setAlarmEnable(self, enable):
        enableStr = "enable" if enable else "disable"
        self.logger.info("%s alarm" % enableStr)
        ret = self._pijuice.rtcAlarm.SetWakeupEnabled(enable)
        if ret['error'] != 'NO_ERROR':
            raise IOError("Unable to %s alarm: %s" % (enableStr, ret['error']))

    def _getAlarmStatus(self):
        s = self._pijuice.rtcAlarm.GetControlStatus()
        if s['error'] != 'NO_ERROR':
            raise IOError("Unable to get device control status: %s" % s['error'])
        status = "OK"
        wakeup_enabled = s['data']['alarm_wakeup_enabled']
        #if s['data']['alarm_flag']:
        #    t = self._pijuice.rtcAlarm.GetTime()
        #    if t['error'] != 'NO_ERROR':
        #        raise IOError("Unable to get device time: %s" % t['error'])
        #    status = 'Last: {}:{}:{}'.format(str(t['hour']).rjust(2, '0'),
        #                                          str(t['minute']).rjust(2, '0'),
        #                                          str(t['second']).rjust(2, '0'))
            #pijuice.rtcAlarm.ClearAlarmFlag()
        return wakeup_enabled, status

    def _formatAlarm(self, alarm):
        entries = []

        if 'day' in alarm:
            if alarm['day'] == 'EVERY_DAY':
                entries.append("every day")
            else:
                entries.append("day of month: %s" % alarm['day'])
        elif 'weekday' in alarm:
            if alarm['weekday'] == 'EVERY_DAY':
                entries.append("every weekday")
            else:
                entries.append("day of week: %s" % alarm['weekday'])

        if 'hour' in alarm:
            if alarm['hour'] == 'EVERY_HOUR':
                entries.append("every hour")
            else:
                entries.append("hour: %s" % alarm['hour'])

        if 'minute' in alarm:
            entries.append("minute: %s" % alarm['minute'])
        elif 'minute_period' in alarm:
            entries.append("minute period: %s" % alarm['minute_period'])

        if 'second' in alarm:
            entries.append("second: %s" % alarm['second'])

        return ", ".join(entries)

    def _getAlarm(self):
        alarm = self._pijuice.rtcAlarm.GetAlarm()
        if alarm['error'] != 'NO_ERROR':
            raise IOError("Unable to get alarm: %s" % alarm['error'])

        status = {unit: {} for unit in ('day', 'hour', 'minute', 'second')}
        # Empty by default
        for unit in ('day', 'hour', 'minute', 'second'):
            status[unit]['value'] = ''

        alarm = alarm['data']
        return alarm

    def _setAlarm(self, alarm):
        status = self._pijuice.rtcAlarm.SetAlarm(alarm)
        if status['error'] != 'NO_ERROR':
            raise IOError("Unable to set alarm: %s" % alarm['error'])
        self.logger.info("alarm time set")

class FaultCommand(CommandBase):
    def __init__(self, pijuice):
        super().__init__(pijuice)
        self.logger = logging.getLogger(self.__class__.__name__)

    def getFaults(self, args):
        faultStatus = self._getFaultStatus()
        self.logger.info("Faults:")
        for key, value in faultStatus.items():
            if value:
                self.logger.info(" - %s" % key)

    def clearFaults(self, args):
        self.logger.info("Clear fault flags")
        faultStatus = self._getFaultStatus()
        flags = faultStatus.keys()
        self._pijuice.status.ResetFaultFlags(flags)

    def _getFaultStatus(self):
        ret = self._pijuice.status.GetFaultStatus()
        if ret['error'] != 'NO_ERROR':
            raise IOError("Unable to get faults: %s" % ret['error'])
        faultStatus = ret['data']
        return faultStatus

class ButtonsCommand(ConfigCommand):
    def __init__(self, pijuice):
        super().__init__(pijuice)
        self.logger = logging.getLogger(self.__class__.__name__)

    def getButtons(self, args):
        self.logger.info("Buttons:")
        for idx, button in enumerate(PiJuiceConfig.buttons):
            ret = self._pijuice.config.GetButtonConfiguration(button)
            if ret['error'] != 'NO_ERROR':
                raise IOError("Unable to get button config: %s" % ret['error'])
            button_config = ret['data']
            self.logger.info(" Button %d:" % (idx + 1))
            for event in PiJuiceConfig.buttonEvents:
                eventConfig = button_config[event]
                function = eventConfig['function']
                parameter = eventConfig['parameter'] 
                self.logger.info("  - %-12s: %s (%s)" % (event, function, parameter))

    def setButton(self, args):
        if not args.nr:
            raise ValueError("button number must be given")
        if not args.event:
            raise ValueError("button event must be given")
        function = self._getFunction(args.function)
        if not function:
            raise ValueError("no function given")
        configData = self.loadPiJuiceConfig()
        if not self._validateFunction(configData, function):
            raise ValueError("function not active: %s" % args.function)
        parameter = args.parameter if args.parameter is not None else 0

        button = PiJuiceConfig.buttons[args.nr -1]
        ret = self._pijuice.config.GetButtonConfiguration(button)
        if ret['error'] != 'NO_ERROR':
            raise IOError("Unable to get button config: %s" % ret['error'])
            
        button_config = ret['data']
        button_config[args.event]['function'] = function
        button_config[args.event]['parameter'] = parameter
        self.logger.info("set button %s on event %s to: %s (%s)" % (button, args.event, function, parameter))
        ret = self._pijuice.config.SetButtonConfiguration(button, button_config)
        if ret['error'] != 'NO_ERROR':
            raise IOError("Unable to set button config: %s" % ret['error'])

    def _getFunction(self, function):
        func = super()._getFunction(function)
        if func:
            return func
        functions = ['NO_FUNC'] + pijuice_hard_functions
        upperFunctions = [name.upper() for name in functions]
        if function.upper() in upperFunctions:
            i = upperFunctions.index(function.upper())
            return functions[i]
        return None

    def _validateFunction(self, configData, function):
        if function in ['NO_FUNC'] + pijuice_hard_functions:
            return True
        if super()._validateFunction(configData, function):
            return True
        return False

class Control:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.current_fw_version = None

    def battery(self, args, pijuice):
        self.logger.debug(args.subparser_name)
        command = BatteryCommand(pijuice, self.current_fw_version)
        if args.get:
            command.getBattery(args)
        elif args.set:
            command.setBattery(args)
        elif args.list:
            command.listBattery(args)

    def service(self, args, pijuice):
        self.logger.debug(args.subparser_name)
        command = ServiceCommand(pijuice)
        if args.get:
            command.getService(args)
        elif args.enable:
            command.enableService(args, True)
        elif args.disable:
            command.enableService(args, False)
        elif args.minCharge:
            command.setMinCharge(args)

    def events(self, args, pijuice):
        self.logger.debug(args.subparser_name)
        command = EventCommand(pijuice)
        if args.get:
            command.getEvents(args)
        elif args.enable:
            command.enableEvent(args)
        elif args.disable:
            command.disableEvent(args)

    def function(self, args, pijuice):
        self.logger.debug(args.subparser_name)
        command = FunctionsCommand(pijuice)
        if args.get:
            command.getFunctions(args)
        elif args.set:
            command.setFunction(args)

    def rtc(self, args, pijuice):
        self.logger.debug(args.subparser_name)
        command = RealTimeClockCommand(pijuice)
        if args.get:
            command.getRTC(args)
        elif args.set:
            command.setRTC(args)

    def wakeup(self, args, pijuice):
        self.logger.debug(args.subparser_name)
        command = WakeupCommand(pijuice, self.current_fw_version)
        if args.get:
            command.getStatus(args)
        elif args.getAlarm:
            command.getAlarm(args)
        elif args.setAlarm:
            command.setAlarm(args)
        elif args.enableAlarm:
            command.enableAlarm(args)
        elif args.disableAlarm:
            command.disableAlarm(args)
        elif args.getCharge:
            command.getCharge(args)
        elif args.enableCharge:
            command.enableCharge(args)
        elif args.disableCharge:
            command.disableCharge(args)

    def firmware(self, args, pijuice):
        self.logger.debug(args.subparser_name)
        command = FirmwareCommand(pijuice, self.current_fw_version)
        if args.get:
            command.getFirmware(args)
        elif args.list:
            command.listFirmware(args)
        elif args.update:
            command.updateFirmware(args)

    def faults(self, args, pijuice):
        self.logger.debug(args.subparser_name)
        command = FaultCommand(pijuice)
        if args.get:
            command.getFaults(args)
        elif args.clear:
            command.clearFaults(args)

    def buttons(self, args, pijuice):
        self.logger.debug(args.subparser_name)
        command = ButtonsCommand(pijuice)
        if args.get:
            command.getButtons(args)
        elif args.setButton:
            command.setButton(args)

    def main(self):
        parser = argparse.ArgumentParser(description="pijuice control utility")
        parser.add_argument('-v', '--verbose', action="store_true", help="verbose output")
        subparsers = parser.add_subparsers(dest='subparser_name', title='commands')

        parser_bat = subparsers.add_parser('battery', help='battery configuration')
        parser_bat.set_defaults(func=self.battery)
        group_bat = parser_bat.add_mutually_exclusive_group(required=True)
        group_bat.add_argument('--get', action="store_true", help="get current battery config")
        group_bat.add_argument('--set', action="store_true", help="set battery profile")
        group_bat.add_argument('--list', action="store_true", help="list available battery profiles")
        parser_bat.add_argument('--profile', help="new  battery profile")

        parser_service = subparsers.add_parser('service', help='pijuice service configuration')
        parser_service.set_defaults(func=self.service)
        group_service = parser_service.add_mutually_exclusive_group(required=True)
        group_service.add_argument('--get', action="store_true", help="get service status")
        group_service.add_argument('--enable', action="store_true", help="enable the service")
        group_service.add_argument('--disable', action="store_true", help="disable the service")
        group_service.add_argument('--minCharge', action="store_true", help="min charge handling")
        parser_service.add_argument('--threshold', type=int, choices=range(0, 101), metavar="{0..100}", help="charge threshold %% (0 disables)")

        parser_events = subparsers.add_parser('events', help='event configuration')
        parser_events.set_defaults(func=self.events)
        group_events = parser_events.add_mutually_exclusive_group(required=True)
        group_events.add_argument('--get', action="store_true", help="get event status")
        group_events.add_argument('--enable', action="store_true", help="enable event")
        group_events.add_argument('--disable', action="store_true", help="disable event")
        parser_events.add_argument('--event', help="event name")
        parser_events.add_argument('--function', help="function  name")

        parser_function = subparsers.add_parser('functions', help='function configuration')
        parser_function.set_defaults(func=self.function)
        group_function = parser_function.add_mutually_exclusive_group(required=True)
        group_function.add_argument('--get', action="store_true", help="get functions")
        group_function.add_argument('--set', action="store_true", help="set user function")
        parser_function.add_argument('--nr', type=int, choices=range(1, len(pijuice_user_functions)), metavar="{1..15}", help="function nr.")
        parser_function.add_argument('--script', help="user script")
        parser_function.add_argument('--kind', choices=['all', 'sys', 'user', 'hard'], help="function kind")

        parser_rtc = subparsers.add_parser('rtc', help='real time clock configuration')
        parser_rtc.set_defaults(func=self.rtc)
        group_rtc = parser_rtc.add_mutually_exclusive_group(required=True)
        group_rtc.add_argument('--get', action="store_true", help="get current RTC")
        group_rtc.add_argument('--set', action="store_true", help="set device RTC to system time")

        parser_wakeup = subparsers.add_parser('wakeup', help='wakeup configuration')
        parser_wakeup.set_defaults(func=self.wakeup)
        group_wakeup = parser_wakeup.add_mutually_exclusive_group(required=True)
        group_wakeup.add_argument('--get', action="store_true", help="get wakeup status")
        group_wakeup.add_argument('--getAlarm', action="store_true", help="get alarm state")
        group_wakeup.add_argument('--setAlarm', action="store_true", help="get alarm state")
        group_wakeup.add_argument('--enableAlarm', action="store_true", help="enable alarm")
        group_wakeup.add_argument('--disableAlarm', action="store_true", help="disable alarm")
        group_wakeup.add_argument('--getCharge', action="store_true", help="get charge state")
        group_wakeup.add_argument('--enableCharge', action="store_true", help="enable wakeup on charge")
        group_wakeup.add_argument('--disableCharge', action="store_true", help="disable wakeup on charge")
        parser_wakeup.add_argument('--hour', type=int, choices=range(0, 24), metavar="{0..23}", help="alarm hour")
        parser_wakeup.add_argument('--minute', type=int, choices=range(0, 60), default=0, metavar="{0..59}", help="alarm minute")
        parser_wakeup.add_argument('--utc', action="store_true", help="treat alarm time as UTC instead of local time")
        parser_wakeup.add_argument('--chargeLevel', type=int, choices=range(10, 101), metavar="{10..100}", help="charge level in %%")

        parser_firmware = subparsers.add_parser('firmware', help='firmware configuration')
        parser_firmware.set_defaults(func=self.firmware)
        group_firmware = parser_firmware.add_mutually_exclusive_group(required=True)
        group_firmware.add_argument('--get', action="store_true", help="get current firmware")
        group_firmware.add_argument('--list', action="store_true", help="list available firmware files")
        group_firmware.add_argument('--update', action="store_true", help="update firmware")
        group_firmware_update = parser_firmware.add_mutually_exclusive_group()
        group_firmware_update.add_argument('--version', help="update to version")
        group_firmware_update.add_argument('--file', help="update firmware file")

        parser_faults = subparsers.add_parser('faults', help='faults status')
        parser_faults.set_defaults(func=self.faults)
        group_faults = parser_faults.add_mutually_exclusive_group(required=True)
        group_faults.add_argument('--get', action="store_true", help="get faults status")
        group_faults.add_argument('--clear', action="store_true", help="clear faults")

        parser_buttons = subparsers.add_parser('buttons', help='buttons status')
        parser_buttons.set_defaults(func=self.buttons)
        group_buttons = parser_buttons.add_mutually_exclusive_group(required=True)
        group_buttons.add_argument('--get', action="store_true", help="get button status")
        group_buttons.add_argument('--setButton', action="store_true", help="set button config")
        parser_buttons.add_argument('--nr', type=int, choices=range(1, len(PiJuiceConfig.buttons) + 1), help="button nr.")
        parser_buttons.add_argument('--event', choices=PiJuiceConfig.buttonEvents, help="event name")
        parser_buttons.add_argument('--function', help="function name")
        parser_buttons.add_argument('--parameter', type=int, choices=range(0, 10000), metavar="{0..10000}", help="function parameter in ms")

        args = parser.parse_args()
        if not 'func' in args:
            parser.error(message="no command")

        if args.verbose:
            consoleLevel = logging.DEBUG
        else:
            consoleLevel = logging.INFO
        logging.basicConfig(level=consoleLevel, format="%(levelname)-6s:%(message)s")

        try:
            self.logger.debug("### started ###")
            pijuice = PiJuice(1, 0x14)
            fc = FirmwareCommand(pijuice, None)
            self.current_fw_version = fc.get_current_fw_version()
            args.func(args, pijuice)
        except KeyboardInterrupt:
            self.logger.warn("aborted")
            return 2
        except: # pylint: disable=bare-except
            self.logger.exception("exception:")
            return 1
        finally:
            self.logger.debug("### finished ###")

if __name__ == '__main__':
    c = Control()
    sys.exit(c.main())
