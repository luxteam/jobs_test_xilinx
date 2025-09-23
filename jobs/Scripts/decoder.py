import os
from typing import Any, Dict, Tuple

from encoder import run_tool
from utils import prepare_keys, select_extension


def prepare_decoder_parameters(
    case: Dict[str, Any], *, output_path: str = '',
    simple_decoder: bool = False
) -> Tuple[str, str, str]:

    input_extension = select_extension(case)
    input_stream = os.path.relpath(
        os.path.join(output_path, f"{case['case']}.{input_extension}")
    )
    extension = 'yuv'

    if simple_decoder:
        output_stream = os.path.relpath(
            os.path.join(output_path, f"{case['case']}")
        )
        prepared_keys = prepare_keys(
            case['simple_parameters'], input_stream, output_stream,
            extension
        )
        case['prepared_keys_simple'] = prepared_keys
    else:
        output_stream = os.path.relpath(
            os.path.join(output_path, f"{case['case']}_ma35")
        )
        prepared_keys = prepare_keys(
            case['xma_parameters'], input_stream, output_stream,
            extension
        )
        case["prepared_keys_xma"] = prepared_keys

    return prepared_keys, input_stream, output_stream


def prepare_decoder_input(
    case: Dict[str, Any], encoder: str, output_stream: str, log: str
) -> None:
    encoder_keys = prepare_keys(case['prepare'], '', output_stream)

    run_tool(encoder, encoder_keys, log)
