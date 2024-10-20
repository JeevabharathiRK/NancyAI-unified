import os
import logging
import requests
from langchain.chains import LLMChain
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)
from langchain_core.messages import SystemMessage
from langchain.chains.conversation.memory import ConversationBufferWindowMemory
from langchain_groq import ChatGroq
from groq import Groq  

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

class Nancy:
    def __init__(self):
        self.name = "Nancy"
        groq_api_key = os.environ['GROQ_API_KEY']
        self.models = {
            'llama3-8b-8192': 'llama3-8b-8192',
            'gemma2-9b-it': 'gemma2-9b-it'
        }
        self.simplified_model_names = {
            'google-gemma': 'gemma2-9b-it',
            'meta-llama': 'llama3-8b-8192'
        }
        self.default_model = 'llama3-8b-8192'
        self.groq_api_key = groq_api_key
        self.chat_data = {}

    def get_memory_for_chat(self, chat_id):
        if chat_id not in self.chat_data:
            self.chat_data[chat_id] = {
                'memory': ConversationBufferWindowMemory(k=20, memory_key="chat_history", return_messages=True),
                'model': self.default_model
            }
        return self.chat_data[chat_id]['memory']

    def get_model_for_chat(self, chat_id):
        if chat_id not in self.chat_data:
            self.get_memory_for_chat(chat_id)
        return self.chat_data[chat_id]['model']

    def prompt(self, msg, chat_id):
        try:
            memory = self.get_memory_for_chat(chat_id)
            model = self.get_model_for_chat(chat_id)
            groq_chat = ChatGroq(groq_api_key=self.groq_api_key, model_name=model)

            prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content="Your name is Nancy, you are a friendly lovely chatbot AI and speak less."),
                MessagesPlaceholder(variable_name="chat_history"),
                HumanMessagePromptTemplate.from_template("{human_input}")
            ])

            conversation = LLMChain(llm=groq_chat, prompt=prompt, verbose=False, memory=memory)
            response = conversation.predict(human_input=msg)
            return response

        except Exception as e:
            logging.error(f"Error processing message: {str(e)}")
            return f"Error processing message: {str(e)}"
