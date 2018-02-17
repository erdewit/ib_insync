import os
import asyncio
import logging
import configparser
from contextlib import suppress

from .objects import Object
import ib_insync.util as util

__all__ = ['IBController']


class IBController(Object):
    """
    Programmatic control over starting and stopping TWS/Gateway
    using IBController (https://github.com/ib-controller/ib-controller).
    
    On Windows the the proactor event loop must have been set:
    
    .. code-block:: python
        
        import asyncio
        asyncio.set_event_loop(asyncio.ProactorEventLoop())

    """
    defaults = dict(
        APP='TWS',  # 'TWS' or 'GATEWAY'
        TWS_MAJOR_VRSN='969',
        TRADING_MODE='live',  # 'live' or 'paper'
        IBC_INI='~/IBController/IBController.ini',
        IBC_PATH='~/IBController',
        TWS_PATH='~/Jts',
        LOG_PATH='~/IBController/Logs',
        TWSUSERID='',
        TWSPASSWORD='',
        JAVA_PATH='',
        TWS_CONFIG_PATH='')
    __slots__ = list(defaults) + ['_proc', '_logger', '_monitor']

    def __init__(self, *args, **kwargs):
        Object.__init__(self, *args, **kwargs)
        self._proc = None
        self._monitor = None
        self._logger = logging.getLogger('ib_insync.IBController')
        self.start()

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        self.stop()

    def start(self):
        """
        Launch TWS/IBG.
        """
        util.syncAwait(self.startAsync())

    def stop(self):
        """
        Cleanly shutdown TWS/IBG.
        """
        util.syncAwait(self.stopAsync())

    def terminate(self):
        """
        Terminate TWS/IBG.
        """
        util.syncAwait(self.terminateAsync())

    async def startAsync(self):
        if self._proc:
            return
        self._logger.info('Starting')

        # expand paths
        d = self.dict()
        for k, v in d.items():
            if k.endswith('_PATH') or k.endswith('_INI'):
                d[k] = os.path.expanduser(v)
        if not d['TWS_CONFIG_PATH']:
            d['TWS_CONFIG_PATH'] = d['TWS_PATH']
        self.update(**d)

        # run shell command
        ext = 'bat' if os.sys.platform == 'win32' else 'sh'
        cmd = f'{d["IBC_PATH"]}/Scripts/DisplayBannerAndLaunch.{ext}'
        env = {**os.environ, **d}
        self._proc = await asyncio.create_subprocess_shell(cmd, env=env,
                stdout=asyncio.subprocess.PIPE)
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
        with suppress(ProcessLookupError):
            self._proc.terminate()
            await self._proc.wait()
        self._proc = None
        self._monitor.cancel()
        self._monitor = None

    async def monitorAsync(self):
        while self._proc:
            line = await self._proc.stdout.readline()
            if not line:
                break
            self._logger.info(line.strip().decode())
