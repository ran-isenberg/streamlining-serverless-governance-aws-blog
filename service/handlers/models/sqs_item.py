from aws_lambda_powertools.utilities.parser.models import SqsRecordModel
from pydantic import BaseModel, Json


class Order(BaseModel):
    item: dict


class OrderSqsRecord(SqsRecordModel):
    body: Json[Order]  # deserialize order data from JSON string
