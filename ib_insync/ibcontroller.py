"""Programmatic control over the TWS/gateway client software."""

import asyncio
import configparser
import logging
import os
from contextlib import suppress
from dataclasses import dataclass
from typing import ClassVar, Union

from eventkit import Event

import ib_insync.util as util
from ib_insync.contract import Forex
from ib_insync.ib import IB

__all__ = ['IBC', 'IBController', 'Watchdog']


@dataclass
class IBC:
    r"""
    Programmatic control over starting and stopping TWS/Gateway
    using IBC (https://github.com/IbcAlpha/IBC).

    Args:
        twsVersion (int): (required) The major version number for
            TWS or gateway.
        gateway (bool):
            * True = gateway
            * False = TWS
        tradingMode (str): 'live' or 'paper'.
        userid (str): IB account username. It is recommended to set the real
            username/password in a secured IBC config file.
        password (str): IB account password.
        twsPath (str): Path to the TWS installation folder.
            Defaults:

            * Linux:    ~/Jts
            * OS X:     ~/Applications
            * Windows:  C:\\Jts
        twsSettingsPath (str): Path to the TWS settings folder.
            Defaults:

            * Linux:     ~/Jts
            * OS X:      ~/Jts
            * Windows:   Not available
        ibcPath (str): Path to the IBC installation folder.
            Defaults:

            * Linux:     /opt/ibc
            * OS X:      /opt/ibc
            * Windows:   C:\\IBC
        ibcIni (str): Path to the IBC configuration file.
            Defaults:

            * Linux:     ~/ibc/config.ini
            * OS X:      ~/ibc/config.ini
            * Windows:   %%HOMEPATH%%\\Documents\IBC\\config.ini
        javaPath (str): Path to Java executable.
            Default is to use the Java VM included with TWS/gateway.
        fixuserid (str): FIX account user id (gateway only).
        fixpassword (str): FIX account password (gateway only).

    This is not intended to be run in a notebook.

    To use IBC on Windows, the proactor (or quamash) event loop
    must have been set:

    .. code-block:: python

        import asyncio
        asyncio.set_event_loop(asyncio.ProactorEventLoop())

    Example usage:

    .. code-block:: python

        ibc = IBC(976, gateway=True, tradingMode='live',
            userid='edemo', password='demouser')
        ibc.start()
        IB.run()
    """

    IbcLogLevel: ClassVar = logging.DEBUG

    twsVersion: int = 0
    gateway: bool = False
    tradingMode: str = ''
    twsPath: str = ''
    twsSettingsPath: str = ''
    ibcPath: str = ''
    ibcIni: str = ''
    javaPath: str = ''
    userid: str = ''
    password: str = ''
    fixuserid: str = ''
    fixpassword: str = ''

    def __post_init__(self):
        self._isWindows = os.sys.platform == 'win32'
        if not self.ibcPath:
            self.ibcPath = '/opt/ibc' if not self._isWindows else 'C:\\IBC'
        self._proc = None
        self._monitor = None
        self._logger = logging.getLogger('ib_insync.IBC')

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *_exc):
        self.terminate()

    def start(self):
        """Launch TWS/IBG."""
        util.run(self.startAsync())

    def terminate(self):
        """Terminate TWS/IBG."""
        util.run(self.terminateAsync())

    async def startAsync(self):
        if self._proc:
            return
        self._logger.info('Starting')

        # map from field names to cmd arguments; key=(UnixArg, WindowsArg)
        args = dict(
            twsVersion=('', ''),
            gateway=('--gateway', '/Gateway'),
            tradingMode=('--mode=', '/Mode:'),
            twsPath=('--tws-path=', '/TwsPath:'),
            twsSettingsPath=('--tws-settings-path=', ''),
            ibcPath=('--ibc-path=', '/IbcPath:'),
            ibcIni=('--ibc-ini=', '/Config:'),
            javaPath=('--java-path=', '/JavaPath:'),
            userid=('--user=', '/User:'),
            password=('--pw=', '/PW:'),
            fixuserid=('--fix-user=', '/FIXUser:'),
            fixpassword=('--fix-pw=', '/FIXPW:'))

        # create shell command
        cmd = [
            f'{self.ibcPath}\\scripts\\StartIBC.bat' if self._isWindows else
            f'{self.ibcPath}/scripts/ibcstart.sh']
        for k, v in util.dataclassAsDict(self).items():
            arg = args[k][self._isWindows]
            if v:
                if arg.endswith('=') or arg.endswith(':'):
                    cmd.append(f'{arg}{v}')
                elif arg:
                    cmd.append(arg)
                else:
                    cmd.append(str(v))

        # run shell command
        self._proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE)
        self._monitor = asyncio.ensure_future(self.monitorAsync())

    async def terminateAsync(self):
        if not self._proc:
            return
        self._logger.info('Terminating')
        if self._monitor:
            self._monitor.cancel()
            self._monitor = None
        if self._isWindows:
            import subprocess
            subprocess.call(
                ['taskkill', '/F', '/T', '/PID', str(self._proc.pid)])
        else:
            with suppress(ProcessLookupError):
                self._proc.terminate()
                await self._proc.wait()
        self._proc = None

    async def monitorAsync(self):
        while self._proc:
            line = await self._proc.stdout.readline()
            if not line:
                break
            self._logger.log(IBC.IbcLogLevel, line.strip().decode())


