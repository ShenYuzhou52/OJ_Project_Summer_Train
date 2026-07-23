from pydantic import BaseModel, Field, field_validator
from typing import Optional
from enum import Enum

class Difficulty(str, Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"

class JudgeMode(str, Enum):
    standard = "standard"
    strict = "strict"
    spj = "spj"

class Sample(BaseModel):
    input: str
    output: str

class TestCase(BaseModel):
    case_id: str
    input: str
    output: str
    score: int = Field(ge = 0)
    is_hidden: bool =  False

class ProblemCreateRequest(BaseModel):
    id: str = Field(min_length = 1,max_length = 32,pattern = r"^[a-zA-Z0-9_-]+$")
    title: str = Field(min_length = 1,max_length = 100)
    description: str = Field(min_length = 1)
    input_description: str = Field(min_length = 1)
    output_description: str = Field(min_length = 1)
    samples: list[Sample] = Field(min_length = 1)
    constraints: str = ""
    time_limit: float = Field(gt = 0)
    memory_limit: float = Field(gt = 0)
    difficulty: Difficulty
    tags: list[str] = []
    test_cases: list[TestCase] = Field(min_length = 1)
    judge_mode: JudgeMode = JudgeMode.standard
    spj_code: Optional[str] = None

    @field_validator("test_cases") #指定需要校验的字段名
    @classmethod
    def test_cases_score_sum(cls, v):
        if sum(tc.score for tc in v) != 100:
            raise ValueError("测试点分值总和必须为100!")
        ids = [tc.case_id for tc in v]
        if len(ids) != len(set(ids)):
            raise ValueError("测试点编号必须两两不同！")
        return v

    @field_validator("spj_code")
    @classmethod
    def spj_code_required_when_spj(cls, v, info):
        judge_mode = info.data.get("judge_mode")
        if judge_mode == "spj" and not v:
            raise ValueError("当 judge_mode 为 spj 时必须提供 spj_code")
        return v

class ProblemUpdateRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, min_length=1)
    input_description: Optional[str] = Field(default=None, min_length=1)
    output_description: Optional[str] = Field(default=None, min_length=1)
    samples: Optional[list[Sample]] = Field(default=None, min_length=1)
    constraints: Optional[str] = None
    time_limit: Optional[float] = Field(default=None, gt=0)
    memory_limit: Optional[float] = Field(default=None, gt=0)
    difficulty: Optional[Difficulty] = None
    tags: Optional[list[str]] = None
    test_cases: Optional[list[TestCase]] = Field(default=None, min_length=1)
    judge_mode: Optional[JudgeMode] = None
    spj_code: Optional[str] = None

    @field_validator("test_cases")
    @classmethod
    def test_cases_score_sum(cls, v):
        if v is not None:
            if sum(tc.score for tc in v) != 100:
                raise ValueError("测试点分值总和必须为100!")
            ids = [tc.case_id for tc in v]
            if len(ids) != len(set(ids)):
                raise ValueError("case_id在同一题中必须相同！")
        return v

class ProblemResponse(BaseModel):
    id: str
    title: str
    description: str
    input_description: str
    output_description: str
    samples: str
    constraints: str
    time_limit: float
    memory_limit: float
    difficulty: Difficulty
    tags: list[str]
    test_cases: Optional[list[TestCase]] = None # 学生如果看不到就是None,Optional代表这个字段可以不传，不传就是None
    judge_mode: JudgeMode = JudgeMode.standard

class ProblemListItem(BaseModel):
    id: str
    title: str
    difficulty: Difficulty
    tags: list[str]
    time_limit: float
    memory_limit: float
    judge_mode: JudgeMode = JudgeMode.standard