from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Control(_message.Message):
    __slots__ = ["end_points", "has_ring_buffer", "has_start", "has_tb_exec_list", "has_tb_info", "max_duration", "mem_info", "memorydumps", "num_faults", "start_address", "start_counter", "tb_exec_list", "tb_exec_list_ring_buffer", "tb_info"]
    END_POINTS_FIELD_NUMBER: _ClassVar[int]
    HAS_RING_BUFFER_FIELD_NUMBER: _ClassVar[int]
    HAS_START_FIELD_NUMBER: _ClassVar[int]
    HAS_TB_EXEC_LIST_FIELD_NUMBER: _ClassVar[int]
    HAS_TB_INFO_FIELD_NUMBER: _ClassVar[int]
    MAX_DURATION_FIELD_NUMBER: _ClassVar[int]
    MEMORYDUMPS_FIELD_NUMBER: _ClassVar[int]
    MEM_INFO_FIELD_NUMBER: _ClassVar[int]
    NUM_FAULTS_FIELD_NUMBER: _ClassVar[int]
    START_ADDRESS_FIELD_NUMBER: _ClassVar[int]
    START_COUNTER_FIELD_NUMBER: _ClassVar[int]
    TB_EXEC_LIST_FIELD_NUMBER: _ClassVar[int]
    TB_EXEC_LIST_RING_BUFFER_FIELD_NUMBER: _ClassVar[int]
    TB_INFO_FIELD_NUMBER: _ClassVar[int]
    end_points: _containers.RepeatedCompositeFieldContainer[EndPoint]
    has_ring_buffer: bool
    has_start: bool
    has_tb_exec_list: bool
    has_tb_info: bool
    max_duration: int
    mem_info: bool
    memorydumps: _containers.RepeatedCompositeFieldContainer[MemoryDump]
    num_faults: int
    start_address: int
    start_counter: int
    tb_exec_list: bool
    tb_exec_list_ring_buffer: bool
    tb_info: bool
    def __init__(self, max_duration: _Optional[int] = ..., num_faults: _Optional[int] = ..., tb_exec_list: bool = ..., tb_info: bool = ..., mem_info: bool = ..., start_address: _Optional[int] = ..., start_counter: _Optional[int] = ..., end_points: _Optional[_Iterable[_Union[EndPoint, _Mapping]]] = ..., tb_exec_list_ring_buffer: bool = ..., memorydumps: _Optional[_Iterable[_Union[MemoryDump, _Mapping]]] = ..., has_tb_exec_list: bool = ..., has_tb_info: bool = ..., has_start: bool = ..., has_ring_buffer: bool = ...) -> None: ...

class EndPoint(_message.Message):
    __slots__ = ["address", "counter"]
    ADDRESS_FIELD_NUMBER: _ClassVar[int]
    COUNTER_FIELD_NUMBER: _ClassVar[int]
    address: int
    counter: int
    def __init__(self, address: _Optional[int] = ..., counter: _Optional[int] = ...) -> None: ...

class MemoryDump(_message.Message):
    __slots__ = ["address", "length"]
    ADDRESS_FIELD_NUMBER: _ClassVar[int]
    LENGTH_FIELD_NUMBER: _ClassVar[int]
    address: int
    length: int
    def __init__(self, address: _Optional[int] = ..., length: _Optional[int] = ...) -> None: ...
