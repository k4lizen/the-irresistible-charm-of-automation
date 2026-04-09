import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class PhysicalRegisterFile:
    def __init__(self) -> None:
        self.regs: list[int] = [0] * 64


class DecodedInstructionRegister:
    def __init__(self) -> None:
        self.decoded_pcs: list[int] = [0] * 4


class RegisterMapTable:
    def __init__(self) -> None:
        # self.logical_to_physical[4] means
        # "Which physical register is mapped to the logical register x4?"
        self.logical_to_physical: list[int] = list(range(32))


class FreeList:
    def __init__(self) -> None:
        self.head: int = 0
        # Tail is one-past the last element.
        self.tail: int = 32
        self.freelist: list[int] = list(range(32))


class BusyBitTable:
    def __init__(self) -> None:
        self.is_busy: list[bool] = [False] * 64


@dataclass
class ActiveListEntry:
    done: bool
    exception: bool
    logical_destination: int
    old_destination: int
    pc: int


# The Reorder Buffer (ROB).
class ActiveList:
    def __init__(self) -> None:
        self.head: int = 0
        self.tail: int = 1
        self.the_list: list[ActiveListEntry] = [
            ActiveListEntry(False, False, 0, 0, 0) for _ in range(32)
        ]


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


# The reservation station.
class IntegerQueue:
    def __init__(self) -> None:
        self.head: int = 0
        self.tail: int = 1
        self.queue: list[IntegerQueueEntry] = [
            IntegerQueueEntry(0, False, 0, 0, False, 0, 0, "", 0) for _ in range(32)
        ]


class CPU:
    def __init__(self, input_instructions: list[str], out_file_path: Path) -> None:
        self.input_instructions: list[str] = input_instructions
        self.out_file_path: Path = out_file_path

        self.state_log: list[dict[Any, Any]] = []

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
        print("dump inump")

    def is_active_empty(self) -> bool:
        return True

    def propagate(self) -> None:
        pass

    def latch(self) -> None:
        pass

    def save_log(self) -> None:
        out_contents = json.dumps(self.state_log)
        with self.out_file_path.open("w") as outfile:
            outfile.write(out_contents)

        print(f"Saved to {self.out_file_path}!")

    def no_instr_left(self) -> bool:
        return self.pc >= len(self.input_instructions)

    def run_completely(self) -> None:
        self.dump_state_into_log()

        while not (self.no_instr_left() and self.is_active_empty()):
            self.propagate()

            self.latch()

            self.dump_state_into_log()

        self.save_log()
