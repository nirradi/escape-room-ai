from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Initialize the ChatOllama model, specify the model you pulled
llm = ChatOllama(model="llama3.1")

# Define a prompt template
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant."),
    ("user", "{input}")
])

# Create a chain using LangChain Expression Language (LCEL)
chain = prompt | llm | StrOutputParser()

# Invoke the chain
response = chain.invoke({"input": "Explain the concept of AI agents in simple terms."})
print(response)