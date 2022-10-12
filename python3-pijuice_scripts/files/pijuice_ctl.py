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

from pijuice import PiJuice

class CommandBase:
    def __init__(self, pijuice):
        self._pijuice = pijuice

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

class ServiceCommand(CommandBase):
    SERVICE_CTL = "/etc/init.d/pijuice"
    PID_FILE = '/tmp/pijuice_sys.pid'
    PiJuiceConfigDataPath = '/var/lib/pijuice/pijuice_config.JSON'

    def __init__(self, pijuice):
        super().__init__(pijuice)
        self.logger = logging.getLogger(self.__class__.__name__)

    def getService(self, args):
        status = subprocess.run([self.SERVICE_CTL, "enabled"])
        enabled = status.returncode == 0
        self.logger.info("service enabled:        %s" % enabled)
        status = subprocess.run([self.SERVICE_CTL, "running"])
        running = status.returncode == 0
        self.logger.info("service running:        %s" % running)
    
        configData = self.loadPiJuiceConfig()
        serviceEnabled = configData.get('system_task', {}).get('enabled')
        self.logger.info("service config enabled: %s" % serviceEnabled)

    def enableService(iself, args, enable):
        self.logger.info("enable service:     %s" % enable)

    def loadPiJuiceConfig(self):
        with open(self.PiJuiceConfigDataPath, 'r') as outputConfig:
            pijuiceConfigData = json.load(outputConfig)
            return pijuiceConfigData

    def savePiJuiceConfig(self, pijuiceConfigData):
        with open(self.PiJuiceConfigDataPath, 'w+') as outputConfig:
            json.dump(pijuiceConfigData, outputConfig, indent=2)
        ret = self.notify_service()
        if ret != 0:
            self.logger.error("failed to communicate with PiJuice service")
        else:
            self.logger.info("settings saved")

    def notify_service(self):
        ret = -1
        try:
            with open(self.PID_FILE, 'r') as r:
                pid = int(r.read())
                ret = os.system("kill -SIGHUP " + str(pid) + " > /dev/null 2>&1")
        except:
            pass
        return ret


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

    def _setAlarmEnable(self, enable):
        enableStr = "enable" if enable else "disable"
        self.logger.info("%s alarm" % enableStr)
        ret = self._pijuice.rtcAlarm.SetWakeupEnabled(enable)
        if ret['error'] != 'NO_ERROR':
            raise IOError("Unable to %s alarm: %s" % (enableStr, ret['error']))

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
            #status['day']['type'] = 0  # Day number
            if alarm['day'] == 'EVERY_DAY':
                #status['day']['every_day'] = True
                entries.append("every day")
            else:
                #status['day']['every_day'] = False
                #status['day']['value'] = alarm['day']
                entries.append("day of month: %s" % alarm['day'])
        elif 'weekday' in alarm:
            #status['day']['type'] = 1  # Day of week number
            if alarm['weekday'] == 'EVERY_DAY':
                #status['day']['every_day'] = True
                entries.append("every weekday")
            else:
                #status['day']['every_day'] = False
                #status['day']['value'] = alarm['weekday']
                entries.append("day of week: %s" % alarm['weekday'])

        if 'hour' in alarm:
            if alarm['hour'] == 'EVERY_HOUR':
                #status['hour']['every_hour'] = True
                entries.append("every hour")
            else:
                #status['hour']['every_hour'] = False
                #status['hour']['value'] = alarm['hour']
                entries.append("hour: %s" % alarm['hour'])

        if 'minute' in alarm:
            #status['minute']['type'] = 0  # Minute
            #status['minute']['value'] = alarm['minute']
            entries.append("minute: %s" % alarm['minute'])
        elif 'minute_period' in alarm:
            #status['minute']['type'] = 1  # Minute period
            #status['minute']['value'] = alarm['minute_period']
            entries.append("minute period: %s" % alarm['minute_period'])

        if 'second' in alarm:
            #status['second']['value'] = alarm['second']
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
        #if 'day' in alarm:
        #    status['day']['type'] = 0  # Day number
        #    if alarm['day'] == 'EVERY_DAY':
        #        status['day']['every_day'] = True
        #    else:
        #        status['day']['every_day'] = False
        #        status['day']['value'] = alarm['day']
        #elif 'weekday' in alarm:
        #    status['day']['type'] = 1  # Day of week number
        #    if alarm['weekday'] == 'EVERY_DAY':
        #        status['day']['every_day'] = True
        #    else:
        #        status['day']['every_day'] = False
        #        status['day']['value'] = alarm['weekday']
        #
        #if 'hour' in alarm:
        #    if alarm['hour'] == 'EVERY_HOUR':
        #        status['hour']['every_hour'] = True
        #    else:
        #        status['hour']['every_hour'] = False
        #        status['hour']['value'] = alarm['hour']
        #
        #if 'minute' in alarm:
        #    status['minute']['type'] = 0  # Minute
        #    status['minute']['value'] = alarm['minute']
        #elif 'minute_period' in alarm:
        #    status['minute']['type'] = 1  # Minute period
        #    status['minute']['value'] = alarm['minute_period']
        #
        #if 'second' in alarm:
        #    status['second']['value'] = alarm['second']

        return alarm

    def _setAlarm(self, alarm):
        status = self._pijuice.rtcAlarm.SetAlarm(alarm)
        if status['error'] != 'NO_ERROR':
            raise IOError("Unable to set alarm: %s" % alarm['error'])
        self.logger.info("alarm time set")

    def _formateDateTime(self, dt):
        dt_fmt = "%a %Y-%m-%d %H:%M:%S"
        timeStr = dt.strftime(dt_fmt)
        return timeStr


