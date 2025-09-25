import json
import os
from subprocess import STDOUT, CalledProcessError, check_output
from typing import Any, Dict

from scaler import get_video_size

from jobs_launcher.core.config import main_logger


def run_executable(command):
    main_logger.debug(f"Run command {command}")
    success = False
    try:
        output = check_output(
            command, stderr=STDOUT
        ).decode()
        success = True
    except CalledProcessError as e:
        output = e.output.decode()
    except Exception as e:
        output = str(e)

    return (success, output)


def get_ffprobe_info(case: Dict[str, Any], stream: str):
    # if 'ENC' in case['case'] or 'TRC' in case['case']:
    if case["case"].split('_')[0] in ('ENC', 'TRC', 'FFMPEG'):
        command = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_streams',
            '-show_format', '-count_frames', stream
        ]
    elif 'DEC' in case['case']:
        keys_list = case['prepare'].split()
        video_size = keys_list[1]

        if 'x' not in video_size:
            video_size = keys_list[keys_list.index('--size')+1]
        framerate = keys_list[keys_list.index('--fps')+1]
        command = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_streams', '-show_format', '-count_frames',  # noqa: E501
            '-f', 'rawvideo', '-video_size', video_size,
            '-framerate', framerate, stream
        ]
    elif 'SCL' in case['case']:
        # get actual filename
        filename = os.path.split(stream)[-1]

        # SCL_001_1.yuv or SCL_001_ma35_1.yuv -> 1
        video_index = int(filename.split('_')[-1].split('.')[0])
        video_size = get_video_size(case['simple_parameters'], video_index)

        command = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_streams', '-show_format', '-count_frames',  # noqa: E501
            '-f', 'rawvideo',
            # ffprobe doesn't work without video_size
            '-video_size', video_size,
            # '-framerate', framerate,
            stream
        ]

    success, output = run_executable(command)

    if success:
        return json.loads(output)
    else:
        main_logger.error(f'Failed to get stream info for {stream}')
        return {}


def hash_and_comapre(video_1, video_2):
    # command = ['diff', '-sq', video_1, video_2]
    command = ['sha1sum', video_1, video_2]
    _, output = run_executable(command)
    output = output.split()
    if output[0] == output[2]:
        return 'identical'
    else:
        return 'different'


def filter_video_names(x, /):
    if x.__getattribute__('keys'):
        x = x['format']['filename']
    # ../Work/Results/Xilinx/FFMPEG_Transcode/Color/FFMPEG_TRC_003_9.mp4 -> 9
    return int(x.split('_')[-1].split('.')[0])
