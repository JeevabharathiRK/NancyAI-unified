import re
import json
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from groq import Groq

class MovieExtractor:
    def __init__(self, groq_api_key, omdb_api_key, model="deepseek-r1-distill-llama-70b"):
        self.groq_client = Groq(api_key=groq_api_key, timeout=20.0)
        self.omdb_api_key = omdb_api_key
        self.model = model
        self.session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",)
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retry))
        self.session.headers.update({"User-Agent": "nancyai/2.0"})

    def _llm_extract(self, text):
        prompt = f"""
        Extract the movie title and release year from this text.
        Return in JSON format with keys 'movie' and 'year'. and give movie name space if it looks like two words.
        Text: "{text}"
        """

        response = self.groq_client.chat.completions.create(
            model="deepseek-r1-distill-llama-70b",  # or gemma2-9b-it
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )

        response_content = response.choices[0].message.content

        # Extract JSON string from the response content
        json_match = re.search(r'```json\s*(.*?)\s*```', response_content, re.DOTALL)
        if json_match:
            json_string = json_match.group(1)
            try:
                data = json.loads(json_string)
                movie = data.get("movie")
                year = data.get("year")
                print(f"Extracted movie: {movie}, year: {year}")
                return movie, year
            except json.JSONDecodeError:
                return None, None
        else:
            return None, None

    def get_movie_details(self, movie_name, year=None):
        """Get movie details from OMDb API"""
        if not movie_name:
            return None
        params = {"apikey": self.omdb_api_key, "t": movie_name}
        if year:
            params["y"] = year
        try:
            response = self.session.get("https://www.omdbapi.com/", params=params, timeout=8)
            response.raise_for_status()
            data = response.json()
            if data.get("Response") != "True":
                if year:
                    return self.get_movie_details(movie_name, None)
                return None
            return {
                "Title": data.get("Title"),
                "Year": data.get("Year"),
                "Rated": data.get("Rated"),
                "Released": data.get("Released"),
                "Runtime": data.get("Runtime"),
                "Genre": data.get("Genre"),
                "Director": data.get("Director"),
                "Actors": data.get("Actors"),
                "Plot": data.get("Plot"),
                "imdbRating": data.get("imdbRating"),
                "Poster": data.get("Poster"),
                "LookupStatus": "ok"
            }
        except Exception as e:
            logging.error("OMDb API error: %s", e)
            return None

    def process(self, filename, caption):
        """Main processing function."""
        movie_name, year = self._llm_extract(filename + " " + caption)
        if not movie_name:
            logging.warning("Could not extract movie name from filename: %s", filename)
            return None
        return self.get_movie_details(movie_name, year)