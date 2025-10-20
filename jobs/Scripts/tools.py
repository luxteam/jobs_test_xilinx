import os
from typing import Any, Dict, Tuple, Union
from subprocess import Popen
from abc import ABC, abstractmethod
from exceptions import ToolFailedException
from jobs_launcher.core.config import main_logger


class Tool(ABC):
    binaries_common_path = '/opt/amd/ama/'

    def __init__(self, log_path: str, simple_tool=False):
        # self.tool_path = ''
        self.log = log_path
        self.simple_tool = simple_tool

    @property
    @abstractmethod
    def tool_path(self) -> str:
        return self._tool_path

    @tool_path.setter
    @abstractmethod
    def tool_path(self):
        ...

    def prepare_keys(
        self, keys: str, input_stream: str, output_stream: str, extension: str
    ) -> str:
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
        count = keys.count('<output_stream>')

        for i in range(1, count+1):
            keys = keys.replace(
                "<output_stream>", f"{output_stream}_{i}.{extension}", 1
            )

        return keys

    def select_extension(
        self, case: Dict[str, Any]
    ) -> Union[str, Tuple[str, str]]:
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

    @abstractmethod
    def prepare_parameters(
        self, case: Dict[str, Any], *, output_path: str = ''
    ) -> Tuple[str, str, str]:
        ...

    def prepare_command(self, params):
        tool_name = self.tool_path.split('/')[-1]

        if tool_name == 'ffmpeg':
            if '&' not in params:
                return f"{self.tool_path} {params}"

            commands = params.split(' & ')
            for idx, value in enumerate(commands):
                commands[idx] = f"{self.tool_path} {value}"

            return ' & '.join(commands)

        else:
            return [self.tool_path] + params.split()

    def run_tool(self, command: str, error_messages: set):
        # run complex ffmpeg commands as shell
        if isinstance(command, list):
            shell = 'ffmpeg' in command[0]
        else:
            shell = 'ffmpeg' in command

        with open(self.log, 'w+') as file:
            process = Popen(
                command, stderr=file.fileno(), stdout=file.fileno(),
                shell=shell
            )
            exit_code = process.wait()  # noqa: E501
            # check simple tools and ama tools for non-zero exit codes
            if 'ffprobe' not in command and exit_code != 0:
                if shell:
                    tool_name = command.split()[0].split('/')[-1]
                else:
                    tool_name = command[0].split()[0].split('/')[-1]
                message = f"{tool_name} returned non-zero exit code"
                main_logger.error(message)
                error_messages.add(message)
                raise ToolFailedException(message)


class Encoder(Tool):
    def __init__(self, log_path, simple_tool=False):
        super().__init__(log_path, simple_tool)

    @property
    def tool_path(self):
        return self._tool_path

    @tool_path.setter
    def tool_path(self):
        if self.simple_tool:
            self._tool_path = os.path.join(self.binaries_common_path, 'amf_Release', 'bin', 'SimpleEncoderAMA')
        else:
            self._tool_path = os.path.join(self.binaries_common_path, 'ma35', 'bin', 'ma35_encoder_app')

    def prepare_parameters(
        self, case: Dict[str, Any], *, output_path: str = ''
    ) -> Tuple[str, str, str]:

        output_extension = self.select_extension(case)
        input_stream = os.path.relpath(
            os.path.join(output_path, f"{case['case']}.yuv")
        )

        if self.simple_tool:
            output_stream = os.path.relpath(
                os.path.join(output_path, f"{case['case']}")
            )

            prepared_keys = self.prepare_keys(
                case["simple_parameters"], input_stream, output_stream,
                output_extension
            )
            case["prepared_keys_simple"] = prepared_keys
        else:
            output_stream = os.path.relpath(
                os.path.join(output_path, f"{case['case']}_ma35")  # noqa: E501
            )

            prepared_keys = self.prepare_keys(
                case["xma_parameters"], input_stream, output_stream,
                output_extension
            )
            case["prepared_keys_xma"] = prepared_keys

        return prepared_keys, input_stream, f"{output_stream}_1.{output_extension}"


