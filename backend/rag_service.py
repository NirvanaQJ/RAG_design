import base64
import json
from typing import List, Dict, Generator

from openai import OpenAI
from sqlalchemy.orm import Session

from config import settings
from vector_store import vector_store
from database import Document


class RAGService:
    def __init__(self):
        self.client = OpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
        )

    def _build_prompt(self, question: str, retrieved_chunks: List[Dict], doc_map: Dict[int, Document]) -> str:
        context_parts = []
        for i, chunk in enumerate(retrieved_chunks):
            doc_id = chunk["doc_id"]
            doc = doc_map.get(doc_id)
            title = doc.title if doc else "未知文档"
            context_parts.append(f"[来源{i+1} - {title}]\n{chunk['content']}")

        context = "\n\n---\n\n".join(context_parts)

        system_prompt = """你是一个校园通知智能问答助手。请严格根据以下知识库内容回答用户问题。

重要规则：
1. 只能基于提供的知识库内容回答，不得使用任何外部知识
2. 如果知识库中没有相关信息，请明确告知用户"根据现有通知，未找到相关信息"
3. 回答时请引用具体的来源编号，如[来源1]、[来源2]
4. 回答要简洁、准确、有条理
5. 如果涉及时间、地点等关键信息，请务必准确引用原文"""

        user_prompt = f"""知识库内容：
{context}

用户问题：{question}

请基于以上知识库内容回答用户问题。"""

        return system_prompt, user_prompt

    def analyze_document(self, text: str) -> Dict[str, str]:
        prompt = f"""请分析以下校园通知文档的内容，提取出：
1. 通知标题（简洁准确，不超过50字）
2. 通知内容描述（概括核心信息，不超过100字）

请以JSON格式返回，格式为：{{"title": "标题", "description": "描述"}}

文档内容：
{text[:3000]}"""

        try:
            response = self.client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[
                    {"role": "system", "content": "你是一个校园通知分析助手。请从通知内容中提取标题和描述，以JSON格式返回。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=300,
            )
            result_text = response.choices[0].message.content.strip()
            if result_text.startswith("```"):
                result_text = result_text.split("\n", 1)[1].rsplit("\n```", 1)[0]
            return json.loads(result_text)
        except Exception:
            pass

        lines = text.strip().split("\n")
        first_line = lines[0].strip() if lines else "未命名通知"
        if len(first_line) > 50:
            first_line = first_line[:50] + "..."
        preview = text[:100].replace("\n", " ").strip()
        return {"title": first_line, "description": preview}

    def analyze_image(self, file_path: str) -> Dict[str, str]:
        with open(file_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else "png"
        mime_map = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "bmp": "bmp", "tiff": "tiff", "gif": "gif"}
        mime_type = f"image/{mime_map.get(ext, 'png')}"

        try:
            response = self.client.chat.completions.create(
                model=settings.VISION_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个校园通知分析助手。请从图片中的通知内容提取标题和描述，以JSON格式返回。",
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:{mime_type};base64,{image_data}"},
                            },
                            {
                                "type": "text",
                                "text": "请分析这张校园通知图片，提取出：\n1. 通知标题（简洁准确，不超过50字）\n2. 通知内容描述（概括核心信息，不超过100字）\n\n请以JSON格式返回：{\"title\": \"标题\", \"description\": \"描述\"}",
                            },
                        ],
                    },
                ],
                temperature=0.3,
                max_tokens=300,
            )
            result_text = response.choices[0].message.content.strip()
            if result_text.startswith("```"):
                result_text = result_text.split("\n", 1)[1].rsplit("\n```", 1)[0]
            return json.loads(result_text)
        except Exception:
            return {"title": "图片通知", "description": "无法识别图片内容，请手动填写标题和描述"}

    def answer(self, question: str, db: Session) -> Dict:
        retrieved_chunks = vector_store.search(question)

        retrieved_chunks = [c for c in retrieved_chunks if c["score"] >= settings.RETRIEVAL_MIN_SCORE]

        if not retrieved_chunks:
            return {
                "answer": "抱歉，根据现有通知，未找到与您问题相关的信息。请尝试其他关键词查询。",
                "sources": [],
            }

        doc_ids = list(set(chunk["doc_id"] for chunk in retrieved_chunks))
        docs = db.query(Document).filter(Document.id.in_(doc_ids)).all()
        doc_map = {doc.id: doc for doc in docs}

        system_prompt, user_prompt = self._build_prompt(question, retrieved_chunks, doc_map)

        try:
            response = self.client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=1000,
            )
            answer = response.choices[0].message.content
        except Exception as e:
            answer = f"AI服务暂时不可用，以下是检索到的相关内容：\n\n"
            for chunk in retrieved_chunks[:3]:
                doc = doc_map.get(chunk["doc_id"])
                title = doc.title if doc else "未知"
                answer += f"【{title}】{chunk['content'][:200]}...\n\n"

        sources = []
        seen_doc_ids = set()
        for chunk in retrieved_chunks:
            doc_id = chunk["doc_id"]
            if doc_id not in seen_doc_ids:
                seen_doc_ids.add(doc_id)
                doc = doc_map.get(doc_id)
                if doc:
                    sources.append({
                        "doc_id": doc.id,
                        "title": doc.title,
                        "url": doc.original_url,
                        "description": doc.description,
                        "relevance_score": round(chunk["score"], 4),
                    })

        return {
            "answer": answer,
            "sources": sources,
        }

    def answer_stream(self, question: str, db: Session) -> Generator[str, None, None]:
        retrieved_chunks = vector_store.search(question)

        retrieved_chunks = [c for c in retrieved_chunks if c["score"] >= settings.RETRIEVAL_MIN_SCORE]

        if not retrieved_chunks:
            yield "data: " + json.dumps({"type": "answer", "content": "抱歉，根据现有通知，未找到与您问题相关的信息。请尝试其他关键词查询。"}, ensure_ascii=False) + "\n\n"
            yield "data: " + json.dumps({"type": "sources", "sources": []}, ensure_ascii=False) + "\n\n"
            yield "data: [DONE]\n\n"
            return

        doc_ids = list(set(chunk["doc_id"] for chunk in retrieved_chunks))
        docs = db.query(Document).filter(Document.id.in_(doc_ids)).all()
        doc_map = {doc.id: doc for doc in docs}

        system_prompt, user_prompt = self._build_prompt(question, retrieved_chunks, doc_map)

        yield "data: " + json.dumps({"type": "thinking", "content": "正在检索相关知识库内容..."}, ensure_ascii=False) + "\n\n"

        try:
            stream = self.client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=1000,
                stream=True,
            )

            full_answer = ""
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    token = chunk.choices[0].delta.content
                    full_answer += token
                    yield "data: " + json.dumps({"type": "answer", "content": token}, ensure_ascii=False) + "\n\n"

        except Exception:
            fallback = "AI服务暂时不可用，以下是检索到的相关内容：\n\n"
            for chunk in retrieved_chunks[:3]:
                doc = doc_map.get(chunk["doc_id"])
                title = doc.title if doc else "未知"
                fallback += f"【{title}】{chunk['content'][:200]}...\n\n"
            yield "data: " + json.dumps({"type": "answer", "content": fallback}, ensure_ascii=False) + "\n\n"

        sources = []
        seen_doc_ids = set()
        for chunk in retrieved_chunks:
            doc_id = chunk["doc_id"]
            if doc_id not in seen_doc_ids:
                seen_doc_ids.add(doc_id)
                doc = doc_map.get(doc_id)
                if doc:
                    sources.append({
                        "doc_id": doc.id,
                        "title": doc.title,
                        "url": doc.original_url,
                        "description": doc.description,
                        "relevance_score": round(chunk["score"], 4),
                    })

        yield "data: " + json.dumps({"type": "sources", "sources": sources}, ensure_ascii=False) + "\n\n"
        yield "data: [DONE]\n\n"


rag_service = RAGService()
