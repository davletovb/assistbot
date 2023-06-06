import os
import logging
import openai
import time

from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain, ConversationChain
from langchain.prompts import PromptTemplate
from langchain.agents import load_tools, initialize_agent, Tool, AgentType
from langchain.memory import ConversationBufferMemory
from langchain.tools import DuckDuckGoSearchRun
from langchain.utilities import GoogleSearchAPIWrapper
from langchain.utilities.wolfram_alpha import WolframAlphaAPIWrapper
from langchain.callbacks.streaming_stdout_final_only import FinalStreamingStdOutCallbackHandler

from vectordb import VectorDB

# Enable logging for debugging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Set OpenAI API key
# openai_api_key = None
openai.api_key = os.environ.get("OPENAI_API_KEY")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.environ.get("GOOGLE_CSE_ID")
WOLFRAM_ALPHA_APPID=os.environ.get("WOLFRAM_ALPHA_APPID")

class RateLimitError(Exception):
    def __init__(self, message, retry_after=None):
        super().__init__(message)
        self.retry_after = retry_after

def handle_rate_limiting(func, *args, **kwargs):
    retries = 5
    backoff_factor = 2

    for attempt in range(retries):
        try:
            return func(*args, **kwargs)
        except openai.error.RateLimitError as e:
            if attempt < retries - 1:  # Check if it's the last attempt
                retry_after = int(e.headers.get("Retry-After", 0))
                wait_time = retry_after or (backoff_factor ** attempt)
                logger.warning(f"Rate limit exceeded. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                raise RateLimitError("Too many rate-limited attempts.", retry_after=retry_after) from e
        except Exception as e:
            raise e

class Prompter:
    def __init__(self, chat_id):
        # check if the chat_id is string
        if not isinstance(chat_id, str):
            self.chat_user_id = str(chat_id)
        else:
            self.chat_user_id = chat_id

    def generate_image(self, prompt):
        try:
            response = handle_rate_limiting(openai.Image.create, prompt=prompt, n=1, size="256x256")
            return response['data'][0]['url']
        except Exception as e:
            logger.error(f"Error generating image: {e}")
            return None

    def transcribe_voice(self, file):
        try:
            transcript = handle_rate_limiting(openai.Audio.transcribe, model="whisper-1", file=file)
            return transcript["text"]
        except Exception as e:
            logger.error(f"Error transcribing voice: {e}")
            return None

    def save_document(self, document):
        try:
            db = VectorDB(chat_user_id=self.chat_user_id, openai_api_key=openai.api_key)
            summary = db.add_document(document=document)
            return summary
        except Exception as e:
            logger.error(f"Error saving document: {e}")
            return "Error saving document"

    def save_url(self, url):
        try:
            db = VectorDB(chat_user_id=self.chat_user_id, openai_api_key=openai.api_key)
            summary = db.add_url(url=url)
            return summary
        except Exception as e:
            logger.error(f"Error saving URL: {e}")
            return "Error saving URL"
        
    def search_database(self, query):
        try:
            db = VectorDB(chat_user_id=self.chat_user_id, openai_api_key=openai.api_key)
            results = db.query(query=query)
            return results
        except Exception as e:
            logger.error(f"Error searching user documents: {e}")
            return "Error searching user documents"
    
    def clear_database(self):
        try:
            db = VectorDB(chat_user_id=self.chat_user_id, openai_api_key=openai.api_key)
            db.clear_database()
            return True
        except Exception as e:
            logger.error(f"Error clearing user documents: {e}")
            return False


    # Prompt the LLM to generate a response
    def generate_response(self, message, chat_context):

        # Format the chat history as a string
        formatted_chat_history = "\n".join([f"{k}: {v}" for entry in chat_context for k, v in entry.items()])

        # Create a prompt template
        template = f"""
        Chat History:
        {formatted_chat_history}

        Human: {message}
        AI:"""

        # Create a prompt template
        #prompt_template = PromptTemplate(template=template, validate_template=False)

        # A conversation buffer (memory) & import llm of choice
        #memory = ConversationBufferMemory(memory_key="chat_history", input_key="input")

        # Create a model, chain and tool for the language model
        llm = ChatOpenAI(temperature=0, 
                        streaming=True, 
                        callbacks=[FinalStreamingStdOutCallbackHandler()], 
                        max_retries=3,
                        openai_api_key=openai.api_key)

        #llm_chain = ConversationChain(llm=llm, prompt=prompt_template)

        # Provide access to a list of tools that the agents will use
        tools = load_tools(['wikipedia',
                            'open-meteo-api',
                            'llm-math'],
                            llm=llm)
        
        tools.extend([
            Tool(name="Image Model", func=self.generate_image, description="Generate images from text", return_direct=True),
            Tool(name="Google Search", func=GoogleSearchAPIWrapper(google_api_key=GOOGLE_API_KEY, google_cse_id=GOOGLE_CSE_ID, k=5).run, description="Search the web"),
            Tool(name="Wolfram Alpha", func=WolframAlphaAPIWrapper(wolfram_alpha_appid=WOLFRAM_ALPHA_APPID).run, description="Search Wolfram Alpha"),
            Tool(name="Search User Documents", func=self.search_database, description="Search user documents database")
        ])
        

        # initialise the agents & make all the tools and llm available to it
        agent = initialize_agent(tools=tools,
                                llm=llm, 
                                agent=AgentType.CONVERSATIONAL_REACT_DESCRIPTION, 
                                verbose=True,
                                handle_parsing_errors="Check your output and make sure it conforms!")

        try:
            answer = agent.run(input=template, chat_history=formatted_chat_history, return_only_outputs=True)
            return answer
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "An error occurred while generating the response."