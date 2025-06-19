import os
from typing import Dict
from subprocess import Popen, DEVNULL

from utils import prepare_keys, select_extension


def run_tool(tool: str, params: str, log: str):
    command = [tool] + params.split()

    with open(log, 'w+') as file:
        Popen(command, stderr=file.fileno(), stdout=file.fileno()).wait()  # noqa: E501


def prepare_encoder_parameters(args, case: Dict, *, output_path: str = '',
                               simple_encoder: bool = False):
    output_extension = select_extension(case['script_info'][0])

    if simple_encoder:
        output_stream = os.path.relpath(os.path.join(output_path, f"{case['case']}.{output_extension}"))  # noqa: E501

        prepared_keys = prepare_keys(
            case["simple_parameters"], '', output_stream
        )
        case["prepared_keys_simple"] = prepared_keys
    else:
        input_stream = create_ma35_encoder_input(
            case['simple_parameters'],
            os.path.join(args.tool_path, f"{case['case']}.{output_extension}")
        )
        output_stream = os.path.relpath(os.path.join(output_path, f"{case['case']}_ma35.{output_extension}"))  # noqa: E501

        prepared_keys = prepare_keys(
            case["xma_parameters"], input_stream, output_stream
        )
        case["prepared_keys_xma"] = prepared_keys

    return prepared_keys, output_stream


def create_ma35_encoder_input(simple_parameters: str, output_stream: str):
    # generate video using simple encoder
    simple_encoder_path = '/opt/amd/ama/amf_Release/bin/SimpleEncoderAMA'
    simple_parameters = prepare_keys(simple_parameters, '', output_stream)

    ma35_input = os.path.join(
        os.path.split(output_stream)[0], 'ma35_input.yuv'
    )
    if os.path.exists(ma35_input):
        os.remove(ma35_input)

    encoder_command = [simple_encoder_path, '--dump-input', '-i', ma35_input] + simple_parameters.split()  # noqa: E501
    Popen(encoder_command, stdout=DEVNULL, stderr=DEVNULL).wait()

    # clean
    os.remove(output_stream)
    return ma35_input
