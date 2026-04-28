# -*- coding: utf-8 -*-

"""
Base classes for structured Lambda function input/output with type-safe validation.
"""

import typing as T
from pydantic import BaseModel

if T.TYPE_CHECKING:  # pragma: no cover
    from aws_lambda_powertools.utilities.typing import LambdaContext


class BaseOutput(BaseModel):
    """
    Base class for Lambda function output with automatic serialization.
    """


OutputType = T.TypeVar("OutputType", bound=BaseOutput)


class BaseInput(
    BaseModel,
    T.Generic[OutputType],
):
    """
    Base class for Lambda function input with validation and local testing capabilities.
    """

    def main(self, context: T.Optional["LambdaContext"] = None) -> "OutputType":
        """Execute the main business logic locally or in Lambda runtime."""
        raise NotImplementedError

    @classmethod
    def lambda_handler(
        cls,
        event: dict[str, T.Any],
        context: T.Optional["LambdaContext"] = None,
    ) -> dict[str, T.Any]:
        """
        AWS Lambda handler that validates input and serializes output.
        """
        input = cls(**event)
        output = input.main(context)
        return output.model_dump()


# if __name__ == "__main__":
#     class Output(BaseOutput):
#         message: str
#
#     class Input(BaseInput[BaseOutput]):
#         name: str
#
#         def main(self, context: T.Optional["LambdaContext"] = None) -> "Output":
#             return Output(message=f"hello {self.name}")
#
#     input = Input(name="Alice")
#     output = input.main()
#     print(f"{output.message = }")
