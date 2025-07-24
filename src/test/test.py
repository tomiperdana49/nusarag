import os
import google.generativeai as genai
from dotenv import load_dotenv
import asyncio
from flask import jsonify
#from connection.connection import get_connection

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain import hub  
from langchain.chat_models import init_chat_model
from langchain_openai import OpenAIEmbeddings

load_dotenv()

gemini_api_key = os.getenv("GEMINI_API_KEY")

os.environ["GOOGLE_API_KEY"] = gemini_api_key

openai_api_key = os.getenv("OPENAI_API_KEY")

embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
embed = OpenAIEmbeddings(model="text-embedding-3-small")
def convert(text):
    return embeddings.embed_query(text)


print(len(embed.embed_query("Saya")))