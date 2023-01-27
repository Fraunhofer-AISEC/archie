from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Fault(_message.Message):
    __slots__ = ("address", "type", "model", "lifespan", "trigger_address", "trigger_hitcounter", "mask_upper", "mask_lower", "num_bytes")
    ADDRESS_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    MODEL_FIELD_NUMBER: _ClassVar[int]
    LIFESPAN_FIELD_NUMBER: _ClassVar[int]
    TRIGGER_ADDRESS_FIELD_NUMBER: _ClassVar[int]
    TRIGGER_HITCOUNTER_FIELD_NUMBER: _ClassVar[int]
    MASK_UPPER_FIELD_NUMBER: _ClassVar[int]
    MASK_LOWER_FIELD_NUMBER: _ClassVar[int]
    NUM_BYTES_FIELD_NUMBER: _ClassVar[int]
    address: int
    type: int
    model: int
    lifespan: int
    trigger_address: int
    trigger_hitcounter: int
    mask_upper: int
    mask_lower: int
    num_bytes: int
    def __init__(self, address: _Optional[int] = ..., type: _Optional[int] = ..., model: _Optional[int] = ..., lifespan: _Optional[int] = ..., trigger_address: _Optional[int] = ..., trigger_hitcounter: _Optional[int] = ..., mask_upper: _Optional[int] = ..., mask_lower: _Optional[int] = ..., num_bytes: _Optional[int] = ...) -> None: ...

class FaultPack(_message.Message):
    __slots__ = ("faults",)
    FAULTS_FIELD_NUMBER: _ClassVar[int]
    faults: _containers.RepeatedCompositeFieldContainer[Fault]
    def __init__(self, faults: _Optional[_Iterable[_Union[Fault, _Mapping]]] = ...) -> None: ...
