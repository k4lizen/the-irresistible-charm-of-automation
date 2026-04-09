import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def str_bool(b: bool) -> str:
    return "true" if b else "false"


class PhysicalRegisterFile:
    def __init__(self) -> None:
        self.regs: list[int] = [0] * 64

    def __str__(self) -> str:
        res: str = '    "PhysicalRegisterFile": [\n      '
        res += ", ".join([str(x) for x in self.regs])
        res += "\n    ],\n"
        return res


class DecodedInstructionRegister:
    def __init__(self) -> None:
        self.decoded_pcs: list[int] = [0] * 4

    def __str__(self) -> str:
        res: str = '    "DecodedInstructionRegister": [\n      '
        res += ", ".join([str(x) for x in self.decoded_pcs])
        res += "\n    ],\n"
        return res


class RegisterMapTable:
    def __init__(self) -> None:
        # self.logical_to_physical[4] means
        # "Which physical register is mapped to the logical register x4?"
        self.logical_to_physical: list[int] = list(range(32))

    def __str__(self) -> str:
        res: str = '    "RegisterMapTable": [\n      '
        res += ", ".join([str(x) for x in self.logical_to_physical])
        res += "\n    ],\n"
        return res


class FreeList:
    def __init__(self) -> None:
        self.head: int = 0
        # Tail is one-past the last element.
        self.tail: int = 32
        self.freelist: list[int] = list(range(32))

    def __str__(self) -> str:
        res: str = '    "FreeList": [\n      '
        res += ", ".join([str(x) for x in self.freelist])
        res += "\n    ],\n"
        return res

class BusyBitTable:
    def __init__(self) -> None:
        self.is_busy: list[bool] = [False] * 64

    def __str__(self) -> str:
        res: str = '    "BusyBitTable": [\n      '
        res += ", ".join([str_bool(x) for x in self.is_busy])
        res += "\n    ],\n"
        return res


@dataclass
class ActiveListEntry:
    done: bool
    exception: bool
    logical_destination: int
    old_destination: int
    pc: int

    def __str__(self) -> str:
        return f"""\
      {{
        "Done": {str_bool(self.done)},
        "Exception": {str_bool(self.exception)},
        "LogicalDestination": {self.logical_destination},
        "OldDestination": {self.old_destination},
        "PC": {self.pc},
      }},
"""


# The Reorder Buffer (ROB).
class ActiveList:
    def __init__(self) -> None:
        self.head: int = 0
        self.tail: int = 0
        self.the_list: list[ActiveListEntry] = [
            ActiveListEntry(False, False, 0, 0, 0) for _ in range(32)
        ]

    def __str__(self) -> str:
        res: str = '    "ActiveList": [\n'
        for el in self.the_list[self.head : self.tail]:
            res += str(el)
        res += "    ],\n"
        return res


@dataclass
class IntegerQueueEntry:
    dest_register: int
    opa_is_ready: bool
    opa_reg_tag: int
    opa_value: int
    opb_is_ready: bool
    opb_reg_tag: int
    opb_value: int
    opcode: str
    pc: int

    def __str__(self) -> str:
        return f"""\
      {{
        "DestRegister": {self.dest_register},
        "OpAIsReady": {str_bool(self.opa_is_ready)},
        "OpARegTag": {self.opa_reg_tag},
        "OpAValue": {self.opa_value},
        "OpBIsReady": {str_bool(self.opb_is_ready)},
        "OpBRegTag": {self.opb_reg_tag},
        "OpBValue": {self.opb_value},
        "OpCode": "{self.opcode}",
        "PC": {self.pc}
      }},
"""


# The reservation station.
class IntegerQueue:
    def __init__(self) -> None:
        self.head: int = 0
        self.tail: int = 0
        self.queue: list[IntegerQueueEntry] = [
            IntegerQueueEntry(0, False, 0, 0, False, 0, 0, "", 0) for _ in range(32)
        ]

    def __str__(self) -> str:
        res: str = '    "IntegerQueue": [\n'
        for el in self.queue[self.head : self.tail]:
            res += str(el)
        # no comma since it's the last structure
        res += "    ]\n"

        return res


class CPU:
    def __init__(self, input_instructions: list[str], out_file_path: Path) -> None:
        self.input_instructions: list[str] = input_instructions
        self.out_file_path: Path = out_file_path

        self.state_log: str = "[\n"

        self.pc: int = 0
        self.exception_pc: int = 0
        self.exception: bool = False

        self.reg_file = PhysicalRegisterFile()
        self.decoded_instr_reg = DecodedInstructionRegister()
        self.reg_map_table = RegisterMapTable()
        self.freelist = FreeList()
        self.busy_bit_table = BusyBitTable()
        self.active_list = ActiveList()
        self.integer_queue = IntegerQueue()

    def dump_state_into_log(self) -> None:
        self.state_log += "  {\n"
        self.state_log += f'    "PC": {self.pc},\n'
        self.state_log += str(self.reg_file)
        self.state_log += str(self.decoded_instr_reg)
        self.state_log += f'    "ExceptionPC": {self.exception_pc},\n'
        self.state_log += f'    "Exception": {str_bool(self.exception)},\n'
        self.state_log += str(self.reg_map_table)
        self.state_log += str(self.freelist)
        self.state_log += str(self.busy_bit_table)
        self.state_log += str(self.active_list)
        self.state_log += str(self.integer_queue)
        self.state_log += "  },\n"

    def is_active_empty(self) -> bool:
        return True

    def propagate(self) -> None:
        pass

    def latch(self) -> None:
        pass

    def save_log(self) -> None:
        self.state_log += "]"
        with self.out_file_path.open("w") as outfile:
            outfile.write(self.state_log)

        print(f"Saved to {self.out_file_path}!")

    def no_instr_left(self) -> bool:
        return self.pc >= len(self.input_instructions)

    def run_completely(self) -> None:
        self.dump_state_into_log()
        self.save_log()

        return

        while not (self.no_instr_left() and self.is_active_empty()):
            self.propagate()

            self.latch()

            self.dump_state_into_log()

        self.save_log()
