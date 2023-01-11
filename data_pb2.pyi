from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Arch_Register(_message.Message):
    __slots__ = ["arch_type", "register_dumps"]
    ARCH_TYPE_FIELD_NUMBER: _ClassVar[int]
    REGISTER_DUMPS_FIELD_NUMBER: _ClassVar[int]
    arch_type: int
    register_dumps: _containers.RepeatedCompositeFieldContainer[Register_dump]
    def __init__(self, register_dumps: _Optional[_Iterable[_Union[Register_dump, _Mapping]]] = ..., arch_type: _Optional[int] = ...) -> None: ...

class Data(_message.Message):
    __slots__ = ["Mem_dump_object_list", "arch_register", "end_reason", "endpoint", "faulted_data_list", "mem_info_list", "tb_exec_orders", "tb_information"]
    ARCH_REGISTER_FIELD_NUMBER: _ClassVar[int]
    ENDPOINT_FIELD_NUMBER: _ClassVar[int]
    END_REASON_FIELD_NUMBER: _ClassVar[int]
    FAULTED_DATA_LIST_FIELD_NUMBER: _ClassVar[int]
    MEM_DUMP_OBJECT_LIST_FIELD_NUMBER: _ClassVar[int]
    MEM_INFO_LIST_FIELD_NUMBER: _ClassVar[int]
    Mem_dump_object_list: _containers.RepeatedCompositeFieldContainer[Mem_dump_object]
    TB_EXEC_ORDERS_FIELD_NUMBER: _ClassVar[int]
    TB_INFORMATION_FIELD_NUMBER: _ClassVar[int]
    arch_register: Arch_Register
    end_reason: str
    endpoint: int
    faulted_data_list: _containers.RepeatedCompositeFieldContainer[Faulted_data]
    mem_info_list: _containers.RepeatedCompositeFieldContainer[Mem_info]
    tb_exec_orders: _containers.RepeatedCompositeFieldContainer[Tb_exec_order]
    tb_information: _containers.RepeatedCompositeFieldContainer[Tb_information]
    def __init__(self, endpoint: _Optional[int] = ..., end_reason: _Optional[str] = ..., tb_information: _Optional[_Iterable[_Union[Tb_information, _Mapping]]] = ..., tb_exec_orders: _Optional[_Iterable[_Union[Tb_exec_order, _Mapping]]] = ..., mem_info_list: _Optional[_Iterable[_Union[Mem_info, _Mapping]]] = ..., arch_register: _Optional[_Union[Arch_Register, _Mapping]] = ..., faulted_data_list: _Optional[_Iterable[_Union[Faulted_data, _Mapping]]] = ..., Mem_dump_object_list: _Optional[_Iterable[_Union[Mem_dump_object, _Mapping]]] = ...) -> None: ...

class Faulted_data(_message.Message):
    __slots__ = ["assembler", "trigger_address"]
    ASSEMBLER_FIELD_NUMBER: _ClassVar[int]
    TRIGGER_ADDRESS_FIELD_NUMBER: _ClassVar[int]
    assembler: str
    trigger_address: int
    def __init__(self, trigger_address: _Optional[int] = ..., assembler: _Optional[str] = ...) -> None: ...

class Mem_dump(_message.Message):
    __slots__ = ["mem"]
    MEM_FIELD_NUMBER: _ClassVar[int]
    mem: bytes
    def __init__(self, mem: _Optional[bytes] = ...) -> None: ...

class Mem_dump_object(_message.Message):
    __slots__ = ["address", "dumps", "len", "used_dumps"]
    ADDRESS_FIELD_NUMBER: _ClassVar[int]
    DUMPS_FIELD_NUMBER: _ClassVar[int]
    LEN_FIELD_NUMBER: _ClassVar[int]
    USED_DUMPS_FIELD_NUMBER: _ClassVar[int]
    address: int
    dumps: _containers.RepeatedCompositeFieldContainer[Mem_dump]
    len: int
    used_dumps: int
    def __init__(self, address: _Optional[int] = ..., len: _Optional[int] = ..., used_dumps: _Optional[int] = ..., dumps: _Optional[_Iterable[_Union[Mem_dump, _Mapping]]] = ...) -> None: ...

class Mem_info(_message.Message):
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

class Register_dump(_message.Message):
    __slots__ = ["pc", "register_data", "tb_count"]
    PC_FIELD_NUMBER: _ClassVar[int]
    REGISTER_DATA_FIELD_NUMBER: _ClassVar[int]
    TB_COUNT_FIELD_NUMBER: _ClassVar[int]
    pc: int
    register_data: _containers.RepeatedScalarFieldContainer[int]
    tb_count: int
    def __init__(self, register_data: _Optional[_Iterable[int]] = ..., pc: _Optional[int] = ..., tb_count: _Optional[int] = ...) -> None: ...

class Tb_exec_order(_message.Message):
    __slots__ = ["pos", "tb_base_address", "tb_info_exist"]
    POS_FIELD_NUMBER: _ClassVar[int]
    TB_BASE_ADDRESS_FIELD_NUMBER: _ClassVar[int]
    TB_INFO_EXIST_FIELD_NUMBER: _ClassVar[int]
    pos: int
    tb_base_address: int
    tb_info_exist: bool
    def __init__(self, tb_info_exist: bool = ..., tb_base_address: _Optional[int] = ..., pos: _Optional[int] = ...) -> None: ...

class Tb_information(_message.Message):
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
