import os
from subprocess import Popen
from typing import Any, Dict, Tuple

from exceptions import ToolFailedException
from utils import prepare_keys, select_extension
from jobs_launcher.core.config import main_logger


def run_tool(tool: str, params: str, log: str, error_messages: set):
    tool_name = tool.split('/')[-1]

    # run complex ffmpeg commands with filters
    if tool_name == 'ffmpeg':
        shell = True
        command = f"{tool} {params}"
    else:
        shell = False
        command = [tool] + params.split()

    with open(log, 'w+') as file:
        process = Popen(command, stderr=file.fileno(), stdout=file.fileno(), shell=shell)
        exit_code = process.wait()  # noqa: E501
        # check simple tools and ama tools for non-zero exit codes
        if tool_name not in ('ffprobe') and exit_code != 0:
            message = f"{tool_name} returned non-zero exit code processing prams '{params}'"  # noqa: E501
            main_logger.error(message)
            error_messages.add(message)
            raise ToolFailedException(message)


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
