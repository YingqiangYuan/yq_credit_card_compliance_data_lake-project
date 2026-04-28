# -*- coding: utf-8 -*-
# mise description="Full Lambda layer pipeline: Build → Zip → Upload (S3) → Publish (AWS Lambda)"

from yq_credit_card_compliance_data_lake.api import one

one.build_lambda_layer_in_container()
