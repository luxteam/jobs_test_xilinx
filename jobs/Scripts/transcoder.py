import os
from typing import Any, Dict, Tuple

from encoder import run_tool
from utils import prepare_keys, select_extension


def prepare_transcoder_parameters(
    case: Dict[str, Any], *, output_path: str = '',
    simple_transcoder: bool = False
) -> Tuple[str, str, str]:

    input_extension, output_extension = select_extension(case)
    input_stream = os.path.relpath(
        os.path.join(output_path, f"{case['case']}_inp.{input_extension}")
    )

    if simple_transcoder:
        output_stream = os.path.relpath(
            os.path.join(output_path, f"{case['case']}")
        )
        prepared_keys = prepare_keys(
            case['simple_parameters'], input_stream, output_stream,
            output_extension
        )
        case['prepared_keys_simple'] = prepared_keys
    else:
        output_stream = os.path.relpath(
            os.path.join(output_path, f"{case['case']}_ma35")
        )
        prepared_keys = prepare_keys(
            case['xma_parameters'], input_stream, output_stream,
            output_extension
        )
        case["prepared_keys_xma"] = prepared_keys

    return prepared_keys, input_stream, f"{output_stream}_1.{output_extension}"


def prepare_transcoder_input(
    case: Dict[str, Any], encoder: str, output_stream: str, log: str
) -> None:
    encoder_keys = case['prepare'].replace("<output_stream>", output_stream)
    error_messages = {*()}
    command = [encoder] + encoder_keys.split()

    run_tool(command, log, error_messages)
