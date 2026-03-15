An AI-powered automated compliance auditing system that analyzes video content against regulatory standards using a Retrieval-Augmented Generation (RAG) architecture. The system ingests multimodal video data (transcripts and OCR), retrieves relevant compliance rules, and uses large language models to detect violations and generate structured compliance reports.

The pipeline is orchestrated using LangGraph, powered by Azure OpenAI (GPT-4o) for reasoning, and supported by Azure Video Indexer, Azure AI Search, and Azure OpenAI Embeddings. Observability and tracing are enabled through LangSmith and Azure Application Insights.

The system transforms unstructured video content into structured JSON compliance reports, enabling automated regulatory auditing with full-stack monitoring.
