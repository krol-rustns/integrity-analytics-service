from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PROTO_DIR = ROOT / "proto"
OUTPUT_DIR = ROOT / "src" / "integrity_analytics" / "generated"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        "-m",
        "grpc_tools.protoc",
        f"-I{PROTO_DIR}",
        f"--python_out={OUTPUT_DIR}",
        f"--grpc_python_out={OUTPUT_DIR}",
        str(PROTO_DIR / "operational_data.proto"),
        str(PROTO_DIR / "diagnostico.proto"),
    ]
    subprocess.run(command, check=True)
    for path in OUTPUT_DIR.glob("*_pb2_grpc.py"):
        source = path.read_text(encoding="utf-8")
        source = re.sub(
            r"^import (operational_data_pb2|diagnostico_pb2) as ",
            r"from . import \1 as ",
            source,
            flags=re.MULTILINE,
        )
        path.write_text(source, encoding="utf-8")
    init_file = OUTPUT_DIR / "__init__.py"
    init_file.touch(exist_ok=True)


if __name__ == "__main__":
    main()
