import json
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db, QueryHistory, User, Conversation, Bookmark
from auth import get_current_user
from rag_service import rag_service

router = APIRouter(prefix="/api/qa", tags=["智能问答"])


class QuestionRequest(BaseModel):
    question: str


class SourceInfo(BaseModel):
    doc_id: int
    title: str
    url: str
    description: str
    relevance_score: float


class AnswerResponse(BaseModel):
    answer: str
    sources: list


@router.post("/ask")
def ask_question(
    req: QuestionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = rag_service.answer(req.question, db)

    history = QueryHistory(
        user_id=current_user.id,
        question=req.question,
        answer=result["answer"],
        sources=json.dumps(result["sources"], ensure_ascii=False),
    )
    db.add(history)
    db.commit()

    return result


@router.post("/ask/stream")
def ask_question_stream(
    req: QuestionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    def generate():
        full_answer = ""
        for event in rag_service.answer_stream(req.question, db):
            if event.startswith("data: [DONE]"):
                break
            data = json.loads(event[6:])
            if data.get("type") == "answer":
                full_answer += data["content"]
            yield event

        history = QueryHistory(
            user_id=current_user.id,
            question=req.question,
            answer=full_answer,
            sources="[]",
        )
        db.add(history)
        db.commit()

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/history")
def get_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    records = (
        db.query(QueryHistory)
        .filter(QueryHistory.user_id == current_user.id)
        .order_by(QueryHistory.created_at.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "id": r.id,
            "question": r.question,
            "answer": r.answer,
            "sources": json.loads(r.sources) if r.sources else [],
            "created_at": r.created_at.isoformat(),
        }
        for r in records
    ]


@router.delete("/history/{history_id}")
def delete_history(
    history_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = db.query(QueryHistory).filter(
        QueryHistory.id == history_id,
        QueryHistory.user_id == current_user.id,
    ).first()
    if not record:
        from fastapi import HTTPException
        raise HTTPException(404, "记录不存在")

    db.delete(record)
    db.commit()
    return {"message": "记录已删除"}


class SaveConversationRequest(BaseModel):
    title: str
    messages: list


@router.post("/conversations")
def save_conversation(
    req: SaveConversationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = Conversation(
        user_id=current_user.id,
        title=req.title,
        messages=json.dumps(req.messages, ensure_ascii=False),
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    return {
        "id": conversation.id,
        "title": conversation.title,
        "created_at": conversation.created_at.isoformat(),
        "updated_at": conversation.updated_at.isoformat(),
    }


@router.get("/conversations")
def list_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversations = (
        db.query(Conversation)
        .filter(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )
    return [
        {
            "id": c.id,
            "title": c.title,
            "message_count": len(json.loads(c.messages)) if c.messages else 0,
            "created_at": c.created_at.isoformat(),
            "updated_at": c.updated_at.isoformat(),
        }
        for c in conversations
    ]


@router.get("/conversations/{conversation_id}")
def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
        .first()
    )
    if not conversation:
        from fastapi import HTTPException
        raise HTTPException(404, "对话记录不存在")

    return {
        "id": conversation.id,
        "title": conversation.title,
        "messages": json.loads(conversation.messages) if conversation.messages else [],
        "created_at": conversation.created_at.isoformat(),
        "updated_at": conversation.updated_at.isoformat(),
    }


@router.put("/conversations/{conversation_id}")
def update_conversation(
    conversation_id: int,
    req: SaveConversationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
        .first()
    )
    if not conversation:
        from fastapi import HTTPException
        raise HTTPException(404, "对话记录不存在")

    conversation.title = req.title
    conversation.messages = json.dumps(req.messages, ensure_ascii=False)
    db.commit()
    db.refresh(conversation)

    return {
        "id": conversation.id,
        "title": conversation.title,
        "created_at": conversation.created_at.isoformat(),
        "updated_at": conversation.updated_at.isoformat(),
    }


@router.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
        .first()
    )
    if not conversation:
        from fastapi import HTTPException
        raise HTTPException(404, "对话记录不存在")

    db.delete(conversation)
    db.commit()
    return {"message": "对话记录已删除"}


class BookmarkRequest(BaseModel):
    message_id: str
    conversation_id: int | None = None
    question: str
    answer_summary: str
    full_answer: str
    sources: list = []


@router.post("/bookmarks")
def add_bookmark(
    req: BookmarkRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing = (
        db.query(Bookmark)
        .filter(
            Bookmark.user_id == current_user.id,
            Bookmark.message_id == req.message_id,
        )
        .first()
    )
    if existing:
        return {"id": existing.id, "message": "已收藏"}

    bookmark = Bookmark(
        user_id=current_user.id,
        conversation_id=req.conversation_id,
        message_id=req.message_id,
        question=req.question,
        answer_summary=req.answer_summary[:200],
        full_answer=req.full_answer,
        sources=json.dumps(req.sources, ensure_ascii=False),
    )
    db.add(bookmark)
    db.commit()
    db.refresh(bookmark)

    return {
        "id": bookmark.id,
        "message_id": bookmark.message_id,
        "created_at": bookmark.created_at.isoformat(),
    }


@router.delete("/bookmarks/{bookmark_id}")
def remove_bookmark(
    bookmark_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    bookmark = (
        db.query(Bookmark)
        .filter(
            Bookmark.id == bookmark_id,
            Bookmark.user_id == current_user.id,
        )
        .first()
    )
    if not bookmark:
        from fastapi import HTTPException
        raise HTTPException(404, "收藏记录不存在")

    db.delete(bookmark)
    db.commit()
    return {"message": "已取消收藏"}


@router.delete("/bookmarks/by-message/{message_id}")
def remove_bookmark_by_message(
    message_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    bookmark = (
        db.query(Bookmark)
        .filter(
            Bookmark.user_id == current_user.id,
            Bookmark.message_id == message_id,
        )
        .first()
    )
    if not bookmark:
        from fastapi import HTTPException
        raise HTTPException(404, "收藏记录不存在")

    db.delete(bookmark)
    db.commit()
    return {"message": "已取消收藏"}


@router.get("/bookmarks")
def list_bookmarks(
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    total = (
        db.query(Bookmark)
        .filter(Bookmark.user_id == current_user.id)
        .count()
    )

    bookmarks = (
        db.query(Bookmark)
        .filter(Bookmark.user_id == current_user.id)
        .order_by(Bookmark.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": b.id,
                "message_id": b.message_id,
                "conversation_id": b.conversation_id,
                "question": b.question,
                "answer_summary": b.answer_summary,
                "full_answer": b.full_answer,
                "sources": json.loads(b.sources) if b.sources else [],
                "created_at": b.created_at.isoformat(),
            }
            for b in bookmarks
        ],
    }


@router.get("/bookmarks/ids")
def get_bookmarked_ids(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    bookmarks = (
        db.query(Bookmark.message_id)
        .filter(Bookmark.user_id == current_user.id)
        .all()
    )
    return {"ids": [b[0] for b in bookmarks]}


@router.get("/bookmarks/{bookmark_id}/navigate")
def navigate_bookmark(
    bookmark_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    bookmark = (
        db.query(Bookmark)
        .filter(
            Bookmark.id == bookmark_id,
            Bookmark.user_id == current_user.id,
        )
        .first()
    )
    if not bookmark:
        from fastapi import HTTPException
        raise HTTPException(404, "收藏记录不存在")

    conversation = None

    if bookmark.conversation_id:
        conversation = (
            db.query(Conversation)
            .filter(
                Conversation.id == bookmark.conversation_id,
                Conversation.user_id == current_user.id,
            )
            .first()
        )

    if not conversation and not bookmark.conversation_id:
        user_conversations = (
            db.query(Conversation)
            .filter(Conversation.user_id == current_user.id)
            .all()
        )
        for conv in user_conversations:
            try:
                msgs = json.loads(conv.messages) if conv.messages else []
                for m in msgs:
                    if str(m.get("id", "")) == str(bookmark.message_id):
                        conversation = conv
                        bookmark.conversation_id = conv.id
                        db.commit()
                        break
            except (json.JSONDecodeError, TypeError):
                continue
            if conversation:
                break

    if not conversation:
        return {
            "status": "not_found",
            "message": "该收藏对应的对话记录未找到，可能已被删除",
        }

    return {
        "status": "ok",
        "conversation": {
            "id": conversation.id,
            "title": conversation.title,
            "messages": json.loads(conversation.messages) if conversation.messages else [],
            "created_at": conversation.created_at.isoformat(),
            "updated_at": conversation.updated_at.isoformat(),
        },
        "target_message_id": bookmark.message_id,
    }
