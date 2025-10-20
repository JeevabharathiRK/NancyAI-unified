import os
from collections import deque
from groq import Groq

MAX_TURNS = 15  # user<->bot pairs (15 user+15 bot messages stored)
CHAT_AI_MODEL = os.getenv("CHAT_AI_MODEL", "llama-3.1-8b-instant")


class AIResponseGenerator:
    def __init__(self):
        self.api_key: str | None = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise RuntimeError("GROQ_API_KEY not set in environment.")
        self.groq_client = Groq(api_key=self.api_key)
        # histories[user_id] = deque[(user_text, bot_reply)]
        self.histories: dict[int, deque[tuple[str, str]]] = {}

    def _history(self, user_id: int) -> deque[tuple[str, str]]:
        return self.histories.setdefault(user_id, deque(maxlen=MAX_TURNS))

    def clear_history(self, user_id: int) -> None:
        self.histories.pop(user_id, None)

    def history_length(self, user_id: int) -> int:
        return len(self._history(user_id))

    async def generate_reply(self, user_id: int, user_name: str, text: str) -> str:
        hist = self._history(user_id)
        messages: list[dict[str, str]] = [
            {
                "role": "system",
                "content": (
                    "You are Nancy, a helpful AI assistant. "
                    f"User name: {user_name}. Keep replies concise. "
                    "Character style: I'm Nancy🦋 💕 Spreading kindness and positivity."
                    "Also If the received message is like a movie name ask them to send the movie file here there by you can plot and rating. (It is handled seperatly)"
                ),
            }
        ]
        for u, a in hist:
            messages.append({"role": "user", "content": u})
            messages.append({"role": "assistant", "content": a})
        messages.append({"role": "user", "content": text})

        completion = self.groq_client.chat.completions.create(
            model= CHAT_AI_MODEL,
            messages=messages,
            max_tokens=256,
            temperature=0.7,
        )
        reply: str = completion.choices[0].message.content.strip()
        hist.append((text, reply))
        return reply


def get_ai_generator() -> AIResponseGenerator:
    return AIResponseGenerator()