
from django.shortcuts import render
from home.rag_logic import (
    get_pdf_text,
    get_text_chunks,
    get_vector_store,
    process_user_question,
    generate_summary,
)

from home.models import ChatMessage, UploadedDocument


def index(request):

    latest_answer = None
    should_animate = False

    if not request.session.session_key:
        request.session.create()

    session_id = request.session.session_key

    if request.method == "POST":

        # Upload PDF
        if "pdf_files" in request.FILES:

            pdf_docs = request.FILES.getlist("pdf_files")

            if pdf_docs:

                raw_text = get_pdf_text(pdf_docs)

                text_chunks = get_text_chunks(raw_text)

                total_pages = raw_text.count("[PAGE")
                total_chunks = len(text_chunks)

                request.session["total_pages"] = total_pages
                request.session["total_chunks"] = total_chunks

                get_vector_store(
                    text_chunks,
                    session_id
                )

                UploadedDocument.objects.filter(
                    session_id=session_id
                ).delete()

                UploadedDocument.objects.create(
                    session_id=session_id,
                    name=pdf_docs[0].name,
                )

                ChatMessage.objects.filter(
                    session_id=session_id
                ).delete()

                ChatMessage.objects.create(
                    session_id=session_id,
                    role="ai",
                    content="✅ New document processed successfully! You can now ask questions or request a summary.",
                )

        # Clear Chat
        elif "clear_chat" in request.POST:

            ChatMessage.objects.filter(
                session_id=session_id
            ).delete()

        # Summarize
        elif "action_summarize" in request.POST:

            ChatMessage.objects.create(
                session_id=session_id,
                role="user",
                content="📝 Summarize Document",
            )

            answer_text = generate_summary(session_id)

            ChatMessage.objects.create(
                session_id=session_id,
                role="ai",
                content=answer_text,
            )

            latest_answer = answer_text
            should_animate = True

        # Ask Question
        elif "user_question" in request.POST:

            user_question = request.POST["user_question"]

            if user_question:

                ChatMessage.objects.create(
                    session_id=session_id,
                    role="user",
                    content=user_question,
                )

                answer_text = process_user_question(
                    user_question,
                    session_id
                )               

                ChatMessage.objects.create(
                    session_id=session_id,
                    role="ai",
                    content=answer_text,
                )

                latest_answer = answer_text
                should_animate = True

    current_doc = UploadedDocument.objects.filter(
        session_id=session_id
    ).first()

    total_pages = request.session.get(
        "total_pages",
        0,
    )

    total_chunks = request.session.get(
        "total_chunks",
        0,
    )

    history = ChatMessage.objects.filter(
        session_id=session_id
    ).order_by("timestamp")

    if not history.exists():

        history = [
            {
                "role": "ai",
                "content": "👋 Heyo! Champ, let's dive into the Document."
            }
        ]

    return render(
        request,
        "home.html",
        {
            "chat_history": history,
            "should_animate": should_animate,
            "latest_answer": latest_answer,
            "current_doc": current_doc,
            "total_pages": total_pages,
            "total_chunks": total_chunks,
        },
    )
    