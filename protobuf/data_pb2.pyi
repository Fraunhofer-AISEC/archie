from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Data(_message.Message):
    __slots__ = ["end_point", "end_reason", "faulted_datas", "mem_dump_infos", "mem_infos", "register_info", "tb_exec_orders", "tb_informations"]
    END_POINT_FIELD_NUMBER: _ClassVar[int]
    END_REASON_FIELD_NUMBER: _ClassVar[int]
    FAULTED_DATAS_FIELD_NUMBER: _ClassVar[int]
    MEM_DUMP_INFOS_FIELD_NUMBER: _ClassVar[int]
    MEM_INFOS_FIELD_NUMBER: _ClassVar[int]
    REGISTER_INFO_FIELD_NUMBER: _ClassVar[int]
    TB_EXEC_ORDERS_FIELD_NUMBER: _ClassVar[int]
    TB_INFORMATIONS_FIELD_NUMBER: _ClassVar[int]
    end_point: int
    end_reason: str
    faulted_datas: _containers.RepeatedCompositeFieldContainer[FaultedData]
    mem_dump_infos: _containers.RepeatedCompositeFieldContainer[MemDumpInfo]
    mem_infos: _containers.RepeatedCompositeFieldContainer[MemInfo]
    register_info: RegisterInfo
    tb_exec_orders: _containers.RepeatedCompositeFieldContainer[TbExecOrder]
    tb_informations: _containers.RepeatedCompositeFieldContainer[TbInformation]
    def __init__(self, end_point: _Optional[int] = ..., end_reason: _Optional[str] = ..., tb_informations: _Optional[_Iterable[_Union[TbInformation, _Mapping]]] = ..., tb_exec_orders: _Optional[_Iterable[_Union[TbExecOrder, _Mapping]]] = ..., mem_infos: _Optional[_Iterable[_Union[MemInfo, _Mapping]]] = ..., register_info: _Optional[_Union[RegisterInfo, _Mapping]] = ..., faulted_datas: _Optional[_Iterable[_Union[FaultedData, _Mapping]]] = ..., mem_dump_infos: _Optional[_Iterable[_Union[MemDumpInfo, _Mapping]]] = ...) -> None: ...

class FaultedData(_message.Message):
    __slots__ = ["assembler", "trigger_address"]
    ASSEMBLER_FIELD_NUMBER: _ClassVar[int]
    TRIGGER_ADDRESS_FIELD_NUMBER: _ClassVar[int]
    assembler: str
    trigger_address: int
    def __init__(self, trigger_address: _Optional[int] = ..., assembler: _Optional[str] = ...) -> None: ...

class MemDump(_message.Message):
    __slots__ = ["mem"]
    MEM_FIELD_NUMBER: _ClassVar[int]
    mem: bytes
    def __init__(self, mem: _Optional[bytes] = ...) -> None: ...

class MemDumpInfo(_message.Message):
    __slots__ = ["address", "dumps", "len"]
    ADDRESS_FIELD_NUMBER: _ClassVar[int]
    DUMPS_FIELD_NUMBER: _ClassVar[int]
    LEN_FIELD_NUMBER: _ClassVar[int]
    address: int
    dumps: _containers.RepeatedCompositeFieldContainer[MemDump]
    len: int
    def __init__(self, address: _Optional[int] = ..., len: _Optional[int] = ..., dumps: _Optional[_Iterable[_Union[MemDump, _Mapping]]] = ...) -> None: ...

class MemInfo(_message.Message):
    __slots__ = ["counter", "direction", "ins_address", "memmory_address", "size"]
    COUNTER_FIELD_NUMBER: _ClassVar[int]
    DIRECTION_FIELD_NUMBER: _ClassVar[int]
    INS_ADDRESS_FIELD_NUMBER: _ClassVar[int]
    MEMMORY_ADDRESS_FIELD_NUMBER: _ClassVar[int]
    SIZE_FIELD_NUMBER: _ClassVar[int]
    counter: int
    direction: int
    ins_address: int
    memmory_address: int
    size: int
    def __init__(self, ins_address: _Optional[int] = ..., size: _Optional[int] = ..., memmory_address: _Optional[int] = ..., direction: _Optional[int] = ..., counter: _Optional[int] = ...) -> None: ...

class RegisterDump(_message.Message):
    __slots__ = ["pc", "register_values", "tb_count"]
    PC_FIELD_NUMBER: _ClassVar[int]
    REGISTER_VALUES_FIELD_NUMBER: _ClassVar[int]
    TB_COUNT_FIELD_NUMBER: _ClassVar[int]
    pc: int
    register_values: _containers.RepeatedScalarFieldContainer[int]
    tb_count: int
    def __init__(self, register_values: _Optional[_Iterable[int]] = ..., pc: _Optional[int] = ..., tb_count: _Optional[int] = ...) -> None: ...

class RegisterInfo(_message.Message):
    __slots__ = ["arch_type", "register_dumps"]
    ARCH_TYPE_FIELD_NUMBER: _ClassVar[int]
    REGISTER_DUMPS_FIELD_NUMBER: _ClassVar[int]
    arch_type: int
    register_dumps: _containers.RepeatedCompositeFieldContainer[RegisterDump]
    def __init__(self, register_dumps: _Optional[_Iterable[_Union[RegisterDump, _Mapping]]] = ..., arch_type: _Optional[int] = ...) -> None: ...

class TbExecOrder(_message.Message):
    __slots__ = ["pos", "tb_base_address"]
    POS_FIELD_NUMBER: _ClassVar[int]
    TB_BASE_ADDRESS_FIELD_NUMBER: _ClassVar[int]
    pos: int
    tb_base_address: int
    def __init__(self, tb_base_address: _Optional[int] = ..., pos: _Optional[int] = ...) -> None: ...

class TbInformation(_message.Message):
    __slots__ = ["assembler", "base_address", "instruction_count", "num_of_exec", "size"]
    ASSEMBLER_FIELD_NUMBER: _ClassVar[int]
    BASE_ADDRESS_FIELD_NUMBER: _ClassVar[int]
    INSTRUCTION_COUNT_FIELD_NUMBER: _ClassVar[int]
    NUM_OF_EXEC_FIELD_NUMBER: _ClassVar[int]
    SIZE_FIELD_NUMBER: _ClassVar[int]
    assembler: str
    base_address: int
    instruction_count: int
    num_of_exec: int
    size: int
    def __init__(self, base_address: _Optional[int] = ..., size: _Optional[int] = ..., instruction_count: _Optional[int] = ..., num_of_exec: _Optional[int] = ..., assembler: _Optional[str] = ...) -> None: ...
