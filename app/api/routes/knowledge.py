"""知识库管理接口（管理员专用）。"""
from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.auth import get_current_admin
from llama_index.core import Document as LIDocument
from app.api.schemas import (
    DocumentItem,
    DocumentListResponse,
    DocumentUpdateRequest,
    GenericResponse,
)
from app.config import settings
from app.core.preprocess import build_nodes_from_dir, enrich_node_metadata, split_documents
from app.core.vector_store import add_nodes, delete_by_doc_id, reset_collection
from app.db import Admin, Document, SystemLog, get_db
from app.utils import gen_id, logger

router = APIRouter(prefix="/api/knowledge", tags=["知识库管理"])

ALLOWED_EXTS = {".pdf", ".txt", ".md", ".docx", ".html"}


@router.get("/documents", response_model=DocumentListResponse)
def list_documents(
    admin: Annotated[Admin, Depends(get_current_admin)],
    db: Annotated[Session, Depends(get_db)],
    page: int = 1,
    page_size: int = 20,
    keyword: str = "",
    category: str = "",
) -> DocumentListResponse:
    q = db.query(Document).filter(Document.status == "active")
    if keyword:
        kw = f"%{keyword}%"
        q = q.filter((Document.title.like(kw)) | (Document.source.like(kw)))
    if category:
        q = q.filter(Document.category == category)
    total = q.count()
    rows = (
        q.order_by(Document.created_at.desc())
        .offset(max(0, (page - 1) * page_size))
        .limit(page_size)
        .all()
    )
    return DocumentListResponse(
        total=total,
        items=[DocumentItem.model_validate(r) for r in rows],
    )


@router.post("/upload", response_model=GenericResponse)
async def upload_document(
    admin: Annotated[Admin, Depends(get_current_admin)],
    db: Annotated[Session, Depends(get_db)],
    file: UploadFile = File(...),
    title: str = Form(""),
    source: str = Form(""),
    category: str = Form("未分类"),
    author: str = Form(""),
    update_time: str = Form(""),
    keywords: str = Form(""),  # 逗号分隔
) -> GenericResponse:
    """上传文档并自动入库。"""
    # 1. 后缀检查
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTS:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {suffix}")

    # 2. 落盘
    upload_dir: Path = settings.resolve("UPLOAD_DIR")
    upload_dir.mkdir(parents=True, exist_ok=True)
    doc_id = gen_id("doc")
    save_path = upload_dir / f"{doc_id}{suffix}"
    content = await file.read()
    save_path.write_bytes(content)

    # 3. 解析 + 分块
    if suffix == ".pdf":
        from llama_index.core import SimpleDirectoryReader
        reader = SimpleDirectoryReader(input_files=[str(save_path)])
        li_docs = reader.load_data()
    else:
        text = content.decode("utf-8", errors="ignore")
        li_docs = [LIDocument(text=text, metadata={"file_name": file.filename})]

    kw_list = [k.strip() for k in keywords.split(",") if k.strip()]
    kw_str = ", ".join(kw_list)
    for d in li_docs:
        d.metadata.update({
            "source": source or file.filename or "未知",
            "category": category or "未分类",
            "author": author,
            "update_time": update_time,
            "keywords": kw_str,
            "doc_id": doc_id,
        })

    nodes = split_documents(li_docs)
    nodes = [
        enrich_node_metadata(n, extra={
            "doc_id": doc_id,
            "source": source or file.filename or "未知",
            "category": category or "未分类",
            "author": author,
            "update_time": update_time,
            "keywords": kw_str,
        })
        for n in nodes
    ]

    # 4. 入向量库
    add_nodes(nodes)

    # 5. 写 MySQL
    db.add(Document(
        doc_id=doc_id,
        title=title or file.filename or "",
        source=source or file.filename or "",
        category=category or "未分类",
        author=author,
        file_path=str(save_path),
        file_type=suffix.lstrip("."),
        file_size=len(content),
        chunk_count=len(nodes),
        keywords=kw_list,
    ))
    db.add(SystemLog(
        level="INFO", module="knowledge", action="upload",
        message=f"上传文档: {file.filename}, chunks={len(nodes)}",
        operator=admin.username,
    ))
    db.commit()

    return GenericResponse(
        message=f"已入库 {len(nodes)} 个 chunk",
        data={"doc_id": doc_id, "chunk_count": len(nodes)},
    )


@router.put("/documents/{doc_id}", response_model=GenericResponse)
def update_document(
    doc_id: str,
    req: DocumentUpdateRequest,
    admin: Annotated[Admin, Depends(get_current_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> GenericResponse:
    doc = db.query(Document).filter(Document.doc_id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    if req.title is not None:
        doc.title = req.title
    if req.source is not None:
        doc.source = req.source
    if req.category is not None:
        doc.category = req.category
    if req.author is not None:
        doc.author = req.author
    if req.keywords is not None:
        doc.keywords = req.keywords
    db.add(SystemLog(
        level="INFO", module="knowledge", action="update",
        message=f"更新文档: {doc_id}", operator=admin.username,
    ))
    db.commit()
    return GenericResponse(message="已更新")


@router.delete("/documents/{doc_id}", response_model=GenericResponse)
def delete_document(
    doc_id: str,
    admin: Annotated[Admin, Depends(get_current_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> GenericResponse:
    doc = db.query(Document).filter(Document.doc_id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    # 1. 删向量
    n = delete_by_doc_id(doc_id)

    # 2. 删文件
    if doc.file_path and Path(doc.file_path).exists():
        try:
            Path(doc.file_path).unlink()
        except Exception as e:
            logger.warning(f"删除文件失败: {doc.file_path}, 错误: {e}")

    # 3. 软删
    doc.status = "deleted"
    db.add(SystemLog(
        level="INFO", module="knowledge", action="delete",
        message=f"删除文档: {doc_id}, chunks={n}", operator=admin.username,
    ))
    db.commit()
    return GenericResponse(message=f"已删除（向量 {n} 条）")


@router.post("/rebuild", response_model=GenericResponse)
def rebuild_index(
    admin: Annotated[Admin, Depends(get_current_admin)],
):
    """根据上传目录重建整个索引（谨慎，会清空向量库）。"""
    reset_collection()
    upload_dir = settings.resolve("UPLOAD_DIR")
    nodes = build_nodes_from_dir(upload_dir)
    if not nodes:
        return GenericResponse(message="无文件，跳过")
    add_nodes(nodes)
    return GenericResponse(message=f"重建完成，共 {len(nodes)} 个 chunk")
