from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.vectorstores.azuresearch import AzureSearch
from langchain_openai import AzureOpenAIEmbeddings, OpenAIEmbeddings
from dotenv import load_dotenv
import os
from langchain_core.tools import tool
import requests as req
from faker import Faker
from random import randint, choice, sample, uniform
from datetime import datetime, timedelta


load_dotenv()

embeddings: OpenAIEmbeddings = OpenAIEmbeddings(
    openai_api_key=os.getenv('OPENAI_API_KEY'), openai_api_version="2023-05-15", model="text-embedding-3-small"
)


index_name: str = "elkjop-big-products-index"
vector_store: AzureSearch = AzureSearch(
    azure_search_endpoint="https://srch-sc-dev-westeu.search.windows.net",
    azure_search_key=os.getenv('AZURE_SEARCH_KEY'),
    index_name=index_name,
    embedding_function=embeddings.embed_query,
)

@tool
def search(query: str, items: int = 10, filter: str = None):
    
    """Makes a call to the product database and returns the most relevant products

    Args:
        query: search word from the user
        items: number of items to return
        filter: filter to apply to the search
    """
    url = "https://srch-sc-dev-westeu.search.windows.net/indexes/elkjop-demo/docs/search?api-version=2023-11-01"
    headers = {
        "Content-Type": "application/json",
        "api-key": os.getenv('AZURE_SEARCH_KEY')
    }
    data = {
        "vectorQueries": [{
            "vector": embeddings.embed_query(query),g
            "fields": "contentVector",
            "kind": "vector",
            "exhaustive": True,
            "k": 5
        }],
        "search": query,
        "select": "id, title, category, subcategory, price, description_short, image_URL, title_URL",
        
    }

    response = req.post(url, headers=headers, json=data)
    response = response.json()
    return response['value']

@tool
def findUser():
    """Generates a fake user profile with purchase history and interests that will be used for personalization in the chatbot, when the user asks for help or product search. 

    """
    fake = Faker()
    
    # Predefined lists for more realistic data
    interests = [
        "Photography", "Gaming", "Home Automation", "Cooking", "Smart Devices",
        "Home Theater", "Music Production", "Remote Work", "Smart Home",
        "Virtual Reality", "Streaming", "DIY Electronics", "Home Office",
        "Smart Kitchen", "Home Entertainment"
    ]
    
    occupations = [
        "Software Engineer", "Teacher", "Marketing Manager", "Doctor",
        "Graphic Designer", "Business Analyst", "Chef", "Architect",
        "Sales Representative", "Financial Advisor", "Project Manager",
        "Content Creator", "Small Business Owner", "Consultant"
    ]
    
    electronics_products = [
        {"name": "4K Smart TV", "price": 899.99},
        {"name": "Robot Vacuum", "price": 299.99},
        {"name": "Smart Speaker", "price": 99.99},
        {"name": "Coffee Maker", "price": 159.99},
        {"name": "Gaming Console", "price": 499.99},
        {"name": "Microwave Oven", "price": 199.99},
        {"name": "Air Purifier", "price": 249.99},
        {"name": "Security Camera", "price": 179.99},
        {"name": "Smart Thermostat", "price": 149.99},
        {"name": "Dishwasher", "price": 699.99}
    ]
    
    # Generate purchase history
    num_purchases = randint(1, 5)
    purchase_history = []
    last_purchase_date = datetime.now()
    
    for _ in range(num_purchases):
        product = choice(electronics_products).copy()
        # Add some price variation (±10%)
        price_variation = uniform(-0.1, 0.1)
        product['actual_price'] = round(product['price'] * (1 + price_variation), 2)
        # Generate a random date within the last year
        purchase_date = last_purchase_date - timedelta(days=randint(1, 365))
        last_purchase_date = purchase_date
        product['purchase_date'] = purchase_date.strftime('%Y-%m-%d')
        purchase_history.append(product)
    
    # Generate user data
    user = {
        'id': fake.uuid4(),
        'name': fake.name(),
        'email': fake.email(),
        'phone': fake.phone_number(),
        'address': fake.address(),
        'occupation': choice(occupations),
        'age': randint(23, 75),
        'interests': sample(interests, randint(2, 5)),
        'join_date': (datetime.now() - timedelta(days=randint(1, 1095))).strftime('%Y-%m-%d'),
        'purchase_history': purchase_history
    }
    
    return user


tools = [search, findUser]