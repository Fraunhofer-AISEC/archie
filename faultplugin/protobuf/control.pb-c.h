/* Generated by the protocol buffer compiler.  DO NOT EDIT! */
/* Generated from: control.proto */

#ifndef PROTOBUF_C_control_2eproto__INCLUDED
#define PROTOBUF_C_control_2eproto__INCLUDED

#include <protobuf-c/protobuf-c.h>

PROTOBUF_C__BEGIN_DECLS

#if PROTOBUF_C_VERSION_NUMBER < 1003000
# error This file was generated by a newer version of protoc-c which is incompatible with your libprotobuf-c headers. Please update your headers.
#elif 1004001 < PROTOBUF_C_MIN_COMPILER_VERSION
# error This file was generated by an older version of protoc-c which is incompatible with your libprotobuf-c headers. Please regenerate this file with a newer version of protoc-c.
#endif


typedef struct Archie__Control Archie__Control;
typedef struct Archie__EndPoint Archie__EndPoint;
typedef struct Archie__MemoryDump Archie__MemoryDump;


/* --- enums --- */


/* --- messages --- */

struct  Archie__Control
{
  ProtobufCMessage base;
  int64_t max_duration;
  int64_t num_faults;
  protobuf_c_boolean tb_exec_list;
  protobuf_c_boolean tb_info;
  protobuf_c_boolean mem_info;
  uint64_t start_address;
  uint64_t start_counter;
  size_t n_end_points;
  Archie__EndPoint **end_points;
  protobuf_c_boolean tb_exec_list_ring_buffer;
  size_t n_memorydumps;
  Archie__MemoryDump **memorydumps;
  protobuf_c_boolean has_start;
};
#define ARCHIE__CONTROL__INIT \
 { PROTOBUF_C_MESSAGE_INIT (&archie__control__descriptor) \
    , 0, 0, 0, 0, 0, 0, 0, 0,NULL, 0, 0,NULL, 0 }


struct  Archie__EndPoint
{
  ProtobufCMessage base;
  uint64_t address;
  uint64_t counter;
};
#define ARCHIE__END_POINT__INIT \
 { PROTOBUF_C_MESSAGE_INIT (&archie__end_point__descriptor) \
    , 0, 0 }


struct  Archie__MemoryDump
{
  ProtobufCMessage base;
  uint64_t address;
  uint64_t length;
};
#define ARCHIE__MEMORY_DUMP__INIT \
 { PROTOBUF_C_MESSAGE_INIT (&archie__memory_dump__descriptor) \
    , 0, 0 }


/* Archie__Control methods */
void   archie__control__init
                     (Archie__Control         *message);
size_t archie__control__get_packed_size
                     (const Archie__Control   *message);
size_t archie__control__pack
                     (const Archie__Control   *message,
                      uint8_t             *out);
size_t archie__control__pack_to_buffer
                     (const Archie__Control   *message,
                      ProtobufCBuffer     *buffer);
Archie__Control *
       archie__control__unpack
                     (ProtobufCAllocator  *allocator,
                      size_t               len,
                      const uint8_t       *data);
void   archie__control__free_unpacked
                     (Archie__Control *message,
                      ProtobufCAllocator *allocator);
/* Archie__EndPoint methods */
void   archie__end_point__init
                     (Archie__EndPoint         *message);
size_t archie__end_point__get_packed_size
                     (const Archie__EndPoint   *message);
size_t archie__end_point__pack
                     (const Archie__EndPoint   *message,
                      uint8_t             *out);
size_t archie__end_point__pack_to_buffer
                     (const Archie__EndPoint   *message,
                      ProtobufCBuffer     *buffer);
Archie__EndPoint *
       archie__end_point__unpack
                     (ProtobufCAllocator  *allocator,
                      size_t               len,
                      const uint8_t       *data);
void   archie__end_point__free_unpacked
                     (Archie__EndPoint *message,
                      ProtobufCAllocator *allocator);
/* Archie__MemoryDump methods */
void   archie__memory_dump__init
                     (Archie__MemoryDump         *message);
size_t archie__memory_dump__get_packed_size
                     (const Archie__MemoryDump   *message);
size_t archie__memory_dump__pack
                     (const Archie__MemoryDump   *message,
                      uint8_t             *out);
size_t archie__memory_dump__pack_to_buffer
                     (const Archie__MemoryDump   *message,
                      ProtobufCBuffer     *buffer);
Archie__MemoryDump *
       archie__memory_dump__unpack
                     (ProtobufCAllocator  *allocator,
                      size_t               len,
                      const uint8_t       *data);
void   archie__memory_dump__free_unpacked
                     (Archie__MemoryDump *message,
                      ProtobufCAllocator *allocator);
/* --- per-message closures --- */

typedef void (*Archie__Control_Closure)
                 (const Archie__Control *message,
                  void *closure_data);
typedef void (*Archie__EndPoint_Closure)
                 (const Archie__EndPoint *message,
                  void *closure_data);
typedef void (*Archie__MemoryDump_Closure)
                 (const Archie__MemoryDump *message,
                  void *closure_data);

/* --- services --- */


/* --- descriptors --- */

extern const ProtobufCMessageDescriptor archie__control__descriptor;
extern const ProtobufCMessageDescriptor archie__end_point__descriptor;
extern const ProtobufCMessageDescriptor archie__memory_dump__descriptor;

PROTOBUF_C__END_DECLS


#endif  /* PROTOBUF_C_control_2eproto__INCLUDED */
