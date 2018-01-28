import os
import asyncio
import logging

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
    __slots__ = list(defaults) + ['_proc', '_logger']

    def __init__(self, *args, **kwargs):
        Object.__init__(self, *args, **kwargs)
        self._proc = None
        self._logger = logging.getLogger('ib_insync.IBController')
        util.syncAwait(self.start())
        asyncio.ensure_future(self.monitor())

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        self.stop()

    def stop(self):
        self._logger.info('Stopping')
        self._proc.terminate()
        self._proc = None

    async def start(self):
        self._logger.info('Starting')
        ext = 'bat' if os.sys.platform == 'win32' else 'sh'
        cmd = f'{self.IBC_PATH}/Scripts/DisplayBannerAndLaunch.{ext}'
        d = self.dict()
        if not d['TWS_CONFIG_PATH']:
            d['TWS_CONFIG_PATH'] = d['TWS_PATH']
        d = {k: os.path.expanduser(v) for k, v in d.items()}
        env = {**os.environ, **d}
        self._proc = await asyncio.create_subprocess_shell(cmd, env=env,
                stdout=asyncio.subprocess.PIPE)

    async def monitor(self):
        while self._proc:
            line = await self._proc.stdout.readline()
            if not line:
                break
            self._logger.info(line.strip().decode())
