import os

from typing import Dict

from encoder import run_tool
from utils import select_extension, prepare_keys


def prepare_decoder_parameters(args, case: Dict, *, output_path: str = '',
                               simple_decoder: bool = False):

    input_extension = select_extension(case['script_info'][0])
    input_stream = os.path.relpath(os.path.join(output_path, f"{case['case']}.{input_extension}"))  # noqa: E501

    if simple_decoder:
        output_stream = os.path.realpath(os.path.join(output_path, f"{case['case']}.yuv"))  # noqa: E501
        prepared_keys = prepare_keys(case['simple_parameters'], input_stream, output_stream)  # noqa: E501
        case['prepared_keys_simple'] = prepared_keys
    else:
        output_stream = os.path.realpath(os.path.join(output_path, f"{case['case']}_ma35.yuv"))  # noqa: E501
        prepared_keys = prepare_keys(case['xma_parameters'], input_stream, output_stream)  # noqa: E501
        case["prepared_keys_xma"] = prepared_keys

    return prepared_keys, input_stream, output_stream


def prepare_decoder_input(case, logs_path, encoder, output_stream: str,
                          log: str):
    encoder_keys = prepare_keys(case['prepare'], '', output_stream)

    run_tool(encoder, encoder_keys, log)
