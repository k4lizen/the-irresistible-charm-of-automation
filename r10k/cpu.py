import copy
from dataclasses import dataclass
from pathlib import Path


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
        self.decoded_pcs: list[int] = []

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


FREELIST_SIZE: int = 32


class FreeList:
    def __init__(self) -> None:
        self.head: int = 0
        # tail is the last valid element
        self.tail: int = FREELIST_SIZE - 1
        self.freelist: list[int] = list(range(FREELIST_SIZE))
        # how many elements currently in the freelist?
        self.size = FREELIST_SIZE

    def has_x_to_give(self, x: int) -> bool:
        """Does the freelist contain >= x elements?"""
        return self.size >= x
    
    def get_free_reg(self) -> int:
        assert self.head != -1, "Not enough registers for renaming, but you checked no?"

        self.size -= 1

        if self.head == self.tail:
            # Only one element left.
            retval = self.freelist[self.head]
            self.head = self.tail = -1
            return retval

        retval = self.freelist[self.head]
        self.head = (self.head + 1) % FREELIST_SIZE
        return retval

    def give_back_reg(self, phys_reg_num: int) -> None:
        self.size += 1

        if self.head == -1:
            # There were no elements in the queue.
            self.head = self.tail = 0
        else:
            assert self.head != (self.tail + 1) % FREELIST_SIZE, (
                f"More than {FREELIST_SIZE} fake regs?"
            )
            self.tail = (self.tail + 1) % FREELIST_SIZE

        self.freelist[self.tail] = phys_reg_num

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

REORDER_BUFFER_SIZE: int = 32

# The Reorder Buffer (ROB).
class ActiveList:
    def __init__(self) -> None:
        self.head: int = -1
        self.tail: int = -1
        self.the_list: list[ActiveListEntry] = [
            ActiveListEntry(False, False, 0, 0, 0) for _ in range(REORDER_BUFFER_SIZE)
        ]
        self.size = 0

    def has_x_free_slots(self, x: int) -> bool:
        """Can the ROB fit x more elements?"""
        return (REORDER_BUFFER_SIZE - self.size) >= x

    def put_entry(self, entry: ActiveListEntry) -> None:
        self.size += 1

        if self.head == -1:
            # There were no elements in the queue.
            self.head = self.tail = 0
        else:
            assert self.head != (self.tail + 1) % REORDER_BUFFER_SIZE, (
                f"No space for active list entry? But you checked, no?"
            )
            self.tail = (self.tail + 1) % FREELIST_SIZE

        self.the_list[self.tail] = entry

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

INTEGER_QUEUE_SIZE = 32

# The reservation station.
class IntegerQueue:
    def __init__(self) -> None:
        self.head: int = -1
        self.tail: int = -1
        self.queue: list[IntegerQueueEntry] = [
            IntegerQueueEntry(0, False, 0, 0, False, 0, 0, "", 0) for _ in range(INTEGER_QUEUE_SIZE)
        ]
        self.size = 0

    def has_x_free_slots(self, x: int) -> bool:
        """Can the queue fit x more elements?"""
        return (INTEGER_QUEUE_SIZE - self.size) >= x

    def put_entry(self, entry: IntegerQueueEntry) -> None:
        self.size += 1

        if self.head == -1:
            # There were no elements in the queue.
            self.head = self.tail = 0
        else:
            assert self.head != (self.tail + 1) % INTEGER_QUEUE_SIZE, (
                f"No space for integer queue entry? But you checked, no?"
            )
            self.tail = (self.tail + 1) % INTEGER_QUEUE_SIZE

        self.queue[self.tail] = entry

    def __str__(self) -> str:
        res: str = '    "IntegerQueue": [\n'
        for el in self.queue[self.head : self.tail]:
            res += str(el)
        # no comma since it's the last structure
        res += "    ]\n"

        return res


