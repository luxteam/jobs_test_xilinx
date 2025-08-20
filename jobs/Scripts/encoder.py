import os
from subprocess import Popen
from typing import Any, Dict, Tuple

from utils import prepare_keys, select_extension


def run_tool(tool: str, params: str, log: str):
    command = [tool] + params.split()

    with open(log, 'w+') as file:
        process = Popen(command, stderr=file.fileno(), stdout=file.fileno())
        exit_code = process.wait()  # noqa: E501
        # check simple tools and ama tools for non-zero exit codes
        if tool.split('/')[-1] not in ('ffmpeg', 'ffprobe') and exit_code != 0:
            raise Exception(f"Command finished with non-zero exit code: {command}")


def prepare_encoder_parameters(
    case: Dict[str, Any], *, output_path: str = '',
    simple_encoder: bool = False
) -> Tuple[str, str, str]:
    output_extension = select_extension(case)
    input_stream = os.path.relpath(
        os.path.join(output_path, f"{case['case']}.yuv")
    )

    if simple_encoder:
        output_stream = os.path.relpath(
            os.path.join(output_path, f"{case['case']}.{output_extension}")
        )

        prepared_keys = prepare_keys(
            case["simple_parameters"], input_stream, output_stream
        )
        case["prepared_keys_simple"] = prepared_keys
    else:
        output_stream = os.path.relpath(
            os.path.join(output_path, f"{case['case']}_ma35.{output_extension}")  # noqa: E501
        )

        prepared_keys = prepare_keys(
            case["xma_parameters"], input_stream, output_stream
        )
        case["prepared_keys_xma"] = prepared_keys

    return prepared_keys, input_stream, output_stream
