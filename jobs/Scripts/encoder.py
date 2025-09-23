import os
from subprocess import Popen
from typing import Any, Dict, Tuple

from exceptions import ToolFailedException
from utils import prepare_keys, select_extension
from jobs_launcher.core.config import main_logger


def run_tool(command: str, log: str, error_messages: set):
    # run complex ffmpeg commands as shell
    shell = 'ffmpeg' in command

    with open(log, 'w+') as file:
        process = Popen(
            command, stderr=file.fileno(), stdout=file.fileno(),
            shell=shell
        )
        exit_code = process.wait()  # noqa: E501
        # check simple tools and ama tools for non-zero exit codes
        if 'ffprobe' not in command and exit_code != 0:
            tool_name = command.split()[0].split('/')[-1]
            message = f"{tool_name} returned non-zero exit code"
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
            os.path.join(output_path, f"{case['case']}")
        )

        prepared_keys = prepare_keys(
            case["simple_parameters"], input_stream, output_stream,
            output_extension
        )
        case["prepared_keys_simple"] = prepared_keys
    else:
        output_stream = os.path.relpath(
            os.path.join(output_path, f"{case['case']}_ma35")  # noqa: E501
        )

        prepared_keys = prepare_keys(
            case["xma_parameters"], input_stream, output_stream,
            output_extension
        )
        case["prepared_keys_xma"] = prepared_keys

    return prepared_keys, input_stream, output_stream
