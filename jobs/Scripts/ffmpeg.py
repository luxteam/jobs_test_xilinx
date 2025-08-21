import os
from typing import Any, Dict, Tuple

from utils import prepare_keys


def select_input_file(case: Dict[str, Any]):
    # map videos to ffmpeg usecases
    # inputs_map = {
    #     "teams": "bbb_360p30.mp4"
    # }
    # test_usecase = case['case'].split('_')[0]
    # for ffmpeg_usecase, input_file in inputs_map.items():
    #     if test_usecase == ffmpeg_usecase:
    #         return input_file

    return 'bbb_360p30.mp4'


def prepare_ffmpeg_parameters(
    case: Dict[str, Any], *,
    input_path: str = '', output_path: str = '',
    amf_ffmpeg: bool = False
) -> Tuple[str, str, str]:
    input_file = select_input_file(case)
    input_stream = os.path.relpath(
        os.path.join(input_path, input_file)
    )

    if amf_ffmpeg:
        output_stream = os.path.relpath(
            os.path.join(output_path, f"{case['case']}.mp4")
        )
        prepared_keys = prepare_keys(
            case["simple_parameters"], input_stream, output_stream
        )
        case["prepared_keys_simple"] = prepared_keys
    else:
        output_stream = os.path.relpath(
            os.path.join(output_path, f"{case['case']}_xma.mp4")
        )
        prepared_keys = prepare_keys(
            case["simple_parameters"], input_stream, output_stream
        )
        case["prepared_keys_xma"] = prepared_keys

    return prepared_keys, input_stream, output_stream


def measure_ffmpeg_performance(
    amf_log: str, xma_log: str, *, error_messages: set
):
    with open(amf_log, 'r') as file:
        amf_log_content = file.read()

    with open(xma_log, 'r') as file:
        xma_log_content = file.read()

    # find fps in each log and compare values
    amf_avg_fps = int(amf_log_content.split('fps=')[1].split(' ')[0])
    xma_avg_fps = int(xma_log_content.split('fps=')[1].split(' ')[0])

    if amf_avg_fps < (xma_avg_fps + (xma_avg_fps * 3 / 100)) or amf_avg_fps > (xma_avg_fps + (xma_avg_fps * 3 / 100)):
        message = f"AMF_FFMPEG's performace (fps={amf_avg_fps}) difference with VPI_FFMPG's performance (fps={xma_avg_fps}) is more than 3%"
        error_messages.add(message)
