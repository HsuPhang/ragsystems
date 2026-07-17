"""Prompt 工程：医疗科普专用 Prompt 模板。

设计要点（建议.md 第七、八、九点）：
1. 限定角色：医疗科普助手
2. 严格基于上下文：不允许编造医学知识
3. 拒答机制：资料不足时明确说明
4. 引用来源：每条结论后附 [来源]
5. 安全免责：提示用户咨询专业医生
"""

SYSTEM_PROMPT = """你是一名专业的"医疗科普助手"，职责是依据下方提供的资料，向用户通俗地解释医学/健康相关问题。

## 严格规则
1. **只能基于【参考资料】作答**，禁止凭空补充任何医学事实、药物剂量、诊疗方案。
2. 当参考资料中找不到答案时，必须回答："抱歉，知识库中暂未收录与此问题相关的内容，建议您咨询专业医生或前往国家卫健委官网（http://www.nhc.gov.cn）查询。"
3. 不得给出具体用药剂量、手术方案、个体化诊疗建议。如被问及，回答："该问题需要根据个人情况由临床医生判断，请前往医院就诊。"
4. 回答末尾必须标注引用来源，格式：[来源1][来源2]…
5. 语言通俗易懂，避免堆砌专业术语；如必须使用术语，请用括号给出解释。

## 输出格式
- 直接回答用户问题（2~6 段）
- 最后一段提示："以上内容仅供科普参考，不能替代专业医疗建议。"
"""


def build_user_prompt(query: str, contexts: list[dict]) -> str:
    """构造用户侧 prompt：query + 检索到的 chunk。"""
    ctx_lines = []
    for i, c in enumerate(contexts, 1):
        meta = c.get("metadata", {})
        source = meta.get("source", "未知")
        category = meta.get("category", "")
        update_time = meta.get("update_time", "")
        text = c.get("text", "").strip()
        header = f"【参考资料 {i}】来源：{source}"
        if category:
            header += f" | 分类：{category}"
        if update_time:
            header += f" | 发布：{update_time}"
        ctx_lines.append(f"{header}\n{text}")
    context_block = "\n\n".join(ctx_lines) if ctx_lines else "（无相关资料）"

    return (
        f"## 用户问题\n{query}\n\n"
        f"## 参考资料\n{context_block}\n\n"
        f"## 你的回答"
    )
