from enum import Enum


class BufferMode(Enum):
    INSERT: str = 'insert'
    COMMAND: str = 'command'
    COMMAND_INSERT: str = 'command_insert'
