# Standard library imports
import os
import time

# Third-party imports
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

#Environment Variables
GROQ_API_KEY = os.environ['GROQ_API_KEY']
BOT_ROLE = "Your name is Nancy!, you are an AI ChatBot, You speak well and less"


class Nancy:
    def __init__(self):
        self.name = "Nancy"
        

        # Consolidated model configuration
        self.models = {
            'google-gemma': 'gemma2-9b-it',
            'meta-llama': 'llama3-8b-8192'
        }
        self.default_model = 'llama3-8b-8192'  # Default model
        self.groq_api_key = GROQ_API_KEY

        # Dictionary to hold memory and models for each chat ID
        self.chat_data = {}

    def get_memory_for_chat(self, chat_id):
        """Retrieve or create a memory object for the specific chat_id."""
        if chat_id not in self.chat_data:
            # Initialize memory and default model for new chat
            self.chat_data[chat_id] = {
                'memory': ConversationBufferWindowMemory(k=20, memory_key="chat_history", return_messages=True),
                'model': self.default_model  # Start with default model
            }
        return self.chat_data[chat_id]['memory']

    def get_model_for_chat(self, chat_id):
        """Retrieve or create a model object for the specific chat_id."""
        if chat_id not in self.chat_data:
            self.get_memory_for_chat(chat_id)  # Ensure chat data is initialized
        return self.chat_data[chat_id]['model']

    def change_model_for_chat(self, chat_id, new_model):
        """Change the model for the specific chat_id."""
        old_model = self.chat_data[chat_id]['model']
        self.chat_data[chat_id]['model'] = new_model
        return old_model, new_model

    def prompt(self, msg, chat_id):
        try:
            memory = self.get_memory_for_chat(chat_id)
            model = self.get_model_for_chat(chat_id)
            groq_chat = ChatGroq(groq_api_key=self.groq_api_key, model_name=model)

            prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content=BOT_ROLE),
                MessagesPlaceholder(variable_name="chat_history"),
                HumanMessagePromptTemplate.from_template("{human_input}")
            ])

            conversation = LLMChain(
                llm=groq_chat,
                prompt=prompt,
                verbose=False,
                memory=memory,  # Use chat-specific memory
            )

            response = conversation.predict(human_input=msg)
            return response

        except Exception as e:
            logging.error(f"Error processing message: {str(e)}")
            return f"Error processing message: {str(e)}"

    def analyze_image(self, image_url, caption, chat_id):
        """Analyze the image using the Groq client and save response to memory."""
        client = Groq()
        completion = client.chat.completions.create(
            model="llama-3.2-11b-vision-preview",
            messages=[{
                "role": "user",
                "content": [{
                    "type": "text",
                    "text": caption
                }, {
                    "type": "image_url",
                    "image_url": {
                        "url": image_url
                    }
                }]
            }, {
                "role": "assistant",
                "content": ""
            }],
            temperature=1,
            max_tokens=1024,
            top_p=1,
            stream=False,
            stop=None,
        )

        analysis_result = completion.choices[0].message.content  # Get the response content

        # Save the analysis result to the chat memory
        memory = self.get_memory_for_chat(chat_id)
        memory.save_context({"input": caption}, {"output": analysis_result})

        return analysis_result