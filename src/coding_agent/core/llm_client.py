import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

MODEL = os.getenv("MODEL", "gpt-5-nano")

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
)
