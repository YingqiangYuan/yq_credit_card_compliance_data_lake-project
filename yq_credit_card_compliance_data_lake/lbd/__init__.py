# -*- coding: utf-8 -*-

"""
Lambda handler subpackage.

Each Lambda function lives in its own module (``hello.py``, ``s3sync.py``) and
follows the base class pattern defined in ``base.py``: a Pydantic ``Input``
model with a ``main()`` method for business logic, and a module-level
``lambda_handler`` function that serves as the AWS entry point.

All handlers are re-exported through ``lambda_function.py`` (one level up) so
that CDK handler paths stay simple and predictable.
"""
