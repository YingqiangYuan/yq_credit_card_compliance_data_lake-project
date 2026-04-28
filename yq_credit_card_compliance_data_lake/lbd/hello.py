# -*- coding: utf-8 -*-

"""
This lambda function takes a name as input and echo back ``hello {name}``
"""

from pydantic import Field

from ..logger import logger
from .base import BaseInput, BaseOutput


class Output(BaseOutput):
    """
    Lambda function output containing the greeting message.
    """
    message: str = Field()


class Input(BaseInput[Output]):
    """
    Lambda function input with name parameter for greeting generation.
    """
    name: str = Field(default="Mr X")

    @logger.pretty_log()
    def main(self, context=None) -> Output:
        """
        Generate greeting message and return formatted output.
        """
        message = f"hello {self.name}"
        logger.info(message)
        return Output(message=message)


lambda_handler = Input.lambda_handler
