"""
知识库相关的 Pydantic Schema
"""
from pydantic import BaseModel, Field
from typing import Optional, List


class DocumentUploadResponse(BaseModel):
    """文档上传响应"""
    file_id: str
    filename: str
    chunks_count: int
    upload_time: str
    status: str = Field(default="processing", description="文件状态: processing/ready/failed")
    processing_progress: int = Field(default=0, description="处理进度 0-100")
    error_message: Optional[str] = Field(default=None, description="错误信息（失败时）")


class KnowledgeBaseStats(BaseModel):
    """知识库统计"""
    agent_name: str
    collection_name: str
    total_files: int
    total_vectors: int
    files: List[dict]
