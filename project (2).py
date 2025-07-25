# -*- coding: utf-8 -*-
"""PROJECT.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1ItlwO0ZNtDrGimBUh5semlqp5Hxi05KI
"""

!pip install gradio langchain langchain-community langchain-openai huggingface_hub PyPDF2 langchain-huggingface faiss-cpu langchain_groq python-dotenv fpdf

import gradio as gr
from PyPDF2 import PdfReader
from langchain.text_splitter import CharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS
from langchain_groq import ChatGroq
from langchain.memory import ConversationSummaryBufferMemory
from langchain.chains import ConversationalRetrievalChain
from huggingface_hub import login
import tempfile
import os

# ⛓️ Load keys directly
HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

login(HUGGINGFACE_TOKEN)

# Extract text from first 3 pages only
def extract_text_from_pdf(file):
    pdf_reader = PdfReader(file)
    text = ""
    for i, page in enumerate(pdf_reader.pages[:3]):
        content = page.extract_text()
        if content:
            text += content
    return text.strip().replace("\n", " ")

#Chunking
#Split the text into smaller chunks for embedding


def split_text_chunks(text):
    splitter = CharacterTextSplitter(
        separator="\n", chunk_size=300, chunk_overlap=30, length_function=len
    )
    chunks = splitter.split_text(text)
    return chunks[:5]  # limit to 5 chunks

# Build FAISS vectorstore
def create_vectorstore(chunks):
    embeddings = HuggingFaceEmbeddings(
        model_name="hkunlp/instructor-xl", model_kwargs={"device": "cuda"}
    )
    return FAISS.from_texts(chunks, embedding=embeddings)

# Create LangChain conversation chain
def create_chain(vectorstore):
    llm = ChatGroq(
        model_name="llama3-8b-8192",
        api_key=GROQ_API_KEY,
        temperature=0.5,
    )
    memory = ConversationSummaryBufferMemory(llm=llm, memory_key="chat_history", return_messages=True)
    return ConversationalRetrievalChain.from_llm(llm=llm, retriever=vectorstore.as_retriever(), memory=memory)

from fpdf import FPDF

def save_quiz_to_pdf(quiz_text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    # Add text to PDF
    for line in quiz_text.split('\n'):
        pdf.multi_cell(0, 10, line)

    # Save PDF to temp file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    pdf.output(temp_file.name)

    return temp_file.name

# Main quiz generation function
def generate_quiz(pdf_file, prompt):
    try:
        text = extract_text_from_pdf(pdf_file)
        chunks = split_text_chunks(text)
        vectorstore = create_vectorstore(chunks)
        chain = create_chain(vectorstore)

        # Final prompt to prevent answers
        final_prompt = (
            "Generate a quiz based on the following instructions. "
            "Do NOT include any answers. Just output clear questions.\n\n" + prompt
        )
    #     response = chain.run(final_prompt)
    #     return response
    # except Exception as e:
    #     return f" Error: {str(e)}"
        quiz_text = chain.run(final_prompt)
        pdf_path = save_quiz_to_pdf(quiz_text)

        return quiz_text, pdf_path
    except Exception as e:
        return f"Error: {str(e)}", None

# Gradio UI
with gr.Blocks() as demo:
    gr.Markdown("## 📘 Education Notes Quiz Generator (Gradio Version)")
    gr.Markdown("Upload your notes (PDF) and give a quiz prompt. Output will contain **questions only** — no answers.")

    with gr.Row():
        pdf_input = gr.File(label="Upload PDF", file_types=[".pdf"])
        prompt_input = gr.Textbox(label="Enter your quiz prompt", placeholder="e.g., Generate 5 MCQs and 2 fill-in-the-blanks questions", lines=2)
    with gr.Row():
        generate_btn = gr.Button("Generate Quiz")
    with gr.Row():
        output_text = gr.Textbox(label="📤 Generated Quiz", lines=20)
        output_pdf = gr.File(label="📥 Download Quiz PDF")


    generate_btn.click(fn=generate_quiz, inputs=[pdf_input, prompt_input], outputs=[output_text, output_pdf])

demo.launch()