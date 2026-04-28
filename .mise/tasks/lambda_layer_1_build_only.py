# -*- coding: utf-8 -*-
# mise description="Build Lambda layer in Docker container (local build only, no upload/publish)"

from yq_credit_card_compliance_data_lake.api import one

one.build_lambda_layer_only()
