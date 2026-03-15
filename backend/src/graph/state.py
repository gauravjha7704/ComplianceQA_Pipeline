import operator
from typing import Annotated, List , Dict, Optional, Any, TypedDict

## define the schema for a single compliance result
# error report stucture
class ComplianceIssue(TypedDict):
    category : str
    description :str # specific details of voilation
    severity : str ## CRITICAL | WARNING
    timestamp : Optional[str]

#DEFINE THE GLOBAL GRAPH STATE
#this define the state that gets passed around in the agentic workflow
class VideoAuditState(TypedDict):
    '''
    define the data schema for langgraph execution content
    Main container : hold all the information about the audit 
    right from the initial url to the final report
    '''
    #input parameters
    video_url : str
    video_id : str

    #ingestion and extraction data
    local_file_path : Optional[str]
    video_metadata: Dict[str,Any] #{"duration :15, "resolution : 1080p"}
    transcript : Optional[str] # fully extracted speech to text
    ocr_text : List[str]

    #analysis output
    # stores the list of all the voilation found by AI
    compliance_results : Annotated[List[ComplianceIssue], operator.add]
    
    #final deliverables:
    final_status : str # PASS | FAIL
    final_report : str # markdown format

    #system observability
    #error : API timeout,  system level errors
    #list of system level crashes, 
    errors: Annotated[List[str], operator.add]

