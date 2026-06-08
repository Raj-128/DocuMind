import os
import re 
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from groq import Groq
from home.models import ChatMessage

load_dotenv()

# ==========================================================
# 1. EXTRACT TEXT (With Page Tags)
# ==========================================================
def get_pdf_text(pdf_docs):
    text = ""
    for pdf in pdf_docs:
        pdf_reader = PdfReader(pdf)
        for i, page in enumerate(pdf_reader.pages):
            page_content = page.extract_text()
            if page_content:
                # Tag every page so we can find it later
                text += f"\n[PAGE {i+1}]\n{page_content}"
    return text

# ==========================================================
# 2. SPLIT TEXT
# ==========================================================
def get_text_chunks(text):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_text(text)
    return chunks

# ==========================================================
# 3. VECTOR STORE
# ==========================================================
def get_vector_store(text_chunks, session_id):
    from langchain_huggingface import HuggingFaceEndpointEmbeddings
    embeddings = HuggingFaceEndpointEmbeddings(
        model="sentence-transformers/all-MiniLM-L6-v2",
        huggingfacehub_api_token=os.getenv("HF_TOKEN")
)
    vector_store = FAISS.from_texts(text_chunks, embedding=embeddings)
    faiss_path = f"faiss_indexes/{session_id}"
    vector_store.save_local(faiss_path)

def get_chat_history_string():
    # Get last 5 messages from DB to maintain context
    messages = ChatMessage.objects.all().order_by('-id')[:5]
    # Reverse them to be in chronological order
    history_text = ""
    for msg in reversed(messages):
        history_text += f"{msg.role.upper()}: {msg.content}\n"
    return history_text

# ==========================================================
# 4. ASK GROQ (Strictly Text Only)
# ==========================================================
def ask_groq(context_text, user_question):
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    
    conversation_history = get_chat_history_string()

    # --- PROMPT: Explicitly bans Mermaid/Graphs ---
    prompt = f"""
    You are a smart enterprise assistant. 
    1. Use the Context and Conversation History below to answer.
    2. If the user asks a follow-up question (like "what about him?"), use the History.
    3. Keep answers concise, professional, and use bullet points where possible.
    4. STRICTLY DO NOT use Markdown asterisks (*) for lists. Use Unicode bullets (•) instead.
    5. STRICTLY DO NOT use Mermaid diagrams, graphs, charts, or code blocks for visualization. 
    6. Output ONLY standard text and emojis.

    --- CONVERSATION HISTORY ---
    {conversation_history}
    
    --- NEW CONTEXT ---
    {context_text}

    --- USER QUESTION ---
    {user_question}
    """
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

# ==========================================================
# 5. MAIN LOGIC (Extracts Sources)
# ==========================================================
def process_user_question(user_question, session_id):
    
    from langchain_huggingface import HuggingFaceEndpointEmbeddings
    embeddings = HuggingFaceEndpointEmbeddings(
        model="sentence-transformers/all-MiniLM-L6-v2",
        huggingfacehub_api_token=os.getenv("HF_TOKEN")
)
    try:
        faiss_path = f"faiss_indexes/{session_id}"

        new_db = FAISS.load_local(
            faiss_path,
            embeddings,
            allow_dangerous_deserialization=True
    )
    except:
        return "⚠️ Please upload a PDF first."
    
    docs = new_db.similarity_search(user_question)
    
    # 🔍 Extract Page Numbers
    sources = []
    for doc in docs:
        match = re.search(r'\[PAGE (\d+)\]', doc.page_content)
        if match:
            sources.append(match.group(1))
    
    unique_sources = sorted(list(set(sources)), key=lambda x: int(x))
    source_string = ", ".join(unique_sources)
    
    context_text = "\n\n".join([doc.page_content for doc in docs])
    answer = ask_groq(context_text, user_question)
    
    # Add Citations to the answer
    if unique_sources:
        return f"{answer}\n\n🔍 Sources: Page {source_string}"
    
    return answer

# ==========================================================
# 6. GENERATE SUMMARY (Strictly Text Only)
# ==========================================================
def generate_summary(session_id):
    from langchain_huggingface import HuggingFaceEndpointEmbeddings
    
    embeddings = HuggingFaceEndpointEmbeddings(
        model="sentence-transformers/all-MiniLM-L6-v2",
        huggingfacehub_api_token=os.getenv("HF_TOKEN")
)
    try:
        faiss_path = f"faiss_indexes/{session_id}"

        new_db = FAISS.load_local(
            faiss_path,
            embeddings,
            allow_dangerous_deserialization=True
        )
    except:
        return "⚠️ Please upload a PDF first."
    
    # Fetch broad context
    docs = new_db.similarity_search("overview introduction conclusion summary main points", k=8)
    context_text = "\n\n".join([doc.page_content for doc in docs])
    
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    
    # --- PROMPT: Explicitly bans Mermaid/Graphs ---
    prompt = f"""
    You are an expert analyst. 
    1. Read the context below.
    2. Provide a 5-point executive summary of the document.
    3. Start with a bold headline "📄 Document Summary".( DO NOT use asterisks)
    4. Use Unicode bullets (•) for the list points. DO NOT use asterisks (*).
    5. STRICTLY DO NOT use Mermaid diagrams, graphs, or code blocks. Use only plain text.

    Context:
    {context_text}
    """
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"