@dataclass
class CPUState:
    pc: int
    exception_pc: int
    exception: bool

    reg_file: PhysicalRegisterFile
    decoded_instr_reg: DecodedInstructionRegister
    reg_map_table: RegisterMapTable
    freelist: FreeList
    busy_bit_table: BusyBitTable
    active_list: ActiveList
    integer_queue: IntegerQueue

    def __str__(self) -> str:
        res = ""
        res += "  {\n"
        res += f'    "PC": {self.pc},\n'
        res += str(self.reg_file)
        res += str(self.decoded_instr_reg)
        res += f'    "ExceptionPC": {self.exception_pc},\n'
        res += f'    "Exception": {str_bool(self.exception)},\n'
        res += str(self.reg_map_table)
        res += str(self.freelist)
        res += str(self.busy_bit_table)
        res += str(self.active_list)
        res += str(self.integer_queue)
        res += "  },\n"
        return res


class CPU:
    def __init__(self, input_instructions: list[str], out_file_path: Path) -> None:
        self.input_instructions: list[str] = input_instructions
        self.out_file_path: Path = out_file_path

        self.state_log: str = "[\n"

        self.state = CPUState(
            0,
            0,
            False,
            PhysicalRegisterFile(),
            DecodedInstructionRegister(),
            RegisterMapTable(),
            FreeList(),
            BusyBitTable(),
            ActiveList(),
            IntegerQueue(),
        )

    def dump_state_into_log(self) -> None:
        self.state_log += str(self.state)

    def is_active_empty(self) -> bool:
        return True

    def stage1(self, newstate: CPUState) -> None:
        # 3.1 Fetch and Decode Stage
        # FIXME: backpreassure stuff

        # Calculate new PC value
        pc_movement: int = min(4, len(self.input_instructions) - self.state.pc)

        # Ah but the DecodedInstructionRegister may not actually be ready since
        # the stage2 may have applied backpreassure. 
        dir_slots: int = 4 - len(newstate.decoded_instr_reg.decoded_pcs)
        pc_movement = min(pc_movement, dir_slots)

        # Now move the PC
        newstate.pc = self.state.pc + pc_movement

        # Put up to 4 instructions in the DecodedInstructionRegister
        for i in range(self.state.pc, newstate.pc):
            newstate.decoded_instr_reg.decoded_pcs.append(i)

    def stage2(self, newstate: CPUState) -> None:
        # 3.2 Rename and Dispatch Stage

        # > Check if there are enough physical registers, enough entries in the Active List, and
        # > enough entries in the Integer Queue. If not, apply back pressure to the previous stage,
        # > and no instruction will be renamed and dispatched. In this case, instructions already
        # > fetched by the previous stage stay in the Decoded Instruction Register. For simplicity,
        # > you can treat the instructions in the Decoded Instruction
        # > Register atomically: either all are renamed and dispatched or none.

        # How many dest registers do we need?
        ninstr: int = len(self.state.decoded_instr_reg.decoded_pcs)

        if not ( newstate.freelist.has_x_to_give(ninstr) and
            newstate.active_list.has_x_free_slots(ninstr) and
            newstate.integer_queue.has_x_free_slots(ninstr)
        ):
            # Not enough resources. We "apply backpreassure" simply by not clearing
            # the Decoded Instruction Register.
            return

        # We can take everything from the DIR.

        for dec_pc in self.state.decoded_instr_reg.decoded_pcs:
            # > If there are enough physical resources, rename the instructions decoded from the
            # > previous stage and update the Register Map Table and Free List accordingly.

            # Kinda weird that we are "fetching" here but w/e
            instr = self.input_instructions[dec_pc].split(" ", 1)
            opcode = instr[0].strip()
            operands: list[str] = instr[1].strip().split(",")

            # logical destination register
            destreg: int = int(operands[0].strip()[1:])
                        
            # physical destination register
            # Update the freelist
            phys_destreg_num: int = newstate.freelist.get_free_reg()

            # Update the Register Map Table
            olddest: int = newstate.reg_map_table.logical_to_physical[destreg]
            newstate.reg_map_table.logical_to_physical[destreg] = phys_destreg_num

            # > Determine the state of the operands required by each instruction. Each operand
            # > can be either (a) ready in the physical register file, (b) ready from the
            # > forwarding path, or (c) not produced yet. Similar to MIPS R10000, a Busy
            # > Bit Table can record whether a physical register is available.

            opa_reg: int = int(operands[1].strip()[1:])
            opb_str: str = operands[2].strip()

            # FIXME: Am I sure that I'm supposed to be looking at the old state of the
            # busy bit table?
            # FIXME: Also looking at the old state of the mapping table right after updating it?
            # oof.

            opa_physreg: int = self.state.reg_map_table.logical_to_physical[opa_reg]
            a_is_valid: bool = not self.state.busy_bit_table.is_busy[opa_physreg]

            # If a is valid, read it from the register file
            a_value: int = -1
            if a_is_valid:
                # FIXME: old or new?
                a_value = self.state.reg_file.regs[opa_physreg]

            b_value: int = -1
            if opb_str[0] == "x":
                # A register
                opb_reg = int(opb_str[1:])
                opb_physreg: int = self.state.reg_map_table.logical_to_physical[opb_reg]
                b_is_valid: bool = not self.state.busy_bit_table.is_busy[opb_physreg]
                if b_is_valid:
                    b_value = self.state.reg_file.regs[opb_physreg]
            else:
                # An immeditate
                b_is_valid = True
                b_value = int(opb_str)

            # FIXME: Also need to check the forwarding paths

            # > Allocate newly renamed entries in the Active List and the Integer Queue. Integer Queue entries are
            # > allocated after accessing the physical register file, which is similar to the Reservation Station used by
            # > the Tomasulo algorithm but differs from what is presented in the R10000 paper.

            rob_entry = ActiveListEntry(False, False, destreg, olddest, dec_pc)
            newstate.active_list.put_entry(rob_entry)

            # FIXME: How do we calculate the tag again?
            intque_entry = IntegerQueueEntry(phys_destreg_num, a_is_valid, -1, a_value, b_is_valid, -1, b_value, opcode, dec_pc)
            newstate.integer_queue.put_entry(intque_entry)

            # > Observe the results of all functional units through the forwarding paths and update the physical
            # > register file as well as the Busy Bit Table.

            # FIXME: Do this.



        # Clear the DIR to indicate no backpreassure.
        # NOTE: This means we must fetch (stage1) after this stage.
        newstate.decoded_instr_reg.decoded_pcs.clear()




    def stage3(self, newstate: CPUState) -> None:
        pass

    def stage4(self, newstate: CPUState) -> None:
        pass

    def stage5(self, newstate: CPUState) -> None:
        pass

    def stage6(self, newstate: CPUState) -> None:
        pass

    def stage7(self, newstate: CPUState) -> None:
        pass

    def propagate(self) -> CPUState:
        # self.state is oldstate, not modified during propagation
        newstate = copy.deepcopy(self.state)

        # We do stage2 before stage1 so the DIR can be cleared or not.
        self.stage2(newstate)

        self.stage1(newstate)

        # self.stage3(newstate)
        # self.stage4(newstate)
        # self.stage5(newstate)
        # self.stage6(newstate)

        return newstate

    def latch(self, newstate: CPUState) -> None:
        self.state = newstate

    def save_log(self) -> None:
        self.state_log += "]"
        with self.out_file_path.open("w") as outfile:
            outfile.write(self.state_log)

        print(f"Saved to {self.out_file_path}!")

    def no_instr_left(self) -> bool:
        return self.state.pc >= len(self.input_instructions)

    def run_completely(self) -> None:
        self.dump_state_into_log()

        while not (self.no_instr_left() and self.is_active_empty()):
            # Make a new CPUState that will be locked in via the latch.
            newstate: CPUState = self.propagate()

            # Lock in new state.
            self.latch(newstate)

            self.dump_state_into_log()

        self.save_log()
