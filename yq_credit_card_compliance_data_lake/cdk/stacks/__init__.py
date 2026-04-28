# -*- coding: utf-8 -*-

"""
CDK stack definitions.

- ``infra_stack.py`` — long-lived IAM resources (changes rarely)
- ``lambda_stack.py`` — Lambda functions, layers, event sources (changes often)
- ``infra_stack_exports.py`` — type-safe CloudFormation export interface
"""
