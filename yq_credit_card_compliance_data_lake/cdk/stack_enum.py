# -*- coding: utf-8 -*-

"""
Stack enumeration — single entry point for all CDK stacks.

**Why ``StackEnum`` instead of bare variables?**

A CDK app typically has multiple stacks, and each stack may depend on the
``one`` singleton for configuration.  ``StackEnum`` wraps them behind
``@cached_property`` so that:

1. **Stacks are only synthesized when accessed** — if ``cdk_app.py`` only
   touches ``stack_enum.lambda_stack``, the infra stack is never constructed.
   This is useful during development when you want to iterate on a single
   stack without waiting for the full app to synthesize.

2. **Import-time side effects are avoided** — each ``cached_property`` uses a
   local import (``from .stacks.infra_stack import InfraStack``) so that heavy
   CDK modules are loaded on demand, not at module import time.

3. **IDE-friendly** — ``stack_enum.infra_stack`` gives autocomplete and
   type inference, unlike a plain ``dict`` or dynamic lookup.

4. **Adding a new stack** is mechanical: create the stack class, add a
   ``@cached_property`` here, and access it in ``cdk_app.py``.
"""

import dataclasses
from functools import cached_property

import aws_cdk as cdk

from ..one.api import one


@dataclasses.dataclass
class StackEnum:
    """
    Registry of all CDK stacks in this project.

    Each stack is exposed as a ``@cached_property`` — constructed once on first
    access, then reused.
    """

    app: cdk.App = dataclasses.field()

    @cached_property
    def infra_stack(self):
        """Long-lived infrastructure stack (IAM roles, policies)."""
        from .stacks.infra_stack import InfraStack

        return InfraStack(
            scope=self.app,
            one=one,
        )

    @cached_property
    def lambda_stack(self):
        """Frequently-deployed compute stack (Lambda functions, layers, events)."""
        from .stacks.lambda_stack import LambdaStack

        return LambdaStack(
            scope=self.app,
            one=one,
        )


# Create the global stack enumeration instance
app = cdk.App()

stack_enum = StackEnum(app=app)
"""
Module-level singleton — import this from ``cdk_app.py`` to synthesize stacks.
"""
