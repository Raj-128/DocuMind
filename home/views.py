from django.shortcuts import render
from home.rag_logic import get_pdf_text, get_text_chunks, get_vector_store, process_user_question, generate_summary
from home.models import ChatMessage 

def index(request):
    latest_answer = None
    should_animate = False

    # 1. Clear Chat on Refresh (GET request)
    if request.method == 'GET':
        ChatMessage.objects.all().delete()

    if request.method == 'POST':
        # -----------------------------------------------
        # OPTION A: Handle PDF Upload
        # -----------------------------------------------
        if 'pdf_files' in request.FILES:
            pdf_docs = request.FILES.getlist('pdf_files')
            if pdf_docs:
                raw_text = get_pdf_text(pdf_docs)
                text_chunks = get_text_chunks(raw_text)
                get_vector_store(text_chunks)
                
                # Clear DB on new upload and notify user
                ChatMessage.objects.all().delete() 
                ChatMessage.objects.create(role='ai', content='✅ New document processed successfully! You can now ask questions or request a summary.')

        # -----------------------------------------------
        # OPTION B: Handle Summarize
        # -----------------------------------------------
        elif 'action_summarize' in request.POST:
            # 1. Save User Command
            ChatMessage.objects.create(role='user', content="📝 Summarize Document")
            
            # 2. Generate Summary
            answer_text = generate_summary()
            
            # 3. Save AI Answer
            ChatMessage.objects.create(role='ai', content=answer_text)
            latest_answer = answer_text
            should_animate = True

        # -----------------------------------------------
        # OPTION C: Handle Normal Question
        # -----------------------------------------------
        elif 'user_question' in request.POST:
            user_question = request.POST['user_question']
            if user_question:
                # 1. Save User Question
                ChatMessage.objects.create(role='user', content=user_question)
                
                # 2. Get AI Answer
                answer_text = process_user_question(user_question)
                
                # 3. Save AI Answer
                ChatMessage.objects.create(role='ai', content=answer_text)
                
                latest_answer = answer_text
                should_animate = True

    # --- Final Render ---
    history = ChatMessage.objects.all()
    if not history:
         history = [{'role': 'ai', 'content': '👋 Heyo! Champ, let\'s dive into the Document.'}]

    return render(request, 'home.html', {
        'chat_history': history,
        'should_animate': should_animate,
        'latest_answer': latest_answer
    })