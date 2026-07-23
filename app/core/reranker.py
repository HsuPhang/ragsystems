"""重排序层：BAAI/bge-reranker-large 二次重排。

为什么需要 Reranker：
- Embedding 检索速度快但粒度粗（语义近似）
- Cross-Encoder Reranker 精确但慢
- 工程实践：Embedding Top10 → Rerank Top5 给 LLM

注意：模型加载较重，惰性加载，避免启动时卡住。
支持两种格式：
- PyTorch 格式（model.safetensors / pytorch_model.bin）
- ONNX 格式（onnx/model.onnx）
"""
from __future__ import annotations

from pathlib import Path

from app.config import settings
from app.core.retriever import RetrievalResult
from app.utils import detect_device, logger

_reranker = None
_reranker_type = None


def _has_pytorch_model(model_path: str) -> bool:
    """检查是否存在 PyTorch 格式的权重文件。"""
    p = Path(model_path)
    return (p / "model.safetensors").exists() or (p / "pytorch_model.bin").exists()


def _has_onnx_model(model_path: str) -> bool:
    """检查是否存在 ONNX 格式的权重文件。"""
    p = Path(model_path)
    return (p / "onnx" / "model.onnx").exists()


def get_reranker():
    """单例重排序模型（惰性加载）。"""
    global _reranker, _reranker_type
    if _reranker is not None:
        return _reranker

    model_path = settings.RERANKER_MODEL_PATH

    if _has_pytorch_model(model_path):
        device = detect_device(settings.RERANKER_DEVICE)
        _reranker_type = "pytorch"
        logger.info(f"加载 Reranker 模型 (PyTorch): {model_path} (device={device})")
        from sentence_transformers import CrossEncoder
        _reranker = CrossEncoder(
            model_path,
            device=device,
            max_length=512,
        )
        logger.info("Reranker 模型加载完成")
    elif _has_onnx_model(model_path):
        device = detect_device(settings.RERANKER_DEVICE)
        _reranker_type = "onnx"
        logger.info(f"加载 Reranker 模型 (ONNX): {model_path} (device={device})")
        try:
            import onnxruntime as ort
            from transformers import AutoTokenizer

            tokenizer = AutoTokenizer.from_pretrained(model_path)
            onnx_path = str(Path(model_path) / "onnx" / "model.onnx")
            providers = ["CPUExecutionProvider"]
            if device.lower() == "cuda":
                providers.insert(0, "CUDAExecutionProvider")
            session = ort.InferenceSession(onnx_path, providers=providers)
            _reranker = (tokenizer, session)
            logger.info("Reranker ONNX 模型加载完成")
        except ImportError as e:
            logger.error(f"ONNX 模型加载失败，缺少依赖: {e}")
            logger.error("请安装依赖: pip install onnxruntime onnx")
            raise
    else:
        device = detect_device(settings.RERANKER_DEVICE)
        logger.info(f"本地模型路径无效，尝试从 HuggingFace 下载: {model_path} (device={device})")
        from sentence_transformers import CrossEncoder
        _reranker_type = "pytorch"
        _reranker = CrossEncoder(
            model_path,
            device=device,
            max_length=512,
        )
        logger.info("Reranker 模型下载并加载完成")

    return _reranker


def _predict_pytorch(model, pairs):
    """PyTorch 模型预测。"""
    return model.predict(pairs, show_progress_bar=False)


def _predict_onnx(model, pairs):
    """ONNX 模型预测。"""
    tokenizer, session = model
    import torch

    all_scores = []
    for query, text in pairs:
        inputs = tokenizer(
            query, text,
            max_length=512,
            padding="max_length",
            truncation=True,
            return_tensors="np",
        )
        input_ids = inputs["input_ids"]
        attention_mask = inputs["attention_mask"]
        token_type_ids = inputs.get("token_type_ids", None)

        onnx_inputs = {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
        }
        if token_type_ids is not None:
            onnx_inputs["token_type_ids"] = token_type_ids

        logits = session.run(None, onnx_inputs)[0]
        score = float(torch.sigmoid(torch.tensor(logits[0][1])).item())
        all_scores.append(score)
    return all_scores


def rerank(
    query: str,
    result: RetrievalResult,
    top_n: int | None = None,
) -> RetrievalResult:
    """对 RetrievalResult 中的 nodes 重新打分并截断到 top_n。"""
    if result.rejected or not result.nodes:
        return result
    top_n = top_n or settings.RERANK_TOP_N

    model = get_reranker()
    pairs = [(query, n.node.get_content()[:1024]) for n in result.nodes]

    if _reranker_type == "onnx":
        scores = _predict_onnx(model, pairs)
    else:
        scores = _predict_pytorch(model, pairs)

    ranked = sorted(
        zip(result.nodes, scores),
        key=lambda x: float(x[1]),
        reverse=True,
    )[:top_n]

    from llama_index.core.schema import NodeWithScore
    new_nodes = [
        NodeWithScore(node=n.node, score=float(s))
        for n, s in ranked
    ]
    result.nodes = new_nodes
    result.top_score = new_nodes[0].score if new_nodes else 0.0
    logger.info(f"Rerank 完成: {len(pairs)} -> {len(new_nodes)}")
    return result
