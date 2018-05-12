import types
import weakref

__all__ = ['Event']


class Event:
    """
    Enable event passing between loosely coupled compenents.
     
    An event contains a list of callables (the listener slots) that are
    called in order when the event is emitted.
    """
    __slots__ = ('name', 'slots')

    def __init__(self, name=''):
        self.name = name
        self.slots = []  # list of [obj, weakref, func] sublists

    def connect(self, c, weakRef=True, hiPriority=False):
        """
        Connect the callable c to this event.
        The ``+=`` operator can be used as a synonym for this method.
        
        When ``weakRef=True`` the callable can be garbage collected upon which
        it will be automatically disconnected from this event; 
        When ``weakRef=False`` a strong reference to the callable will be kept.

        With ``hiPriority=True`` the callable will be placed in the first slot,
        otherwise it will be placed last.
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
        Disconnect the callable from this event.
        The ``-=`` operator can be used as a synonym for this method.
        
        It's okay (i.e. not considered an error) if the callable is
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

    __iadd__ = connect
    __isub__ = disconnect
    __call__ = emit
            
    def __repr__(self):
        return f'Event<{self.name}, {self.slots}>'

    def __len__(self):
        return len(self.slots)

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
        if type(c) is types.FunctionType:
            t = (None, c)
        elif type(c) is types.MethodType:
            t = (c.__self__, c.__func__)
        elif type(c) is types.BuiltinMethodType:
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