class Control:

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.current_fw_version = None

    def battery(self, args, pijuice):
        self.logger.debug(args.subparser_name)
        batteryCommand = BatteryCommand(pijuice, self.current_fw_version)
        if args.get:
            batteryCommand.getBattery(args)
        elif args.set:
            batteryCommand.setBattery(args)
        elif args.list:
            batteryCommand.listBattery(args)

    def service(self, args, pijuice):
        self.logger.debug(args.subparser_name)
        command = ServiceCommand(pijuice)
        if args.get:
            command.getService(args)
        elif args.enable:
            command.enableService(args, True)
        elif args.disable:
            command.enableService(args, False)

    def rtc(self, args, pijuice):
        self.logger.debug(args.subparser_name)
        command = RealTimeClockCommand(pijuice)
        if args.get:
            command.getRTC(args)
        elif args.set:
            command.setRTC(args)
        elif args.getAlarm:
            command.getAlarm(args)
        elif args.setAlarm:
            command.setAlarm(args)
        elif args.enableAlarm:
            command.enableAlarm(args)
        elif args.disableAlarm:
            command.disableAlarm(args)

    def firmware(self, args, pijuice):
        self.logger.debug(args.subparser_name)
        command = FirmwareCommand(pijuice, self.current_fw_version)
        if args.get:
            command.getFirmware(args)
        elif args.list:
            command.listFirmware(args)
        elif args.update:
            command.updateFirmware(args)

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

        parser_rtc = subparsers.add_parser('rtc', help='real time clock configuration')
        parser_rtc.set_defaults(func=self.rtc)
        group_rtc = parser_rtc.add_mutually_exclusive_group(required=True)
        group_rtc.add_argument('--get', action="store_true", help="get current RTC")
        group_rtc.add_argument('--set', action="store_true", help="set device RTC to system time")
        group_rtc.add_argument('--getAlarm', action="store_true", help="get alarm state")
        group_rtc.add_argument('--setAlarm', action="store_true", help="get alarm state")
        group_rtc.add_argument('--enableAlarm', action="store_true", help="enable alarm")
        group_rtc.add_argument('--disableAlarm', action="store_true", help="disable alarm")
        parser_rtc.add_argument('--hour', type=int, choices=range(0, 24), help="alarm hour")
        parser_rtc.add_argument('--minute', type=int, choices=range(0, 60), default=0, help="alarm minute")
        parser_rtc.add_argument('--utc', action="store_true", help="treat alarm time as UTC instead of local time")

        parser_firmware = subparsers.add_parser('firmware', help='firmware configuration')
        parser_firmware.set_defaults(func=self.firmware)
        group_firmware = parser_firmware.add_mutually_exclusive_group(required=True)
        group_firmware.add_argument('--get', action="store_true", help="get current firmware")
        group_firmware.add_argument('--list', action="store_true", help="list available firmware files")
        group_firmware.add_argument('--update', action="store_true", help="update firmware")
        group_firmware_update = parser_firmware.add_mutually_exclusive_group()
        group_firmware_update.add_argument('--version', help="update to version")
        group_firmware_update.add_argument('--file', help="update firmware file")

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
