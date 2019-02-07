import types
import weakref
import asyncio

__all__ = ['Event']


class Event:
    """
    Enable event passing between loosely coupled components.

    An event contains a list of callables (the listener slots) that are
    called in order when the event is emitted.
    """
    __slots__ = ('name', 'slots')

    def __init__(self, name=''):
        self.name = name
        self.slots = []  # list of [obj, weakref, func] sublists

    def connect(self, c, weakRef=True, hiPriority=False):
        """
        Connect a callable to this event.
        The ``+=`` operator can be used as a synonym for this method.

        Args:
            c: The callable to connect.
            weakRef:
                * True: The callable can be garbage collected
                  upon which it will be automatically disconnected from this
                  event
                * False: A strong reference to the callable will be kept
            hiPriority:
                * True: The callable will be placed in the first slot
                * False The callable will be placed last
        """
        if c in self:
            raise ValueError(f'Duplicate callback: {c}')

        obj, func = self._split(c)
        if weakRef and hasattr(obj, '__weakref__'):
            ref = weakref.ref(obj, self._onFinalize)
            obj = None
        else:
            ref = None
        slot = [obj, ref, func]
        if hiPriority:
            self.slots.insert(0, slot)
        else:
            self.slots.append(slot)
        return self

    def disconnect(self, c):
        """
        Disconnect a callable from this event.
        The ``-=`` operator can be used as a synonym for this method.

        Args:
            c: The callable to disconnect. It is valid if the callable is
                already not connected.
        """
        obj, func = self._split(c)
        for slot in self.slots:
            if (slot[0] is obj or slot[1] and slot[1]() is obj) \
                    and slot[2] is func:
                slot[0] = slot[1] = slot[2] = None
        self.slots = [s for s in self.slots if s != [None, None, None]]
        return self

    def emit(self, *args, **kwargs):
        """
        Call all slots in this event with the given arguments.
        """
        for obj, ref, func in self.slots:
            if ref:
                obj = ref()
            if obj is None:
                if func:
                    func(*args, **kwargs)
            else:
                if func:
                    func(obj, *args, **kwargs)
                else:
                    obj(*args, **kwargs)

    def clear(self):
        """
        Clear all slots.
        """
        for slot in self.slots:
            slot[0] = slot[1] = slot[2] = None
        self.slots = []

    @staticmethod
    def init(obj, eventNames):
        """
        Convenience function for initializing events as members
        of the given object.
        """
        for name in eventNames:
            setattr(obj, name, Event(name))

    async def wait(self):
        """
        Asynchronously await the next emit of this event and return
        the emitted data.

        The bare event can be used as synonym for this method.
        """
        def onEvent(*args):
            if not fut.done():
                fut.set_result(
                    args[0] if len(args) == 1 else args if args else None)

        fut = asyncio.Future()
        self += onEvent
        try:
            return await fut
        finally:
            self -= onEvent

    async def aiter(self, skipToLast: bool = False):
        """
        Create an asynchronous iterator that yields the emitted data
        from this event.

        The bare event can be used as synonym for this method.

        Args:
            skipToLast:
                * True: Backlogged events are skipped over to yield only
                  the last event.
                * False: All events are yielded.

        Example usage:

        .. code-block:: python

            async for trade, fill in ib.execDetailsEvent:
                print(fill)
        """
        def onEvent(*args):
            q.put_nowait(args)

        q = asyncio.Queue()
        self += onEvent
        try:
            while True:
                args = await q.get()
                if skipToLast:
                    while q.qsize():
                        args = q.get_nowait()
                yield args[0] if len(args) == 1 else args if args else None
        finally:
            self -= onEvent

    __iadd__ = connect
    __isub__ = disconnect
    __call__ = emit
    __aiter__ = aiter

    def __repr__(self):
        return f'Event<{self.name}, {self.slots}>'

    def __len__(self):
        return len(self.slots)

    def __await__(self):
        return self.wait().__await__()

    def __contains__(self, c):
        """
        See if callable is already connected.
        """
        obj, func = self._split(c)
        slots = [s for s in self.slots if s[2] is func]
        if obj is None:
            funcs = [s[2] for s in slots if s[0] is None and s[1] is None]
            return func in funcs
        else:
            objIds = set(id(s[0]) for s in slots if s[0] is not None)
            refdIds = set(id(s[1]()) for s in slots if s[1])
            return id(obj) in objIds | refdIds

    def _split(self, c):
        """
        Split given callable in (object, function) tuple.
        """
        if isinstance(c, types.FunctionType):
            t = (None, c)
        elif isinstance(c, types.MethodType):
            t = (c.__self__, c.__func__)
        elif isinstance(c, types.BuiltinMethodType):
            if type(c.__self__) is type:
                # built-in method
                t = (c.__self__, c)
            else:
                # built-in function
                t = (None, c)
        elif hasattr(c, '__call__'):
            t = (c, None)
        else:
            raise ValueError(f'Invalid callable: {c}')
        return t

    def _onFinalize(self, ref):
        for slot in self.slots:
            if slot[1] is ref:
                slot[0] = slot[1] = slot[2] = None
        self.slots = [s for s in self.slots if s != [None, None, None]]
