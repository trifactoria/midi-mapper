from typing import Any, Dict


OUTPUT_PORT_CACHE: Dict[str, Any] = {}


def close_output_ports(output_port_cache: Dict[str, Any]) -> None:
    for name, out in list(output_port_cache.items()):
        try:
            out.close()
        except Exception:
            pass
        output_port_cache.pop(name, None)
