from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RepositoryCreate(BaseModel):
    owner: str = Field(min_length=1, max_length=255)
    name: str = Field(min_length=1, max_length=255)
    full_name: str = Field(min_length=1, max_length=511)
    github_repo_id: int
    default_branch: str = Field(default="main", min_length=1, max_length=255)
    description: str | None = None
    is_private: bool = False
    clone_url: str = Field(min_length=1, max_length=2048)


class RepositoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner: str
    name: str
    full_name: str
    github_repo_id: int
    default_branch: str
    description: str | None
    is_private: bool
    clone_url: str