@dataclass
class IBController:
    """
    For new installations it is recommended to use IBC instead.

    Programmatic control over starting and stopping TWS/Gateway
    using IBController (https://github.com/ib-controller/ib-controller).

    On Windows the the proactor (or quamash) event loop must have been set:

    .. code-block:: python

        import asyncio
        asyncio.set_event_loop(asyncio.ProactorEventLoop())

    This is not intended to be run in a notebook.
    """

    APP: str = 'TWS'  # 'TWS' or 'GATEWAY'
    TWS_MAJOR_VRSN: str = '969'
    TRADING_MODE: str = 'live'  # 'live' or 'paper'
    IBC_INI: str = '~/IBController/IBController.ini'
    IBC_PATH: str = '~/IBController'
    TWS_PATH: str = '~/Jts'
    LOG_PATH: str = '~/IBController/Logs'
    TWSUSERID: str = ''
    TWSPASSWORD: str = ''
    JAVA_PATH: str = ''
    TWS_CONFIG_PATH: str = ''

    def __post_init__(self):
        self._proc = None
        self._monitor = None
        self._logger = logging.getLogger('ib_insync.IBController')

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *_exc):
        self.terminate()

    def start(self):
        """Launch TWS/IBG."""
        util.run(self.startAsync())

    def stop(self):
        """Cleanly shutdown TWS/IBG."""
        util.run(self.stopAsync())

    def terminate(self):
        """Terminate TWS/IBG."""
        util.run(self.terminateAsync())

    async def startAsync(self):
        if self._proc:
            return
        self._logger.info('Starting')

        # expand paths
        d = util.dataclassAsDict(self)
        for k, v in d.items():
            if k.endswith('_PATH') or k.endswith('_INI'):
                d[k] = os.path.expanduser(v)
        if not d['TWS_CONFIG_PATH']:
            d['TWS_CONFIG_PATH'] = d['TWS_PATH']
        self.__dict__.update(**d)

        # run shell command
        ext = 'bat' if os.sys.platform == 'win32' else 'sh'
        cmd = f'{d["IBC_PATH"]}/Scripts/DisplayBannerAndLaunch.{ext}'
        env = {**os.environ, **d}
        self._proc = await asyncio.create_subprocess_exec(
            cmd, env=env, stdout=asyncio.subprocess.PIPE)
        self._monitor = asyncio.ensure_future(self.monitorAsync())

    async def stopAsync(self):
        if not self._proc:
            return
        self._logger.info('Stopping')

        # read ibcontroller ini file to get controller port
        txt = '[section]' + open(self.IBC_INI).read()
        config = configparser.ConfigParser()
        config.read_string(txt)
        contrPort = config.getint('section', 'IbControllerPort')

        _reader, writer = await asyncio.open_connection('127.0.0.1', contrPort)
        writer.write(b'STOP')
        await writer.drain()
        writer.close()
        await self._proc.wait()
        self._proc = None
        self._monitor.cancel()
        self._monitor = None

    async def terminateAsync(self):
        if not self._proc:
            return
        self._logger.info('Terminating')
        self._monitor.cancel()
        self._monitor = None
        with suppress(ProcessLookupError):
            self._proc.terminate()
            await self._proc.wait()
        self._proc = None

    async def monitorAsync(self):
        while self._proc:
            line = await self._proc.stdout.readline()
            if not line:
                break
            self._logger.info(line.strip().decode())


