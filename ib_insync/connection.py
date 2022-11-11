"""Event-driven socket connection."""

import asyncio

from eventkit import Event

from ib_insync.util import getLoop


class Connection(asyncio.Protocol):
    """
    Event-driven socket connection.

    Events:
        * ``hasData`` (data: bytes):
          Emits the received socket data.
        * ``disconnected`` (msg: str):
          Is emitted on socket disconnect, with an error message in case
          of error, or an empty string in case of a normal disconnect.
    """

    def __init__(self):
        self.hasData = Event('hasData')
        self.disconnected = Event('disconnected')
        self.reset()

    def reset(self):
        self.transport = None
        self.numBytesSent = 0
        self.numMsgSent = 0

    async def connectAsync(self, host, port):
        if self.transport:
            # wait until a previous connection is finished closing
            self.disconnect()
            await self.disconnected
        self.reset()
        loop = getLoop()
        self.transport, _ = await loop.create_connection(
            lambda: self, host, port)

    def disconnect(self):
        if self.transport:
            self.transport.write_eof()
            self.transport.close()

    def isConnected(self):
        return self.transport is not None

    def sendMsg(self, msg):
        if self.transport:
            self.transport.write(msg)
            self.numBytesSent += len(msg)
            self.numMsgSent += 1

    def connection_lost(self, exc):
        self.transport = None
        msg = str(exc) if exc else ''
        self.disconnected.emit(msg)

    def data_received(self, data):
        self.hasData.emit(data)
