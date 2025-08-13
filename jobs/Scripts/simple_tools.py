import os
from typing import Any, Dict, Tuple, Union
from subprocess import Popen


class Tool():

    def __init__(self, log_path: str, simple_tool=False):
        self.binaries_common_path = '/opt/amd/ama/'
        self.tool_path = ''
        self.log_path = log_path
        self.simple_tool = simple_tool

    def prepare_parameters(
        self, case: Dict[str, Any], *, output_path: str = '',
    ) -> Tuple[str, str, str]:
        pass

    def run_tool(self, params: str, tool=None, log=None):
        if log is None:
            log = self.log_path
        if tool is None:
            tool = self.tool_path

        command = [tool] + params.split()

        with open(log, 'w+') as file:
            Popen(command, stderr=file.fileno(), stdout=file.fileno()).wait()  # noqa: E501

    def select_extension(self, case: Dict[str, Any]) -> Union[str, Tuple[str, str]]:
        """Select appropriate file extension(s) based on video codec parameters.

        This function analyzes the script_info from a test case and determines the
        appropriate file extension based on the video codec mentioned.
        For transcoding cases (TRC), it returns both source and target extensions.

        Args:
            case (Dict[str, Any]): Dictionary containing test case information
                with required keys:
                - 'script_info': List with at least one string element containing
                codec info
                - 'case': String identifier, may contain 'TRC' for transcoding
                cases

        Returns:
            Union[str, Tuple[str, str]]: For non-TRC cases: Single extension
                string, for TRC cases: Tuple of (from_extension, to_extension)
        """

        def _select_extension(params: str) -> str:
            params = params.lower()
            if 'h264' in params:
                return 'h264'
            elif 'h265' in params or 'hevc' in params:
                return 'h265'
            elif 'av1' in params or 'vp9' in params:
                return 'ivf'

        script_info = case['script_info'][0].lower()

        if 'TRC' in case['case']:
            script_info = script_info.split('__')
            from_ext = _select_extension(script_info[0])
            to_ext = _select_extension(script_info[1])

            return from_ext, to_ext

        else:
            return _select_extension(script_info)

    def prepare_keys(self, keys: str, input_stream: str, output_stream: str,
                     iterate: bool = False, extension: str = '') -> str:
        """Prepare command keys by replacing placeholder tokens with actual paths.

        This function processes a template string containing placeholders and
        replaces them with actual file paths. For iterative cases, it can
        generate multiple numbered output files.

        Args:
            keys (str): Template string containing placeholders
                '\<input_stream\>'and '\<output_stream\>' to be replaced
            input_stream (str): File path to replace '\<input_stream\>' placeholder
            output_stream (str): Base file path to replace '\<output_stream\>'
                placeholder(s)
            iterate (bool, optional): If True, generates numbered output files for
                multiple'\<output_stream\>' placeholders. If False, replaces all
                with the same output_stream path. Defaults to False.
            extension (str, optional): File extension to append when iterate=True
                (without dot). Defaults to ''.

        Returns:
            str: Processed string with placeholders replaced by actual paths
        """
        keys = keys.replace("<input_stream>", input_stream)

        if iterate:
            count = keys.count('<output_stream>')
            for i in range(1, count+1):
                keys = keys.replace(
                    "<output_stream>", f"{output_stream}_{i}.{extension}", 1
                )
        else:
            keys = keys.replace("<output_stream>", output_stream)

        return keys


class Encoder(Tool):
    def __init__(self, log_path, simple_tool=False):
        super().__init__(log_path, simple_tool)
        if simple_tool:
            self.tool_path = os.path.join(
                self.binaries_common_path, 'amf_Release', 'bin', 'SimpleEncoderAMA'
            )
        else:
            self.tool_path = os.path.join(
                self.binaries_common_path, 'ma35', 'bin', 'ma35_encoder_app'
            )

    pass


class Decoder(Tool):
    def __init__(self, log_path, simple_tool, input_preparation_log):
        super().__init__(log_path, simple_tool)
        self.input_preparation_log = input_preparation_log
        self.encoder_path = os.path.join(
                self.binaries_common_path, 'amf_Release', 'bin', 'SimpleEncoderAMA'
            )
        if simple_tool:
            self.tool_path = os.path.join(
                self.binaries_common_path, 'amf_Release', 'bin', 'SimpleDecoderAMA'
            )
        else:
            self.tool_path = os.path.join(
                self.binaries_common_path, 'ma35', 'bin', 'ma35_decoder_app'
            )
    pass

    def prepare_parameters(
        self, case: Dict[str, Any], *, output_path: str = '',
    ) -> Tuple[str, str, str]:
        input_extension = self.select_extension(case)
        input_stream = os.path.relpath(
            os.path.join(output_path, f"{case['case']}.{input_extension}")
        )

        if self.simple_tool:
            output_stream = os.path.relpath(
                os.path.join(output_path, f"{case['case']}.yuv")
            )
            prepared_keys = self.prepare_keys(
                case['simple_parameters'], input_stream, output_stream
            )
            case['prepared_keys_simple'] = prepared_keys
        else:
            output_stream = os.path.relpath(
                os.path.join(output_path, f"{case['case']}_ma35.yuv")
            )
            prepared_keys = self.prepare_keys(
                case['xma_parameters'], input_stream, output_stream
            )
            case["prepared_keys_xma"] = prepared_keys

        return prepared_keys, input_stream, output_stream

    def prepare_input(self, case: Dict[str, Any], output_stream: str):
        encoder_keys = self.prepare_keys(case['prepare'], '', output_stream)
        self.run_tool(
            encoder_keys, self.encoder_path, self.input_preparation_log
        )
