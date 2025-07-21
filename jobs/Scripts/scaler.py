import os
from typing import Any, Dict, Tuple

from utils import prepare_keys


def prepare_scaler_parameters(
    case: Dict[str, Any], *, output_path: str = '',
    simple_scaler: bool = False
) -> Tuple[str, str, str]:
    input_stream = os.path.relpath(
        os.path.join(output_path, f"{case['case']}.yuv")
    )
    if simple_scaler:
        output_stream = os.path.relpath(
            os.path.join(output_path, f"{case['case']}")
        )
        prepared_keys = prepare_keys(
            case['simple_parameters'], input_stream, output_stream,
            iterate=True, extension='yuv'
        )
        case['prepared_keys_simple'] = prepared_keys
    else:
        output_stream = os.path.relpath(
            os.path.join(output_path, f"{case['case']}_ma35")
        )
        prepared_keys = prepare_keys(
            case['xma_parameters'], input_stream, output_stream,
            iterate=True, extension='yuv'
        )
        case['prepared_keys_xma'] = prepared_keys
    return prepared_keys, input_stream, output_stream


def get_video_size(keys: str, count: int) -> str:
    keys = keys.split()

    for i in range(1, count+1):
        # get index of the first ocurrance of <output_stream>
        index = keys.index('<output_stream>')
        if i == count:
            return keys[index-2]

        # update list to find the next ocurrance of <output_stream>
        keys = keys[index+1:]
