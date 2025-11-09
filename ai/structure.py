from pydantic import BaseModel, Field

class Structure(BaseModel):
    tldr: str = Field(description="generate a too long; didn't read summary")
    motivation: str = Field(description="describe the motivation in this paper in one sentence")
    method: str = Field(description="method of this paper in one sentence")
    result: str = Field(description="result of this paper in one sentence")
    conclusion: str = Field(description="conclusion of this paper in one sentence")