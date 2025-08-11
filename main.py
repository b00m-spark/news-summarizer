import openai
import os
from dotenv import find_dotenv, load_dotenv
import time
import logging
import requests
import json
from datetime import datetime
import streamlit as st

# Get the openai key and the news api key
load_dotenv()
news_api_key = os.environ.get("NEWS_API_KEY")

client = openai.OpenAI()
model = "gpt-4"

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

    def process_message(self):
        if self.thread:
            # Get list of all messages inside thread
            messages = self.client.beta.threads.messages.list(
                thread_id = self.thread.id
            )
            summary = []
            
            # Get the latest message
            last_message = messages.data[0]
            role = last_message.role
            response = last_message.content[0].text.value

            # Append its response to the summary list
            summary.append(response)
            self.summary = "\n".join(summary)

            print(f"SUMMARY as {role.capitalize()}: ====> {response}")

    def call_required_functions(self, required_actions):
        if not self.run:
            return
        tool_outputs = []

        # In required_actions->tool_calls, there's a list (in this case only one) of 
        # tools (functions) that the assistant requires us to call
        for action in required_actions["tool_calls"]:

            # Get function name and arguments for each
            func_name = action["function"]["name"]
            arguments = json.loads(action["function"]["arguments"])

            # If function name is get_news, we call get_news with the topic the assistant passed in
            if func_name == "get_news":
                output = get_news(topic= arguments["topic"])
                print(f"get_news returns: {output}")
                final_str = ""
                for item in output:
                    final_str += "".join(item)
                
                # The final result is the get_news output with the id of this required action 
                tool_outputs.append({"tool_call_id": action["id"],
                                     "output": final_str})
            else:
                raise ValueError(f"Unknown function: {func_name}")
                
        print("Submitting outputs back to the assistant ...")
        self.client.beta.threads.runs.submit_tool_outputs(
            thread_id= self.thread.id,
            run_id= self.run.id,
            tool_outputs= tool_outputs
        )

    def get_summary(self):
        return self.summary

    def wait_for_completion(self):

        if self.thread and self.run:
            while True:
                time.sleep(5)
                run_status = self.client.beta.threads.runs.retrieve(
                    thread_id= self.thread.id,
                    run_id= self.run.id
                )
                print(f"RUN STATUS: {run_status.model_dump_json(indent=4)}")

                if run_status.status == "completed":
                    self.process_message()
                    if self.summary and self.client.beta.threads.messages.list(
                        thread_id=self.thread.id
                    ).data[0].role == "assistant":
                        break

                # If the status becomes requires_action, we proceed to call functions according to its requirements
                elif run_status.status == "requires_action":
                    print("FUNCTION CALLING NOW ...")
                    self.call_required_functions(required_actions= run_status.required_action.submit_tool_outputs.model_dump())

def main():
    # result = get_news("gymnastics")
    # print(result)
    manager = AssistantManager()

    # Streamlit interface
    st.title("News Summarizer")

    with st.form(key="user_input_form"):
        instructions = st.text_input("Enter topic")
        submit_button = st.form_submit_button(label= "Run Assistant")

        if submit_button:
            manager.create_assistant(
                name= "News Summarizer",
                instructions= "You're a personal article summarizer Assistant who knows how to take a list of article's titles and descriptions and write a short summary of all the news articles",
                tools=[
                    {
                        "type": "function",
                        "function": {
                            "name": "get_news",
                            "description": "Get the list of articles/news for the given topic",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "topic": {
                                        "type": "string",
                                        "description": "The topic for the news, eg. bitcoin"
                                    }
                                },
                                "required": ["topic"]
                            }
                        }
                    }
                ]
            )

            manager.create_thread()

            manager.add_message_to_thread(
                role= "user",
                content= f"summarize the news on this topic {instructions}"
            )

            manager.run_assistant(instructions="Summarize the news")
            manager.wait_for_completion()

            summary = manager.get_summary()
            print(f"Summary --------> {summary}")

            st.write(summary)
            # st.text("Run Steps: ")
            # st.code(manager.run_steps(), line_numbers= True)


if __name__ == "__main__":
    main()