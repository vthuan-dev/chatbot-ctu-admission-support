from pydantic import BaseModel, Field

class ResultSchema(BaseModel):
    title: str = Field(description="The title of the workflow")
    description: str = Field(description="The description of the workflow")
    url: str = Field(description="The URL of the workflow")
    name: str = Field(description="The name of the workflow") 