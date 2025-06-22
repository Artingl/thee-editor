from enum import Enum


class BufferMode(Enum):
    INSERT: str = 'insert'
    COMMAND: str = 'command'
    VISUAL: str = 'visual'
    COMMAND_INSERT: str = 'command_insert'
