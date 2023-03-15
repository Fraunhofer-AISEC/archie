from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Fault(_message.Message):
    __slots__ = ["address", "lifespan", "mask_lower", "mask_upper", "model", "num_bytes", "trigger_address", "trigger_hitcounter", "type"]
    ADDRESS_FIELD_NUMBER: _ClassVar[int]
    LIFESPAN_FIELD_NUMBER: _ClassVar[int]
    MASK_LOWER_FIELD_NUMBER: _ClassVar[int]
    MASK_UPPER_FIELD_NUMBER: _ClassVar[int]
    MODEL_FIELD_NUMBER: _ClassVar[int]
    NUM_BYTES_FIELD_NUMBER: _ClassVar[int]
    TRIGGER_ADDRESS_FIELD_NUMBER: _ClassVar[int]
    TRIGGER_HITCOUNTER_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    address: int
    lifespan: int
    mask_lower: int
    mask_upper: int
    model: int
    num_bytes: int
    trigger_address: int
    trigger_hitcounter: int
    type: int
    def __init__(self, address: _Optional[int] = ..., type: _Optional[int] = ..., model: _Optional[int] = ..., lifespan: _Optional[int] = ..., trigger_address: _Optional[int] = ..., trigger_hitcounter: _Optional[int] = ..., mask_upper: _Optional[int] = ..., mask_lower: _Optional[int] = ..., num_bytes: _Optional[int] = ...) -> None: ...

class FaultPack(_message.Message):
    __slots__ = ["faults"]
    FAULTS_FIELD_NUMBER: _ClassVar[int]
    faults: _containers.RepeatedCompositeFieldContainer[Fault]
    def __init__(self, faults: _Optional[_Iterable[_Union[Fault, _Mapping]]] = ...) -> None: ...
