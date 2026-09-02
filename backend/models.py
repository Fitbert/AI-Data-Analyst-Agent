from pydantic import BaseModel


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    explanation: str
    sql: str
    chart_type: str
    rows: list[dict]
    row_count: int


class SchemaResponse(BaseModel):
    tables: list[dict]
