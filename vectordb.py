"""
Vector database for storing vectors and their metadata.
"""

import os
import logging
from langchain.document_loaders import UnstructuredFileLoader, WebBaseLoader
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.text_splitter import CharacterTextSplitter
from langchain.vectorstores import Chroma
from langchain import OpenAI
from langchain.chains import RetrievalQAWithSourcesChain
from langchain.prompts import PromptTemplate
from langchain.chains.summarize import load_summarize_chain
from chromadb.config import Settings

# Set OpenAI API key
openai_api_key = os.environ["OPENAI_API_KEY"]

# Set Chroma settings
CHROMA_SETTINGS = Settings(
    chroma_db_impl="duckdb+parquet",
    persist_directory="db",
    anonymized_telemetry=False)

# Set logging level
# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

class VectorDB():
    def __init__(self, chat_user_id):

        self.text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
        self.embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
        self.vector_store = Chroma(embedding_function=self.embeddings, client_settings=CHROMA_SETTINGS, persist_directory="db", collection_name=chat_user_id)
        self.llm = OpenAI(openai_api_key=openai_api_key, temperature=0)

    def add(self, document):
        """Ingest a document into the vector store."""

        # Load the document
        loader = UnstructuredFileLoader(document)

        doc = loader.load()
        
        logger.info(f"Document loaded")

        # Split the document into sentences
        texts = self.text_splitter.split_documents(doc)

        logger.info(f"Split document into chunks")
        
        # Store the embeddings
        self.vector_store.add_documents(documents=texts)

        logger.info(f"Stored embeddings")
        
        # Persist the vector store to disk
        self.vector_store.persist()

        # return the summary of the document
        logger.info(f"Gathering summary")
        summary = self.summarize(texts)

        return summary
        
        # Clear the vector store from the memory
        #self.vector_store = None
    
    
    def add_urls(self, urls):

        loader = WebBaseLoader(urls)

        docs = loader.load()

        logger.info(f"Web page loaded")

        # Split the document into sentences
        texts = self.text_splitter.split_documents(docs)

        logger.info(f"Split document into chunks")

        # Store the embeddings
        self.vector_store.add_documents(documents=texts)

        logger.info(f"Stored embeddings")
        
        # Persist the vector store to disk
        self.vector_store.persist()

        # Gather the summary
        summary = self.summarize(texts)
        logger.info(f"Summary gathered")

        return summary
    

    def query(self, query):
        """Query the vector store for similar vectors."""
        
        # Query the vector store
        chain = RetrievalQAWithSourcesChain.from_chain_type(
            llm=self.llm, chain_type="stuff", retriever=self.vector_store.as_retriever())
        
        logger.info(f"Querying vector store")

        # Get the results
        results = chain({"question": query}, return_only_outputs=True)

        return results

    
    def summarize(self, docs):
        """Get the summary of a document."""
        
        # Prompt template only for the stuff chain type
        prompt_tempate = """Write a concise summary of the following text, use simple language and bullet points:
                        {text}

                        SUMMARY:"""
        
        prompt = PromptTemplate(template=prompt_tempate, 
                                input_variables=["text"])

        # Create the chain
        chain = load_summarize_chain(self.llm,
                                     chain_type="map_reduce",
                                     map_prompt=prompt,
                                     combine_prompt=prompt)

        summary = chain.run(input_documents=docs, return_only_outputs=True)

        logger.info(f"Summary gathered")

        return summary