@dataclass
class Watchdog:
    """
    Start, connect and watch over the TWS or gateway app and try to keep it
    up and running. It is intended to be used in an event-driven
    application that properly initializes itself upon (re-)connect.

    It is not intended to be used in a notebook or in imperative-style code.
    Do not expect Watchdog to magically shield you from reality. Do not use
    Watchdog unless you understand what it does and doesn't do.

    Args:
        controller (Union[IBC, IBController]): (required) IBC or IBController
            instance.
        ib (IB): (required) IB instance to be used. Do no connect this
            instance as Watchdog takes care of that.
        host (str): Used for connecting IB instance.
        port (int):  Used for connecting IB instance.
        clientId (int):  Used for connecting IB instance.
        connectTimeout (float):  Used for connecting IB instance.
        readonly (bool): Used for connecting IB instance.
        appStartupTime (float): Time (in seconds) that the app is given
            to start up. Make sure that it is given ample time.
        appTimeout (float): Timeout (in seconds) for network traffic idle time.
        retryDelay (float): Time (in seconds) to restart app after a
            previous failure.

    The idea is to wait until there is no traffic coming from the app for
    a certain amount of time (the ``appTimeout`` parameter). This triggers
    a historical request to be placed just to see if the app is still alive
    and well. If yes, then continue, if no then restart the whole app
    and reconnect. Restarting will also occur directly on errors 1100 and 100.

    Example usage:

    .. code-block:: python

        def onConnected():
            print(ib.accountValues())

        ibc = IBC(974, gateway=True, tradingMode='paper')
        ib = IB()
        ib.connectedEvent += onConnected
        watchdog = Watchdog(ibc, ib, port=4002)
        watchdog.start()
        ib.run()

    Events:
        * ``startingEvent`` (watchdog: :class:`.Watchdog`)
        * ``startedEvent`` (watchdog: :class:`.Watchdog`)
        * ``stoppingEvent`` (watchdog: :class:`.Watchdog`)
        * ``stoppedEvent`` (watchdog: :class:`.Watchdog`)
        * ``softTimeoutEvent`` (watchdog: :class:`.Watchdog`)
        * ``hardTimeoutEvent`` (watchdog: :class:`.Watchdog`)
    """

    events = [
        'startingEvent', 'startedEvent', 'stoppingEvent', 'stoppedEvent',
        'softTimeoutEvent', 'hardTimeoutEvent']

    controller: Union[IBC, IBController]
    ib: IB
    host: str = '127.0.0.1'
    port: int = 7497
    clientId: int = 1
    connectTimeout: float = 2
    appStartupTime: float = 30
    appTimeout: float = 20
    retryDelay: float = 2
    readonly: bool = False

    def __post_init__(self):
        self.startingEvent = Event('startingEvent')
        self.startedEvent = Event('startedEvent')
        self.stoppingEvent = Event('stoppingEvent')
        self.stoppedEvent = Event('stoppedEvent')
        self.softTimeoutEvent = Event('softTimeoutEvent')
        self.hardTimeoutEvent = Event('hardTimeoutEvent')
        if not self.controller:
            raise ValueError('No controller supplied')
        if not self.ib:
            raise ValueError('No IB instance supplied')
        if self.ib.isConnected():
            raise ValueError('IB instance must not be connected')
        assert 0 < self.appTimeout < 60
        assert self.retryDelay > 0
        self._runner = None
        self._logger = logging.getLogger('ib_insync.Watchdog')

    def start(self):
        self._logger.info('Starting')
        self.startingEvent.emit(self)
        self._runner = asyncio.ensure_future(self.runAsync())

    async def runForeverAsync(self):
        start()
        await self._runner

    def stop(self):
        self._logger.info('Stopping')
        self.stoppingEvent.emit(self)
        self.ib.disconnect()
        self._runner = None

    async def runAsync(self):

        def onTimeout(idlePeriod):
            if not waiter.done():
                waiter.set_result(None)

        def onError(reqId, errorCode, errorString, contract):
            if errorCode in [1100, 100] and not waiter.done():
                waiter.set_exception(Warning(f'Error {errorCode}'))

        def onDisconnected():
            if not waiter.done():
                waiter.set_exception(Warning('Disconnected'))

        while self._runner:
            try:
                await self.controller.startAsync()
                await asyncio.sleep(self.appStartupTime)
                await self.ib.connectAsync(
                    self.host, self.port, self.clientId, self.connectTimeout,
                    self.readonly)
                self.startedEvent.emit(self)
                self.ib.setTimeout(self.appTimeout)
                self.ib.timeoutEvent += onTimeout
                self.ib.errorEvent += onError
                self.ib.disconnectedEvent += onDisconnected

                while self._runner:
                    waiter = asyncio.Future()
                    await waiter
                    # soft timeout, probe the app with a historical request
                    self._logger.debug('Soft timeout')
                    self.softTimeoutEvent.emit(self)
                    probe = self.ib.reqHistoricalDataAsync(
                        Forex('EURUSD'), '', '30 S', '5 secs',
                        'MIDPOINT', False)
                    bars = None
                    with suppress(asyncio.TimeoutError):
                        bars = await asyncio.wait_for(probe, 4)
                    if not bars:
                        self.hardTimeoutEvent.emit(self)
                        raise Warning('Hard timeout')
                    self.ib.setTimeout(self.appTimeout)

            except ConnectionRefusedError:
                pass
            except Warning as w:
                self._logger.warning(w)
            except Exception as e:
                self._logger.exception(e)
            finally:
                self.ib.timeoutEvent -= onTimeout
                self.ib.errorEvent -= onError
                self.ib.disconnectedEvent -= onDisconnected
                await self.controller.terminateAsync()
                self.stoppedEvent.emit(self)
                if self._runner:
                    await asyncio.sleep(self.retryDelay)


if __name__ == '__main__':
    asyncio.get_event_loop().set_debug(True)
    util.logToConsole(logging.DEBUG)
    ibc = IBC(976, gateway=True, tradingMode='paper')
#             userid='edemo', password='demouser')
    ib = IB()
    app = Watchdog(ibc, ib, port=4002, appStartupTime=15, appTimeout=10)
    app.start()
    IB.run()
