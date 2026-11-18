"""
Genera el código Python de gRPC a partir de contracts/proto/airport.proto y lo
copia en los dos servicios que lo usan:

  services/airport-service/app/grpc_stubs/     (servidor)
  services/itinerary-service/app/grpc_stubs/   (cliente)

Uso (desde la raíz del repo):
    pip install grpcio-tools
    python scripts/generate_grpc.py

Los archivos generados se suben al repo para que los servicios no necesiten
grpcio-tools en tiempo de ejecución.
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROTO_DIR = ROOT / "contracts" / "proto"
TARGETS = [
    ROOT / "services" / "airport-service" / "app" / "grpc_stubs",
    ROOT / "services" / "itinerary-service" / "app" / "grpc_stubs",
]


def main() -> None:
    out = TARGETS[0]
    out.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            sys.executable, "-m", "grpc_tools.protoc",
            f"-I{PROTO_DIR}",
            f"--python_out={out}",
            f"--pyi_out={out}",
            f"--grpc_python_out={out}",
            str(PROTO_DIR / "airport.proto"),
        ],
        check=True,
    )
    # protoc genera "import airport_pb2"; dentro de un paquete necesitamos un import relativo.
    grpc_file = out / "airport_pb2_grpc.py"
    grpc_file.write_text(
        re.sub(r"^import airport_pb2 as", "from . import airport_pb2 as", grpc_file.read_text(encoding="utf-8"), flags=re.M),
        encoding="utf-8",
    )
    (out / "__init__.py").write_text('"""Código GENERADO por scripts/generate_grpc.py. No editar a mano."""\n', encoding="utf-8")

    for target in TARGETS[1:]:
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(out, target, ignore=shutil.ignore_patterns("__pycache__"))
    print("Código gRPC generado en:", *[str(t.relative_to(ROOT)) for t in TARGETS], sep="\n  ")


if __name__ == "__main__":
    main()
