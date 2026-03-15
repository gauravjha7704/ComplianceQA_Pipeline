import json 
import os 
import logging
import re  ## for regular expression
from typing import Dict, Any , List

from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_community.vectorstores import AzureSearch
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage


#impot state schema
from backend.src.graph.state import VideoAuditState,ComplianceIssue

# import service 
from backend.src.services.video_indexer import VideoIndexerService

# configure the logger 
logger = logging.getLogger("brand-guardian")
logging.basicConfig(level=logging.INFO)

# NODE 1: Indexer 
### function resposible for convertion video to text

def index_video_node(state:VideoAuditState) -> Dict[str,Any]:
    '''
    Downloads the youtube video from the url
    Uploads to the Azure video Indexer 
    extract the insights
    '''
    video_url = state.get("video_url")
    video_id_input = state.get("video_id","vid_demo")

    logger.info(f"---[Node:Indexer] Processing : {video_url}")

    local_filename = "temp_audio_video.mp4"

    try:
        vi_service = VideoIndexerService()
        #download : yt.dlp (download the video from youtube temporarily)
        if "youtube.com" in video_url or "youtu.be" in video_url:
            local_path = vi_service.download_youtube_video(video_url, output_path=local_filename)
        else:
            raise Exception("please provide a valid youtube url for this test.")
        #upload 
        azure_video_id = vi_service.upload_video(local_path, video_name = video_id_input)
        logger.info(f"Upload Success. Azure ID : {azure_video_id}")
        #cleanup
        if os.path.exists(local_path):
            os.remove(local_path)
        #wait
        raw_insights = vi_service.wait_for_processing(azure_video_id) ## this prevent the code from moving forward until video results are ready
        #extract 
        clean_data = vi_service.extract_data(raw_insights) # pulls  out the transcript & ocr
        logger.info("---[NODE: Indexer] Extraction Complete -------")
        return clean_data
    
    except Exception as e:
        logger.error(f"video Indexer failed : {e}")
        return {
            "error": [str(e)],
            "final_status" : "FAIL",
            "transcript" : "",
            "ocr_text" : []
        }
#Node 2: Compliance Auditor 
def audio_content_node(state:VideoAuditState) -> Dict[str,Any]: # help ai to judge the content
    '''
    perform Retrieval Augmented Generation to audit the content - brand video 
    
    '''
    logger.info("---[Node: Auditor] querying knowledge base & LLM")
    transcript= state.get("transcript","")
    if not transcript:
        logger.warning("no transcript available . skipping audit....")
        return{
            "final_status": "FAIL",
            "final_report": "Audit Skipping because video processing failed (No transcipt.)"

        }
    
    #initialize client
    llm = AzureChatOpenAI(
        azure_deployment = os.get("AZURE_OPENAI_CHAT_DEPLOYMENT"),
        openai_api_version = os.getenv("AZURE_OPEN_API_VERSION"),  #Already defined in getenv
        temperature = 0.0
    )
    embeddings= AzureOpenAIEmbeddings(
        azure_deployment= "text-embedding-3-small",
        open_api_version = os.getenv("AZURE_OPENAI_API_VERSION")
    )

    vector_store = AzureSearch(
        azure_search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT"),
        azure_search_key = os.getenv("AZURE_SEARCH_API_KEY"),
        index_name = os.getenv("AZURE_SEARCH_INDEX_NAME"),
        embedding_function=embeddings.embed_query

    )
    #RAG Retrieval 
    ocr_text = state.get("ocr.text",[])
    query_text = f"{transcript} {''.join(ocr_text)}" ## query merging transcript and ocr
    docs = vector_store.similarity_search(query_text,k=3) ## ask azure search find me the the three most relvent pages (chunks) from pdf rulebook matching the text
    retrieved_rules = "\n\n".join([doc.page_content for doc in docs]) ## save those three pages in retrieved rules # we send these three paragraphs only otherwise whole is costly

    # giving insturction to ai, context: rule & taks : finding the voilation
    system_prompt = f""" 
            you are a senior brand complicance auditor
            OFFICIAL REGULATORY RULES:
            {retrieved_rules}
            INSTRUCTIONS:
            1.Analyse the transcript and OCT text below.
            2.Identify ANY violation of the rules
            3. Return strictly JSON in the following format:
            {{
            "compliance_results":[
                {{
                     "category": "claim Validation..."
                     "severity": "CRITICAL",
                     "description": "Explanation of the violation. 
                }}
            ],
            "status": "FAIL",
            "final_report":"summary of findings..."
            }}

            if no violations are found, set "status" to "PASS" and "compliance_result" to []. 
            """
        
    user_message = f"""
                VIDEO_METADATA : {state.get('video_metadata',{})}
                TRANSCRIPT : {transcript}
                ON-SCREEN TEXT (OCR) : {ocr_text}
                """
    try:
        response = llm.invoke([
            SystemMessage(content= system_prompt),
            HumanMessage(content = user_message)
        ])
        content = response.content
        if "```" in content:     ###safety mechanism , to prevent the code form backtick (ai try to be help ful and write code in markdown backtick)
            content = re.search(r"```(?:json)?(.?)```", content, re.DOTALL).group(1)  ## use regualar exp to look for backtick
        audit_data = json.loads(content.strip())
        return{                                               ## return pure json, backtick removed
            "compliance_results" : audit_data.get("compliance_results",[]),
            "final_status" : audit_data.get("status", "FAIL"),
            "final_report" : audit_data.get("final_report", "No report generated")
        }
    except Exception as e:
        logger.error(f"system Error in Auditor Node: {str(e)}") 
        #logging  the raw response
        logger.error(f"Raw LLM response : {response.content if 'response' in locals() else 'None'}")
        return {
            "errors" : [str(e)],
            "final_status" : "FAIL"
        }     
    