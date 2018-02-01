import os
import asyncio
import logging
import configparser

from .objects import Object
import ib_insync.util as util

__all__ = ['IBController']


class IBController(Object):
    """
    Programmatic control over starting and stopping TWS/Gateway
    using IBController (https://github.com/ib-controller/ib-controller).
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
    __slots__ = list(defaults) + ['_proc', '_logger', '_controllerPort']

    def __init__(self, *args, **kwargs):
        Object.__init__(self, *args, **kwargs)
        self._proc = None
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
        self._logger.info('Terminating')
        self._proc.terminate()
        self._proc = None

    async def startAsync(self):
        self._logger.info('Starting')

        # expand paths
        d = self.dict()
        for k, v in d.items():
            if k.endswith('_PATH') or k.endswith('_INI'):
                d[k] = os.path.expanduser(v)
        if not d['TWS_CONFIG_PATH']:
            d['TWS_CONFIG_PATH'] = d['TWS_PATH']

        # read ibcontroller ini file to get controller port
        txt = '[section]' + open(d['IBC_INI']).read()
        config = configparser.ConfigParser()
        config.read_string(txt)
        self._controllerPort = config.getint('section', 'IbControllerPort')

        # run shell command
        ext = 'bat' if os.sys.platform == 'win32' else 'sh'
        cmd = f'{d["IBC_PATH"]}/Scripts/DisplayBannerAndLaunch.{ext}'
        env = {**os.environ, **d}
        self._proc = await asyncio.create_subprocess_shell(cmd, env=env,
                stdout=asyncio.subprocess.PIPE)
        asyncio.ensure_future(self.monitorAsync())

    async def stopAsync(self):
        self._logger.info('Stopping')
        _reader, writer = await asyncio.open_connection(
                '127.0.0.1', self._controllerPort)
        writer.write(b'STOP')
        await writer.drain()
        writer.close()
        self._proc = None

    async def monitorAsync(self):
        while self._proc:
            line = await self._proc.stdout.readline()
            if not line:
                break
            self._logger.info(line.strip().decode())
