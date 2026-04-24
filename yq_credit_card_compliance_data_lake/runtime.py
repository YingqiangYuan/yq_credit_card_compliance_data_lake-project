# -*- coding: utf-8 -*-

"""
Runtime environment detection for multi-context applications.

This module provides centralized runtime environment detection capabilities essential for
cloud-native applications that run across multiple execution contexts, enabling environment-aware
configuration and resource management without scattered conditional logic throughout the codebase.

.. seealso::

    :ref:`Understand-Runtime`
"""

import which_runtime.api as which_runtime


class Runtime(which_runtime.Runtime):
    """
    Runtime environment detection class for context-aware application behavior.

    Extends the base runtime detection to provide centralized identification of execution
    contexts including local development, CI/CD pipelines, and AWS compute environments,
    enabling consistent environment-aware configuration and resource access patterns.
    """


runtime = Runtime()
