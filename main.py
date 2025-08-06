import openai
import os
from dotenv import find_dotenv, load_dotenv
import time
import logging
import requests
import json
from datetime import datetime

load_dotenv()

news_api_key = os.environ.get("NEWS_API_KEY")

client = openai.OpenAI()
model = "gpt-3.5-turbo-16k"


def get_news(topic):
    url = (
        f"https://newsapi.org/v2/everything?q={topic}&apiKey={news_api_key}&pageSize=5"
    )

    try:
        response = requests.get(url)
        if response.status_code == 200:
            news = json.dumps(response.json(), indent= 4)
            news_json = json.loads(news)

            data = news_json

            status = data["status"]
            total_results = data["totalResults"]
            articles = data["articles"]

            final_news = []

            for article in articles:
                source_name = article["source"]
                author = article["author"]
                title = article["title"]
                description = article["description"]
                article_url = article["url"]
                content = article["content"]

                news_piece = f"""
                    Title: {title},
                    Author: {author},
                    Source: {source_name},
                    Description: {description},
                    URL: {url}
                """
                final_news.append(news_piece)
        
            return final_news

        else:
            print("return empty list")
            return []
    
    
    except requests.exceptions.RequestException as e:
        print("Error occured during API request", e)


def main():
    result = get_news("gymnastics")
    print(result)

if __name__ == "__main__":
    main()