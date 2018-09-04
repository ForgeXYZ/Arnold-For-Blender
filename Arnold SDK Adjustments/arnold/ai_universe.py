
from ctypes import *
from .arnold_common import ai, NullToNone
from .ai_bbox import *
from .ai_types import *

from arnold import ai_nodes

# Cache types
#
AI_CACHE_TEXTURE      = 0x0001  ## Flushes all texturemaps
AI_CACHE_BACKGROUND   = 0x0002  ## Flushes all skydome importance tables for background
AI_CACHE_QUAD         = 0x0004  ## Flushes all quad lights importance tables
AI_CACHE_ALL          = 0xFFFF  ## Flushes all cache types simultaneously

class AtUniverse(Structure):
    pass

class AtNodeIterator(Structure):
    pass

class AtNodeEntryIterator(Structure):
    pass

class AtAOVIterator(Structure):
    pass

class AtAOVEntry(Structure):
    _fields_ = [("name", AtStringStruct),
                ("type", c_ubyte),
                ("blend_mode", c_int),
                ("expression", AtStringStruct)]

_AiUniverse = ai.AiUniverse
_AiUniverse.restype = c_void_p

def AiUniverse():
    return NullToNone(_AiUniverse(), POINTER(AtUniverse))

AiUniverseDestroy = ai.AiUniverseDestroy
AiUniverseDestroy.argtypes = [POINTER(AtUniverse)]

AiUniverseIsActive = ai.AiUniverseIsActive
AiUniverseIsActive.restype = c_bool

def _AiUniverseCacheFlush(universe, flags):
    func = ai.AiUniverseCacheFlush
    func.argtypes = [POINTER(AtUniverse), c_int]

    func(universe, flags)

def AiUniverseCacheFlush(*args):
    _AiUniverseCacheFlush(*args) if args[0] is None or type(args[0]) == POINTER(AtUniverse) else _AiUniverseCacheFlush(None, *args)

def _AiUniverseGetOptions(universe):
    func = ai.AiUniverseGetOptions
    func.argtypes = [POINTER(AtUniverse)]
    func.restype = c_void_p

    return NullToNone(func(universe), POINTER(ai_nodes.AtNode))

def AiUniverseGetOptions(*args):
    return _AiUniverseGetOptions(*args) if len(args) > 0 else _AiUniverseGetOptions(None)

def _AiUniverseGetCamera(universe):
    func = ai.AiUniverseGetCamera
    func.argtypes = [POINTER(AtUniverse)]
    func.restype = c_void_p

    return NullToNone(func(universe), POINTER(ai_nodes.AtNode))

def AiUniverseGetCamera(*args):
    return _AiUniverseGetCamera(*args) if len(args) > 0 else _AiUniverseGetCamera(None)

def _AiUniverseGetSceneBounds(universe):
    func = ai.AiUniverseGetSceneBounds
    func.argtypes = [POINTER(AtUniverse)]
    func.restype = AtBBox

    return func(universe)

def AiUniverseGetSceneBounds(*args):
    return _AiUniverseGetSceneBounds(*args) if len(args) > 0 else _AiUniverseGetSceneBounds(None)

def _AiUniverseGetNodeIterator(universe, mask):
    func = ai.AiUniverseGetNodeIterator
    func.argtypes = [POINTER(AtUniverse), c_uint]
    func.restype = c_void_p

    return NullToNone(func(universe, mask), POINTER(AtNodeIterator))

def AiUniverseGetNodeIterator(*args):
    return _AiUniverseGetNodeIterator(*args) if args[0] is None or type(args[0]) == POINTER(AtUniverse) else _AiUniverseGetNodeIterator(None, *args)

_AiUniverseGetNodeEntryIterator = ai.AiUniverseGetNodeEntryIterator
_AiUniverseGetNodeEntryIterator.argtypes = [c_uint]
_AiUniverseGetNodeEntryIterator.restype = c_void_p

def AiUniverseGetNodeEntryIterator(mask):
    return NullToNone(_AiUniverseGetNodeEntryIterator(mask), POINTER(AtNodeEntryIterator))

_AiUniverseGetAOVIterator = ai.AiUniverseGetAOVIterator
_AiUniverseGetAOVIterator.argtypes = []
_AiUniverseGetAOVIterator.restype = c_void_p

def AiUniverseGetAOVIterator():
    return NullToNone(_AiUniverseGetAOVIterator(), POINTER(AtAOVIterator))

AiNodeIteratorDestroy = ai.AiNodeIteratorDestroy
AiNodeIteratorDestroy.argtypes = [POINTER(AtNodeIterator)]

_AiNodeIteratorGetNext = ai.AiNodeIteratorGetNext
_AiNodeIteratorGetNext.argtypes = [POINTER(AtNodeIterator)]
_AiNodeIteratorGetNext.restype = c_void_p

def AiNodeIteratorGetNext(iter):
    return NullToNone(_AiNodeIteratorGetNext(iter), POINTER(ai_nodes.AtNode))

AiNodeIteratorFinished = ai.AiNodeIteratorFinished
AiNodeIteratorFinished.argtypes = [POINTER(AtNodeIterator)]
AiNodeIteratorFinished.restype = c_bool

AiNodeEntryIteratorDestroy = ai.AiNodeEntryIteratorDestroy
AiNodeEntryIteratorDestroy.argtypes = [POINTER(AtNodeEntryIterator)]

_AiNodeEntryIteratorGetNext = ai.AiNodeEntryIteratorGetNext
_AiNodeEntryIteratorGetNext.argtypes = [POINTER(AtNodeEntryIterator)]
_AiNodeEntryIteratorGetNext.restype = c_void_p

def AiNodeEntryIteratorGetNext(iter):
    return NullToNone(_AiNodeEntryIteratorGetNext(iter), POINTER(ai_nodes.AtNodeEntry))

AiNodeEntryIteratorFinished = ai.AiNodeEntryIteratorFinished
AiNodeEntryIteratorFinished.argtypes = [POINTER(AtNodeEntryIterator)]
AiNodeEntryIteratorFinished.restype = c_bool

AiAOVIteratorDestroy = ai.AiAOVIteratorDestroy
AiAOVIteratorDestroy.argtypes = [POINTER(AtAOVIterator)]

_AiAOVIteratorGetNext = ai.AiAOVIteratorGetNext
_AiAOVIteratorGetNext.argtypes = [POINTER(AtAOVIterator)]
_AiAOVIteratorGetNext.restype = c_void_p

def AiAOVIteratorGetNext(iter):
    return NullToNone(_AiAOVIteratorGetNext(iter), POINTER(AtAOVEntry))

AiAOVIteratorFinished = ai.AiAOVIteratorFinished
AiAOVIteratorFinished.argtypes = [POINTER(AtAOVIterator)]
AiAOVIteratorFinished.restype = c_bool

AiTextureInvalidate = ai.AiTextureInvalidate
AiTextureInvalidate.argtypes = [AtPythonString]