class Decoder(Tool):
    def __init__(self, log_path, simple_tool=False):
        super().__init__(log_path, simple_tool)

    @property
    def tool_path(self):
        return self._tool_path

    @tool_path.setter
    def tool_path(self):
        if self.simple_tool:
            self._tool_path = os.path.join(self.binaries_common_path, 'amf_Release', 'bin', 'SimpleDecoderAMA')
        else:
            self._tool_path = os.path.join(self.binaries_common_path, 'ma35', 'bin', 'ma35_decoder_app')

    def prepare_input(
        self, case: Dict[str, Any], output_stream: str, log: str
    ) -> None:
        encoder = Encoder(log, False)
        encoder_keys = case['prepare'].replace("<output_stream>", output_stream)
        command = [encoder] + encoder_keys.split()

        encoder.run_tool(command, {*()})

    def prepare_parameters(
        self, case: Dict[str, Any], *, output_path: str = ''
    ) -> Tuple[str, str, str]:

        input_extension = self.select_extension(case)
        input_stream = os.path.relpath(
            os.path.join(output_path, f"{case['case']}.{input_extension}")
        )
        extension = 'yuv'

        if self.simple_tool:
            output_stream = os.path.relpath(
                os.path.join(output_path, f"{case['case']}")
            )
            prepared_keys = self.prepare_keys(
                case['simple_parameters'], input_stream, output_stream,
                extension
            )
            case['prepared_keys_simple'] = prepared_keys
        else:
            output_stream = os.path.relpath(
                os.path.join(output_path, f"{case['case']}_ma35")
            )
            prepared_keys = self.prepare_keys(
                case['xma_parameters'], input_stream, output_stream,
                extension
            )
            case["prepared_keys_xma"] = prepared_keys

        return prepared_keys, input_stream, f"{output_stream}_1.{extension}"


class Scaler(Tool):
    def __init__(self, log_path, simple_tool=False):
        super().__init__(log_path, simple_tool)

    @property
    def tool_path(self):
        return self._tool_path

    @tool_path.setter
    def tool_path(self):
        if self.simple_tool:
            self._tool_path = os.path.join(self.binaries_common_path, 'amf_Release', 'bin', 'SimpleScalerAMA')
        else:
            self._tool_path = os.path.join(self.binaries_common_path, 'ma35', 'bin', 'ma35_scaler_app')

    def prepare_parameters(
        self, case: Dict[str, Any], *, output_path: str = ''
    ) -> Tuple[str, str, str]:

        input_stream = os.path.relpath(
            os.path.join(output_path, f"{case['case']}.yuv")
        )
        extension = 'yuv'

        if self.simple_tool:
            output_stream = os.path.relpath(
                os.path.join(output_path, f"{case['case']}")
            )
            prepared_keys = self.prepare_keys(
                case['simple_parameters'], input_stream, output_stream,
                extension
            )
            case['prepared_keys_simple'] = prepared_keys
        else:
            output_stream = os.path.relpath(
                os.path.join(output_path, f"{case['case']}_ma35")
            )
            prepared_keys = self.prepare_keys(
                case['xma_parameters'], input_stream, output_stream,
                extension
            )
            case['prepared_keys_xma'] = prepared_keys

        return prepared_keys, input_stream, output_stream


class Transcoder(Tool):
    def __init__(self, log_path, simple_tool=False):
        super().__init__(log_path, simple_tool)

    @property
    def tool_path(self):
        return self._tool_path

    @tool_path.setter
    def tool_path(self):
        if self.simple_tool:
            self._tool_path = os.path.join(self.binaries_common_path, 'amf_Release', 'bin', 'SimpleTranscoderAMA')
        else:
            self._tool_path = os.path.join(self.binaries_common_path, 'ma35', 'bin', 'ma35_transcoder_app')

    def prepare_input(
        self, case: Dict[str, Any], output_stream: str, log: str
    ) -> None:
        encoder = Encoder(log, False)
        encoder_keys = case['prepare'].replace("<output_stream>", output_stream)
        command = [encoder] + encoder_keys.split()

        encoder.run_tool(command, {*()})

    def prepare_parameters(
        self, case: Dict[str, Any], *, output_path: str = ''
    ) -> Tuple[str, str, str]:

        input_extension, output_extension = self.select_extension(case)
        input_stream = os.path.relpath(
            os.path.join(output_path, f"{case['case']}_inp.{input_extension}")
        )

        if self.simple_tool:
            output_stream = os.path.relpath(
                os.path.join(output_path, f"{case['case']}")
            )
            prepared_keys = self.prepare_keys(
                case['simple_parameters'], input_stream, output_stream,
                output_extension
            )
            case['prepared_keys_simple'] = prepared_keys
        else:
            output_stream = os.path.relpath(
                os.path.join(output_path, f"{case['case']}_ma35")
            )
            prepared_keys = self.prepare_keys(
                case['xma_parameters'], input_stream, output_stream,
                output_extension
            )
            case["prepared_keys_xma"] = prepared_keys

        return prepared_keys, input_stream, f"{output_stream}_1.{output_extension}"
