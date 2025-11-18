from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Data(_message.Message):
    __slots__ = ("architecture", "end_point", "end_reason", "tb_informations", "tb_exec_orders", "mem_infos", "register_info", "faulted_datas", "mem_dump_infos", "mem_map_infos")
    ARCHITECTURE_FIELD_NUMBER: _ClassVar[int]
    END_POINT_FIELD_NUMBER: _ClassVar[int]
    END_REASON_FIELD_NUMBER: _ClassVar[int]
    TB_INFORMATIONS_FIELD_NUMBER: _ClassVar[int]
    TB_EXEC_ORDERS_FIELD_NUMBER: _ClassVar[int]
    MEM_INFOS_FIELD_NUMBER: _ClassVar[int]
    REGISTER_INFO_FIELD_NUMBER: _ClassVar[int]
    FAULTED_DATAS_FIELD_NUMBER: _ClassVar[int]
    MEM_DUMP_INFOS_FIELD_NUMBER: _ClassVar[int]
    MEM_MAP_INFOS_FIELD_NUMBER: _ClassVar[int]
    architecture: str
    end_point: int
    end_reason: str
    tb_informations: _containers.RepeatedCompositeFieldContainer[TbInformation]
    tb_exec_orders: _containers.RepeatedCompositeFieldContainer[TbExecOrder]
    mem_infos: _containers.RepeatedCompositeFieldContainer[MemInfo]
    register_info: RegisterInfo
    faulted_datas: _containers.RepeatedCompositeFieldContainer[FaultedData]
    mem_dump_infos: _containers.RepeatedCompositeFieldContainer[MemDumpInfo]
    mem_map_infos: _containers.RepeatedCompositeFieldContainer[MemMapInfo]
    def __init__(self, architecture: _Optional[str] = ..., end_point: _Optional[int] = ..., end_reason: _Optional[str] = ..., tb_informations: _Optional[_Iterable[_Union[TbInformation, _Mapping]]] = ..., tb_exec_orders: _Optional[_Iterable[_Union[TbExecOrder, _Mapping]]] = ..., mem_infos: _Optional[_Iterable[_Union[MemInfo, _Mapping]]] = ..., register_info: _Optional[_Union[RegisterInfo, _Mapping]] = ..., faulted_datas: _Optional[_Iterable[_Union[FaultedData, _Mapping]]] = ..., mem_dump_infos: _Optional[_Iterable[_Union[MemDumpInfo, _Mapping]]] = ..., mem_map_infos: _Optional[_Iterable[_Union[MemMapInfo, _Mapping]]] = ...) -> None: ...

class TbInformation(_message.Message):
    __slots__ = ("base_address", "size", "instruction_count", "num_of_exec", "assembler")
    BASE_ADDRESS_FIELD_NUMBER: _ClassVar[int]
    SIZE_FIELD_NUMBER: _ClassVar[int]
    INSTRUCTION_COUNT_FIELD_NUMBER: _ClassVar[int]
    NUM_OF_EXEC_FIELD_NUMBER: _ClassVar[int]
    ASSEMBLER_FIELD_NUMBER: _ClassVar[int]
    base_address: int
    size: int
    instruction_count: int
    num_of_exec: int
    assembler: str
    def __init__(self, base_address: _Optional[int] = ..., size: _Optional[int] = ..., instruction_count: _Optional[int] = ..., num_of_exec: _Optional[int] = ..., assembler: _Optional[str] = ...) -> None: ...

class TbExecOrder(_message.Message):
    __slots__ = ("tb_base_address", "pos")
    TB_BASE_ADDRESS_FIELD_NUMBER: _ClassVar[int]
    POS_FIELD_NUMBER: _ClassVar[int]
    tb_base_address: int
    pos: int
    def __init__(self, tb_base_address: _Optional[int] = ..., pos: _Optional[int] = ...) -> None: ...

class MemInfo(_message.Message):
    __slots__ = ("ins_address", "size", "memmory_address", "direction", "counter")
    INS_ADDRESS_FIELD_NUMBER: _ClassVar[int]
    SIZE_FIELD_NUMBER: _ClassVar[int]
    MEMMORY_ADDRESS_FIELD_NUMBER: _ClassVar[int]
    DIRECTION_FIELD_NUMBER: _ClassVar[int]
    COUNTER_FIELD_NUMBER: _ClassVar[int]
    ins_address: int
    size: int
    memmory_address: int
    direction: int
    counter: int
    def __init__(self, ins_address: _Optional[int] = ..., size: _Optional[int] = ..., memmory_address: _Optional[int] = ..., direction: _Optional[int] = ..., counter: _Optional[int] = ...) -> None: ...

class MemDumpInfo(_message.Message):
    __slots__ = ("address", "len", "dumps")
    ADDRESS_FIELD_NUMBER: _ClassVar[int]
    LEN_FIELD_NUMBER: _ClassVar[int]
    DUMPS_FIELD_NUMBER: _ClassVar[int]
    address: int
    len: int
    dumps: _containers.RepeatedCompositeFieldContainer[MemDump]
    def __init__(self, address: _Optional[int] = ..., len: _Optional[int] = ..., dumps: _Optional[_Iterable[_Union[MemDump, _Mapping]]] = ...) -> None: ...

class MemDump(_message.Message):
    __slots__ = ("mem",)
    MEM_FIELD_NUMBER: _ClassVar[int]
    mem: bytes
    def __init__(self, mem: _Optional[bytes] = ...) -> None: ...

class RegisterInfo(_message.Message):
    __slots__ = ("register_dumps", "arch_type")
    REGISTER_DUMPS_FIELD_NUMBER: _ClassVar[int]
    ARCH_TYPE_FIELD_NUMBER: _ClassVar[int]
    register_dumps: _containers.RepeatedCompositeFieldContainer[RegisterDump]
    arch_type: int
    def __init__(self, register_dumps: _Optional[_Iterable[_Union[RegisterDump, _Mapping]]] = ..., arch_type: _Optional[int] = ...) -> None: ...

class RegisterDump(_message.Message):
    __slots__ = ("register_values", "pc", "tb_count")
    REGISTER_VALUES_FIELD_NUMBER: _ClassVar[int]
    PC_FIELD_NUMBER: _ClassVar[int]
    TB_COUNT_FIELD_NUMBER: _ClassVar[int]
    register_values: _containers.RepeatedScalarFieldContainer[int]
    pc: int
    tb_count: int
    def __init__(self, register_values: _Optional[_Iterable[int]] = ..., pc: _Optional[int] = ..., tb_count: _Optional[int] = ...) -> None: ...

class FaultedData(_message.Message):
    __slots__ = ("trigger_address", "assembler")
    TRIGGER_ADDRESS_FIELD_NUMBER: _ClassVar[int]
    ASSEMBLER_FIELD_NUMBER: _ClassVar[int]
    trigger_address: int
    assembler: str
    def __init__(self, trigger_address: _Optional[int] = ..., assembler: _Optional[str] = ...) -> None: ...

class MemMapInfo(_message.Message):
    __slots__ = ("address", "size")
    ADDRESS_FIELD_NUMBER: _ClassVar[int]
    SIZE_FIELD_NUMBER: _ClassVar[int]
    address: int
    size: int
    def __init__(self, address: _Optional[int] = ..., size: _Optional[int] = ...) -> None: ...
