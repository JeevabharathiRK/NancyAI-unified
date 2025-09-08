
from groq import Groq
from os import getenv

client = Groq(
    api_key=getenv("GROQ_API_KEY"),
)

