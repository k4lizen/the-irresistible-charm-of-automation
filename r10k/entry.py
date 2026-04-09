import json
import sys
from pathlib import Path

from .cpu import CPU


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: r10k </path/to/input.json> </path/to/output.json>")
        sys.exit(1)

    in_file_path: Path = Path(sys.argv[1])
    out_file_path: Path = Path(sys.argv[2])

    with in_file_path.open() as infile:
        input_instructions: list[str] = json.loads(infile.read())

    cpu = CPU(input_instructions, out_file_path)
    cpu.run_completely()


if __name__ == "__main__":
    main()
