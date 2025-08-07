import openai
import os
from dotenv import find_dotenv, load_dotenv
import time
import logging
import requests
import json
from datetime import datetime

# Get the openai key and the news api key
load_dotenv()
news_api_key = os.environ.get("NEWS_API_KEY")

client = openai.OpenAI()
model = "gpt-3.5-turbo-16k"

# Use newsapi.org to get news
def get_news(topic):
    url = (
        f"https://newsapi.org/v2/everything?q={topic}&apiKey={news_api_key}&pageSize=5"
    )

    try:
        response = requests.get(url) 

        # if request is successful, convert the reponse into json
        if response.status_code == 200:
            #news = json.dumps(response.json(), indent= 4)
            #news_json = json.loads(news)
            news_json = response.json()

            data = news_json

            status = data["status"]
            total_results = data["totalResults"]
            articles = data["articles"]

            final_news = []

            # concatenate every article into a string and append into one list
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

class AssistantManager:
    thread_id = None
    assistant_id = None

    def __init__(self, model: str = model):
        self.client = client
        self.model  = model
        self.assistant = None
        self.thread = None
        self.run = None
        self.summary = None

        # If AssistantManager already has an assistant_id or thread_id, retrieve the assistant or thread
        if AssistantManager.assistant_id:
            self.assistant = self.client.beta.assistants.retrieve(
                assistant_id= AssistantManager.assistant_id
            )
        if AssistantManager.thread_id:
            self.thread = self.client.beta.threads.retrieve(
                thread_id = AssistantManager.thread_id
            )
    
    def create_assistant(self, name, instructions, tools):

        # If we don't have an assistant yet, create one using our client
        if not self.assistant:
            assistant_obj = self.client.beta.assistants.create(
                name = name,
                instructions = instructions,
                tools = tools,
                model = self.model
            )
        
            # Now that we have an assistant, set self.assistant and self.assistant_id
            AssistantManager.assistant_id = assistant_obj.id
            self.assistant = assistant_obj
            print(f"Created assistant with ID: {self.assistant.id}")
    
    def create_thread(self):

        # If we don't have a thread yet, create one using our client
        if not self.thread:
            thread_obj = self.client.beta.threads.create()

            # Now that we have a new thread, set self.
            AssistantManager.thread_id = thread_obj.id
            self.thread = thread_obj
            print(f"Created thread with ID {self.thread.id}")
    
    def add_message_to_thread(self, role, content):
        if self.thread:
            self.client.beta.threads.messages.create(
                thread_id = self.thread.id,
                role = role,
                content = content
            )
    

    def run_assistant(self, instructions):
        if self.thread and self.assistant:
            self.run = self.client.beta.threads.runs.create(
                thread_id = self.thread.id,
                assistant_id = self.assistant.id,
                instructions = instructions
            )

if __name__ == "__main__":
    main()