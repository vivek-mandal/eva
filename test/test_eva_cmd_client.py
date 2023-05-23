# coding=utf-8
# Copyright 2018-2022 EVA
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import argparse
import asyncio
import unittest

from mock import call, patch

from eva.configuration.configuration_manager import ConfigurationManager
from eva.eva_cmd_client import eva_client, main


class CMDClientTest(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_mock_stdin_reader(self) -> asyncio.StreamReader:
        stdin_reader = asyncio.StreamReader()
        stdin_reader.feed_data(b"EXIT;\n")
        stdin_reader.feed_eof()
        return stdin_reader

    @patch("eva.eva_cmd_client.start_cmd_client")
    @patch("eva.server.interpreter.create_stdin_reader")
    def test_eva_client(self, mock_stdin_reader, mock_client):
        mock_stdin_reader.return_value = self.get_mock_stdin_reader()
        mock_client.side_effect = Exception("Test")

        async def test():
            with self.assertRaises(Exception):
                await eva_client("0.0.0.0", 8803)

        asyncio.run(test())

        mock_client.reset_mock()
        mock_client.side_effect = KeyboardInterrupt

        async def test2():
            # Pass exception
            await eva_client("0.0.0.0", 8803)

        asyncio.run(test2())

    @patch("argparse.ArgumentParser.parse_known_args")
    @patch("eva.eva_cmd_client.start_cmd_client")
    def test_eva_client_with_cmd_arguments(
        self, mock_start_cmd_client, mock_parse_known_args
    ):
        # Set up the mock to simulate command-line arguments
        mock_parse_known_args.return_value = (
            argparse.Namespace(host="127.0.0.1", port="8800"),
            [],
        )

        # Call the function under test
        main()
        mock_start_cmd_client.assert_called_once_with("127.0.0.1", "8800")

    @patch("argparse.ArgumentParser.parse_known_args")
    @patch("eva.eva_cmd_client.start_cmd_client")
    def test_main_without_cmd_arguments(
        self, mock_start_cmd_client, mock_parse_known_args
    ):
        # Set up the mock to simulate missing command-line arguments
        mock_parse_known_args.return_value = (
            argparse.Namespace(host=None, port=None),
            [],
        )

        # Mock the ConfigurationManager's get_value method
        with patch.object(
            ConfigurationManager, "get_value", return_value="default_value"
        ) as mock_get_value:
            # Call the function under test
            main()

            # Assert that the mocked functions were called correctly
            mock_start_cmd_client.assert_called_once_with(
                "default_value", "default_value"
            )
            mock_get_value.assert_has_calls(
                [call("server", "host"), call("server", "port")]
            )
