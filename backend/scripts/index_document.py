import os
import glob
import logging
from dotenv import load_dotenv

load_dotenv(override=True)

# document loaders and splitters
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

# azure components
from langchain_openai import AzureOpenAIEmbeddings
from langchain_community.vectorstores import AzureSearch

# setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger("indexer")


def index_docs():
    """
    Reads PDFs, chunks them, and uploads them to Azure AI Search
    """

    # locate data folder
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_folder = os.path.join(current_dir, "../../backend/data")

    # environment check
    logger.info("=" * 60)
    logger.info("Environment Configure Check:")
    logger.info(f"AZURE_OPENAI_ENDPOINT: {os.getenv('AZURE_OPENAI_ENDPOINT')}")
    logger.info(f"AZURE_OPENAI_API_VERSION: {os.getenv('AZURE_OPENAI_API_VERSION')}")
    logger.info(f"AZURE_SEARCH_ENDPOINT: {os.getenv('AZURE_SEARCH_ENDPOINT')}")
    logger.info(f"AZURE_SEARCH_INDEX_NAME: {os.getenv('AZURE_SEARCH_INDEX_NAME')}")
    logger.info("=" * 60)

    # validate required env variables
    required_vars = [
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY",
        "AZURE_SEARCH_ENDPOINT",
        "AZURE_SEARCH_API_KEY",
        "AZURE_SEARCH_INDEX_NAME"
    ]

    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        logger.error("Check your .env file.")
        return

    index_name = os.getenv("AZURE_SEARCH_INDEX_NAME")

    # initialize embeddings
    try:
        logger.info("Initializing Azure OpenAI Embeddings...")

        embeddings = AzureOpenAIEmbeddings(
            azure_deployment=os.getenv(
                "AZURE_OPENAI_EMBEDDING_DEPLOYMENT",
                "text-embedding-3-small"
            ),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2023-05-15")
        )

        logger.info("Embedding model initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize embeddings: {e}")
        return

    # initialize Azure Search vector store
    try:
        logger.info("Initializing Azure AI Search vector store...")

        vector_store = AzureSearch(
            azure_search_endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
            azure_search_key=os.getenv("AZURE_SEARCH_API_KEY"),
            index_name=index_name,
            embedding_function=embeddings.embed_query
        )

        logger.info(f"Vector store initialized for index: {index_name}")

    except Exception as e:
        logger.error(f"Failed to initialize Azure Search: {e}")
        return

    # find PDFs
    pdf_files = glob.glob(os.path.join(data_folder, "*.pdf"))

    if not pdf_files:
        logger.warning(f"No PDFs found in {data_folder}. Add files.")
        return

    logger.info(
        f"Found {len(pdf_files)} PDFs: {[os.path.basename(f) for f in pdf_files]}"
    )

    all_splits = []

    # process each PDF
    for pdf_path in pdf_files:

        try:
            logger.info(f"Loading {os.path.basename(pdf_path)}")

            loader = PyPDFLoader(pdf_path)
            raw_docs = loader.load()

            # chunking
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200
            )

            splits = splitter.split_documents(raw_docs)

            for split in splits:
                split.metadata["source"] = os.path.basename(pdf_path)

            all_splits.extend(splits)

            logger.info(f"Split into {len(splits)} chunks")

        except Exception as e:
            logger.error(f"Failed processing {pdf_path}: {e}")

    # upload to Azure Search
    if all_splits:

        logger.info(
            f"Uploading {len(all_splits)} chunks to Azure AI Search '{index_name}'"
        )

        try:
            vector_store.add_documents(all_splits)

            logger.info("=" * 60)
            logger.info("Indexing Complete! Knowledge Base ready.")
            logger.info(f"Total chunks indexed: {len(all_splits)}")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"Upload failed: {e}")

    else:
        logger.warning("No documents were processed.")


if __name__ == "__main__":
    index_docs()