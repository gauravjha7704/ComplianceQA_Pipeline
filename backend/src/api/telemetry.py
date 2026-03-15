#azure opentelemetry integration

import os 
import logging
from azure.monitor.opentelemetry import configure_azure_monitor

# create a dedicated logger
logger = logging.getLogger("brand-guardian-telemetry")

def seup_telemetry(): # industry standard observability framework (both telemetry and langsmith do the same task)
    '''
    Initializes Azure Monitor OpenTelemetry 
    Tracks: HTTP requests, database queries ,errors, performance metrics
    send this data to azuure monitor (you can consider this as a flight data recorder)

    it auto captures every API request
    No need to manually log each endpoint

    '''
# retrieve connection string
    connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRINGS")
# check if configured
    if not connection_string:
        logger.warning("No instrumentation key found.Telemtry is DISABLED.")
        return
# configure the azure monitor
    try:
        configure_azure_monitor(
            connection_string = connection_string,
            logger_name = "brand-guardian-tracer"
        )
        logger.info("Azure Monitor Tracking Enabled and Connected")
    except Exception as e:
            logger.error(f"Failed to Initialize Azure Monitor: {e}")

'''
why do we use telemetry ?
 
 Without:
 API is slow -> No idea which part
 How many users access today? No Visibility
 
 With: 
 /audit endpoint avergaes 4.5 s (Indexer takes 3.8 s)
 Error logs show : 12% of audits failed due to Youtube download errors
 Metrics show : 450 API Calls today, 89% success rate
 '''


