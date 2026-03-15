'''
This module define the DAG: Directed Acyclic Graph that orchestrate the video compliance
audit process.
it connects the nodes using the StateGraph from LangGraph

START -> index_video_node -> audit_ content_ node -> END
'''

from langgraph.graph import StateGraph, END  # state graph is main tool fromthe langraph to build stateful workslow, # END special marker that tells graph work is done , and graph is to be finished 
from backend.src.graph.state import VideoAuditState 

from backend.src.graph.nodes import (
    index_video_node,  # two nodes we will be using
    audit_content_node
)

def create_graph(): ## graph constructor
    '''
    Constructs and Compiles the LangGraph workflow
    Returns:
    Compiled Graph: runnable graph object for execution
    '''
    #initialize the graph with state schema 
    workflow = StateGraph(VideoAuditState)  # every node  must accept and return the data that matches videoauditstructure, if it throw random data , graph throws error
    # add the nodes
    workflow.add_node("indexer", index_video_node) # (here graph donot care about complex python name) 
    workflow.add_node("auditor", audit_content_node)
    # define the entry point : indexer 
    workflow.set_entry_point("indexer") #beginning of graph 
    # define the edges 
    workflow.add_edge("indexer", "auditor") # direct path we are creating between indexer and auditor,send the data to auditor
    # once the audit is complete , the workflow ends
    workflow.add_edge("auditor", END)
    # compile the graph
    app = workflow.compile() # it prepare the graph to run, check everything like disconneted node,errors 
    return app

#expose this runnable app
app = create_graph() 