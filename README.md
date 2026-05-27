# Text-to-SQL App — Olist E-Commerce

An LLM-powered application that converts natural language questions 
into PostgreSQL queries on the Olist Brazilian E-Commerce dataset.

## Tech Stack
- Python
- LangChain + Groq (Llama 3.3 70B)
- PostgreSQL
- Streamlit

## Features
- Natural language to SQL conversion
- Auto query retry on error
- Interactive results table
- Auto chart generation
- Query history

## Setup
1. Clone the repo
2. Install dependencies: `pip install -r requirements.txt`
3. Create `.env` file with your credentials
4. Load data: `python src/load_data.py`
5. Run app: `streamlit run src/app.py`
6. http://localhost:8501/

## Dataset
Olist Brazilian E-Commerce — 100K+ orders across 7 tables
