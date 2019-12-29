"""Event-driven socket connection."""

import asyncio


class Connection(asyncio.Protocol):
    """Socket connection."""

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.transport = None
        self.numBytesSent = 0
        self.numMsgSent = 0

        # the following are callbacks for socket events:
        self.disconnected = None
        self.hasError = None
        self.hasData = None

    async def connectAsync(self):
        loop = asyncio.get_event_loop()
        self.transport, _ = await loop.create_connection(
            lambda: self, self.host, self.port)

    def disconnect(self):
        if self.transport:
            self.transport.close()
            self.transport = None

    def isConnected(self):
        return self.transport is not None

    def sendMsg(self, msg):
        self.transport.write(msg)
        self.numBytesSent += len(msg)
        self.numMsgSent += 1

    def connection_lost(self, exc):
        if exc:
            self.hasError(str(exc))
        else:
            self.disconnected()

    def data_received(self, data):
        self.hasData(data)
