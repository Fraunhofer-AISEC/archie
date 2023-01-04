from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Config(_message.Message):
    __slots__ = ["end_list", "exists_end", "exists_memory_dump", "exists_ring_buffer", "exists_start", "exists_tb_exec_list", "exists_tb_info", "max_duration", "mem_info", "memorydump", "num_faults", "num_memregions", "start_address", "start_counter", "tb_exec_list", "tb_exec_list_ring_buffer", "tb_info"]
    END_LIST_FIELD_NUMBER: _ClassVar[int]
    EXISTS_END_FIELD_NUMBER: _ClassVar[int]
    EXISTS_MEMORY_DUMP_FIELD_NUMBER: _ClassVar[int]
    EXISTS_RING_BUFFER_FIELD_NUMBER: _ClassVar[int]
    EXISTS_START_FIELD_NUMBER: _ClassVar[int]
    EXISTS_TB_EXEC_LIST_FIELD_NUMBER: _ClassVar[int]
    EXISTS_TB_INFO_FIELD_NUMBER: _ClassVar[int]
    MAX_DURATION_FIELD_NUMBER: _ClassVar[int]
    MEMORYDUMP_FIELD_NUMBER: _ClassVar[int]
    MEM_INFO_FIELD_NUMBER: _ClassVar[int]
    NUM_FAULTS_FIELD_NUMBER: _ClassVar[int]
    NUM_MEMREGIONS_FIELD_NUMBER: _ClassVar[int]
    START_ADDRESS_FIELD_NUMBER: _ClassVar[int]
    START_COUNTER_FIELD_NUMBER: _ClassVar[int]
    TB_EXEC_LIST_FIELD_NUMBER: _ClassVar[int]
    TB_EXEC_LIST_RING_BUFFER_FIELD_NUMBER: _ClassVar[int]
    TB_INFO_FIELD_NUMBER: _ClassVar[int]
    end_list: _containers.RepeatedCompositeFieldContainer[End]
    exists_end: bool
    exists_memory_dump: bool
    exists_ring_buffer: bool
    exists_start: bool
    exists_tb_exec_list: bool
    exists_tb_info: bool
    max_duration: int
    mem_info: bool
    memorydump: _containers.RepeatedCompositeFieldContainer[Memory_Region]
    num_faults: int
    num_memregions: int
    start_address: int
    start_counter: int
    tb_exec_list: bool
    tb_exec_list_ring_buffer: bool
    tb_info: bool
    def __init__(self, max_duration: _Optional[int] = ..., num_faults: _Optional[int] = ..., tb_exec_list: bool = ..., tb_info: bool = ..., mem_info: bool = ..., start_address: _Optional[int] = ..., start_counter: _Optional[int] = ..., end_list: _Optional[_Iterable[_Union[End, _Mapping]]] = ..., tb_exec_list_ring_buffer: bool = ..., num_memregions: _Optional[int] = ..., memorydump: _Optional[_Iterable[_Union[Memory_Region, _Mapping]]] = ..., exists_tb_exec_list: bool = ..., exists_tb_info: bool = ..., exists_start: bool = ..., exists_end: bool = ..., exists_memory_dump: bool = ..., exists_ring_buffer: bool = ...) -> None: ...

class End(_message.Message):
    __slots__ = ["address", "counter"]
    ADDRESS_FIELD_NUMBER: _ClassVar[int]
    COUNTER_FIELD_NUMBER: _ClassVar[int]
    address: int
    counter: int
    def __init__(self, address: _Optional[int] = ..., counter: _Optional[int] = ...) -> None: ...

class Memory_Region(_message.Message):
    __slots__ = ["address", "length"]
    ADDRESS_FIELD_NUMBER: _ClassVar[int]
    LENGTH_FIELD_NUMBER: _ClassVar[int]
    address: int
    length: int
    def __init__(self, address: _Optional[int] = ..., length: _Optional[int] = ...) -> None: ...
