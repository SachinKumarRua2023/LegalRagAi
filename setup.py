from setuptools import setup, find_packages

setup(
    name="complete-rag-ai",
    version="1.0.0",
    description="AI Agent RAG system for US Legal Cases with ChromaDB + Gemini",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "chromadb>=0.5.0",
        "langchain>=0.3.0",
        "sentence-transformers>=3.0.0",
        "google-generativeai>=0.8.0",
        "pdfplumber>=0.11.0",
        "python-docx>=1.1.0",
        "python-pptx>=1.0.0",
        "openpyxl>=3.1.0",
        "requests>=2.32.0",
        "rich>=13.0.0",
        "python-dotenv>=1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "rag-ingest=ingest:main",
            "rag-agent=main:main",
        ],
    },
)
