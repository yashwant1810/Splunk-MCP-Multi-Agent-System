from crewai import Agent, Task, Crew, Process, LLM
from dotenv import load_dotenv
import asyncio
from client import MCPClient 
import os
from crewai.tools import BaseTool 
from typing import Type
from pydantic import BaseModel, Field
import sys
load_dotenv()

gemini_llm= LLM(
    model="gemini/gemini-1.5-flash", 
    provider="google",              
    api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.7,
    verbose=True
)

class ValidateSPLInput(BaseModel):
    query: str = Field(..., description="The SPL query to validate")

# --- SearchOneshotInput and SearchOneshotTool ---
class SearchOneshotInput(BaseModel):
    query: str
    earliest_time: str = "-24h"
    latest_time: str = "now"

class SearchOneshotTool(BaseTool):
    name: str = "Search Oneshot"
    description: str = "Executes a SPL query using the oneshot search API and returns results."
    args_schema: Type[BaseModel] = SearchOneshotInput

    def _run(self, query: str, earliest_time: str = "-24h", latest_time: str = "now") -> str:
        print(f"DEBUG (tool input): QUERY={query} EARLIEST={earliest_time} LATEST={latest_time}")
        client = MCPClient()
        return asyncio.get_event_loop().run_until_complete(
            self._async_search(client, query, earliest_time, latest_time)
        )

    async def _async_search(self, client, query: str, earliest_time: str = "-24h", latest_time: str = "now") -> str:
        await client.connect()
        response = await client.search_oneshot(query, earliest_time, latest_time)
        await client.close()
        return str(response)

# --- GetIndexesTool ---
class GetIndexesInput(BaseModel):
    pass

class GetIndexesTool(BaseTool):
    name: str = "Get Indexes"
    description: str = "Retrieves a list of available Splunk indexes and their properties."
    args_schema: Type[BaseModel] = GetIndexesInput

    def _run(self) -> str:
        client = MCPClient()
        return asyncio.get_event_loop().run_until_complete(self._async_get_indexes(client))

    async def _async_get_indexes(self, client) -> str:
        await client.connect()
        response = await client.get_indexes()
        await client.close()
        return str(response)

# --- RunSavedSearchTool ---
class RunSavedSearchInput(BaseModel):
    search_name: str = Field(..., description="The name of the saved search to run")

class RunSavedSearchTool(BaseTool):
    name: str = "Run Saved Search"
    description: str = "Runs a saved search by name"
    args_schema: Type[BaseModel] = RunSavedSearchInput

    def _run(self, search_name: str) -> str:
        client = MCPClient()
        return asyncio.get_event_loop().run_until_complete(self._async_run_search(client, search_name))

    async def _async_run_search(self, client, search_name: str) -> str:
        await client.connect()
        response = await client.run_saved_search(search_name)
        await client.close()
        return str(response)

# --- SearchExportTool ---
class SearchExportInput(BaseModel):
    query: str
    earliest_time: str = "-24h"
    latest_time: str = "now"
    max_count: int = 100
    output_format: str = "json"

class SearchExportTool(BaseTool):
    name: str = "Search Export"
    description: str = "Streams results from a Splunk SPL query without creating a job."
    args_schema: Type[BaseModel] = SearchExportInput

    def _run(self, query: str, earliest_time: str = "-24h", latest_time: str = "now", max_count: int = 100, output_format: str = "json") -> str:
        client = MCPClient()
        return asyncio.get_event_loop().run_until_complete(
            self._async_export(client, query, earliest_time, latest_time, max_count, output_format)
        )

    async def _async_export(self, client, query: str, earliest_time: str, latest_time: str, max_count: int, output_format: str) -> str:
        await client.connect()
        response = await client.search_export(query, earliest_time, latest_time, max_count, output_format)
        await client.close()
        return str(response)

class GetSavedSearchesInput(BaseModel):
    pass

class GetSavedSearchesTool(BaseTool):
    name: str = "Get Saved Searches"
    description: str = "Retrieves a list of all saved searches available in Splunk."
    args_schema: Type[BaseModel] = GetSavedSearchesInput

    def _run(self) -> str:
        client = MCPClient()
        return asyncio.get_event_loop().run_until_complete(self._async_get_saved_searches(client))

    async def _async_get_saved_searches(self, client) -> str:
        await client.connect()
        response = await client.get_saved_searches()
        await client.close()
        return str(response)

class ValidateSPLTool(BaseTool):
    name: str = "Validate SPL Query"
    description: str = "Validates an SPL query for security risks and execution safety"
    args_schema: Type[BaseModel] = ValidateSPLInput

    def _run(self, query: str) -> str:
        client = MCPClient()
        return asyncio.get_event_loop().run_until_complete(self._async_validate(client, query))

    async def _async_validate(self, client, query: str) -> str:
        await client.connect()
        response = await client.validate_spl(query)
        await client.close()
        return str(response)


class GetConfigInput(BaseModel):
    pass

class GetConfigTool(BaseTool):
    name: str = "Get Config"
    description: str = "Fetches the configuration of the Splunk MCP environment."
    args_schema: Type[BaseModel] = GetConfigInput

    def _run(self) -> str:
        client = MCPClient()
        return asyncio.get_event_loop().run_until_complete(self._async_get_config(client))

    async def _async_get_config(self, client) -> str:
        await client.connect()
        response = await client.get_config()
        await client.close()
        return str(response)
    
validate_spl_tool = ValidateSPLTool()
search_oneshot_tool = SearchOneshotTool()
get_indexes_tool = GetIndexesTool()
run_saved_search_tool = RunSavedSearchTool()
search_export_tool = SearchExportTool()
get_saved_searches_tool = GetSavedSearchesTool()
get_config_tool = GetConfigTool()

splunk_agent = Agent(
    role="Splunk Security Analyst and SPL Expert",
    goal="Convert natural language requests to effective SPL queries and analyze Splunk data",
    backstory="""You are an expert Splunk engineer with deep knowledge of SPL syntax and data analysis. 
    You can convert natural language requests into proper SPL queries and execute them safely. 
    You understand common security use cases, log analysis patterns, and statistical operations in Splunk.
    
    Key SPL expertise:
    - Field extraction and filtering
    - Statistical operations (stats, top, rare, timechart)
    - Index selection based on data type
    - Time range optimization
    - Security analysis patterns
    - Performance considerations
    
    Common field mappings you know:
    - Source IPs: src_ip, src, clientip, remote_addr
    - Destination IPs: dest_ip, dest, dst, server_ip
    - User agents: http_user_agent, user_agent, useragent
    - Users: user, username, account, login
    - Authentication: action=failure, success=false, result=fail
    - Ports: dest_port, src_port, port
    - Protocols: protocol, proto, transport
    """,
    verbose=True,
    allow_delegation=False,
    llm=gemini_llm,
)

def create_spl_query_agent():
    return Agent(
        role="SPL Query Specialist",
        goal="Convert natural language to optimized SPL queries",
        backstory=
"""
Expert in SPL syntax, field mappings, and query optimization. 
Specializes in translating business requirements into efficient Splunk searches.

IMPORTANT : Return only raw SPL Query without any explaination, commentary or markdown formatting.

QUERY REQUIREMENTS :
- Always use the appropriate index and source type
- Apply relevant field extractions and filters
- Include proper time ranges( default to 24h if not specified)
- For metric queries, use appropriate statistical functions (stats, timechart, chart) for visualisation
- Always include aggregation where applicable (sum, count, avg, min, max)
- Optimize performance by using only necessary fields
- Format timestamps appropriately when working with time-based data
- Apply proper sorting (descending for counts, chronological for time series)
- Limit results appropriately (default to top 10/20 if not specified)
- Add meaningful field aliases for readablility in final output
""",
        verbose=True,
        llm=gemini_llm,
        tools=[search_oneshot_tool, get_indexes_tool]
    )

def create_search_execution_agent():
    return Agent(
        role="Search Execution Specialist", 
        goal="Execute Splunk searches and handle results efficiently",
        backstory=
"""
Expert in Splunk search execution, result formatting, and performance optimization.
Handles search jobs, exports, and result processing.
""",
        verbose=True,
        llm=gemini_llm,
        tools=[search_oneshot_tool, search_export_tool]
    )

def create_saved_search_agent():
    return Agent(
        role="Saved Search Manager",
        goal="Manage saved searches - creation, execution, and organization",
        backstory="""Specialist in Splunk saved search management, naming conventions, and search organization.
        Handles saving queries and managing search libraries.""",
        verbose=True,
        llm=gemini_llm,
        tools=[get_saved_searches_tool, run_saved_search_tool]
    )

def create_data_export_agent():
    return Agent(
        role="Data Export Specialist",
        goal="Handle data exports in various formats efficiently",
        backstory="""Expert in data formatting, export optimization, and file handling.
        Specializes in CSV, JSON, XML exports and data transformation.""",
        verbose=True,
        llm=gemini_llm,
        tools=[search_export_tool]
    )

def create_validation_agent():
    return Agent(
        role="Security Validation Specialist",
        goal="Validate SPL queries for security and safety",
        backstory="""Security expert focused on SPL query validation, risk assessment, and safe execution.
        Prevents malicious queries and ensures query safety.""",
        verbose=True,
        llm=gemini_llm,
        tools=[validate_spl_tool]
    )

def create_configuration_agent():
    return Agent(
        role="Splunk Configuration Specialist",
        goal="Manage Splunk environment configuration and settings",
        backstory="""Expert in Splunk administration, configuration management, and environment setup.
        Handles index management and system configuration.""",
        verbose=True,
        llm=gemini_llm,
        tools=[get_config_tool, get_indexes_tool]
    )

# Agent selection function
def get_specialized_agent(task_name: str):
    """Return the appropriate specialized agent for each task type"""
    agent_mapping = {
        'search_oneshot': create_spl_query_agent(),
        'search_export': create_data_export_agent(), 
        'run_saved_search': create_saved_search_agent(),
        'get_saved_searches': create_saved_search_agent(),
        'validate_spl': create_validation_agent(),
        'get_indexes': create_configuration_agent(),
        'get_config': create_configuration_agent()
    }
    
    return agent_mapping.get(task_name, create_spl_query_agent())  # Default fallback

def create_task_from_info_with_context(task_info, task_index, previous_outputs):
    """Enhanced version that properly handles context from previous tasks"""
    task_name = task_info['task']
    description = task_info['description']
    depends_on = task_info.get('depends_on')
    
    # Build context from previous tasks
    context = ""
    extracted_spl = ""
    extracted_search_name = ""
    
    if depends_on is not None and depends_on in previous_outputs:
        previous_output = previous_outputs[depends_on]
        context = f"Previous task output:\n{previous_output}\n\n"
        
        # Extract useful information from previous output
        extracted_spl = extract_spl_from_output(previous_output)
        extracted_search_name = extract_search_name_from_output(previous_output)
        
        print(f"🔍 Extracted from previous task: SPL='{extracted_spl[:50]}...', Name='{extracted_search_name}'")
    
    # Get environment variables
    user_request = os.getenv("USER_REQUEST", "")
    earliest = os.getenv("EARLIEST", "-24h")
    latest = os.getenv("LATEST", "now")
    max_count = int(os.getenv("MAX_COUNT", "100"))
    output_format = os.getenv("OUTPUT_FORMAT", "json")
    
    if task_name == "validate_spl":
        # Extract SPL from user request for validation
        spl_to_validate = extract_spl_from_request(user_request) or "index=* | head 10"
        
        return Task(
            description=f"""
{context}You must use the Validate SPL Query tool to validate this SPL query: {spl_to_validate}

Use the validate_spl tool with:
- query: {spl_to_validate}

Execute the tool and return the validation results.
""",
            expected_output="SPL validation results from the Validate SPL Query tool",
            agent=get_specialized_agent(task_name)
        )
    
    elif task_name == "search_oneshot":
        return Task(
            description=f"""
{context}You must use the Search Oneshot tool to execute this search request: "{user_request}"

Convert the user request to SPL and use the Search Oneshot tool with:
- query: [your converted SPL query]
- earliest_time: {earliest}
- latest_time: {latest}

IMPORTANT: After using the tool, prefix your SPL query in the response with "GENERATED_SPL: " followed by the exact query you used.

Execute the tool and return the search results with the SPL prefix.
""",
            expected_output="Search results from the Search Oneshot tool with GENERATED_SPL prefix",
            agent=get_specialized_agent(task_name)
        )
    
    elif task_name == "get_saved_searches":
        return Task(
            description=f"""
{context}You must use the Get Saved Searches tool to retrieve all saved searches.

Use the Get Saved Searches tool (no parameters needed).

Execute the tool and return the list of saved searches.
""",
            expected_output="Complete list of saved searches from the Get Saved Searches tool",
            agent=get_specialized_agent(task_name)
        )
    
    elif task_name == "search_export":
        spl_query = extracted_spl or extract_spl_from_request(user_request) or "index=* | head 10"
        
        return Task(
            description=f"""
{context}You must use the Search Export tool to export search results.

Use the Search Export tool with:
- query: {spl_query}
- earliest_time: {earliest}
- latest_time: {latest}
- max_count: {max_count}
- output_format: {output_format}

Execute the tool and return the exported results.
""",
            expected_output="Exported search results from the Search Export tool",
            agent=get_specialized_agent(task_name)
        )
    
    elif task_name == "get_indexes":
        return Task(
            description=f"""
{context}You must use the Get Indexes tool to retrieve available indexes.

Use the Get Indexes tool (no parameters needed).

Execute the tool and return the list of indexes.
""",
            expected_output="List of available indexes from the Get Indexes tool",
            agent=get_specialized_agent(task_name)
        )
    
    elif task_name == "run_saved_search":
        search_name = extracted_search_name or extract_saved_search_name_from_request(user_request) or "default_search"
        
        return Task(
            description=f"""
{context}You must use the Run Saved Search tool to execute the saved search.

Use the Run Saved Search tool with:
- search_name: {search_name}

Execute the tool and return the search results.
""",
            expected_output=f"Results from running saved search '{search_name}' using the Run Saved Search tool",
            agent=get_specialized_agent(task_name)
        )
    
    elif task_name == "get_config":
        return Task(
            description=f"""
{context}You must use the Get Config tool to retrieve Splunk configuration.

Use the Get Config tool (no parameters needed).

Execute the tool and return the configuration.
""",
            expected_output="Splunk configuration from the Get Config tool",
            agent=get_specialized_agent(task_name)
        )
    
    # Default fallback
    return Task(
        description=f"{context}{description} - Use the appropriate tool to complete this task.",
        expected_output="Task completed using the appropriate tool",
        agent=get_specialized_agent(task_name)
    )

def extract_spl_from_output(output):
    """Extract SPL query from task output"""
    import re
    
    # Look for GENERATED_SPL: prefix
    if 'GENERATED_SPL:' in output:
        spl_line = output.split('GENERATED_SPL:')[1].split('\n')[0].strip()
        # Clean up any brackets or extra characters
        spl_line = spl_line.strip('[]').strip()
        return spl_line
    
    # Look for index= patterns
    spl_match = re.search(r'index=\w+[^|\n]*(?:\|[^|\n]*)*', output)
    if spl_match:
        return spl_match.group(0).strip()
    
    return ""

def extract_search_name_from_output(output):
    """Extract search name from task output"""
    import re
    
    patterns = [
        r"saved as ['\"]([^'\"]+)['\"]",
        r"search ['\"]([^'\"]+)['\"].*saved",
        r"name ['\"]([^'\"]+)['\"]"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, output, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return ""

def extract_spl_from_request(user_request):
    """Extract SPL components from natural language request"""
    import re
    
    # Common patterns for Splunk searches
    request_lower = user_request.lower()
    
    # Build SPL based on request patterns
    spl_parts = []
    
    # Index detection
    index_match = re.search(r'from (\w+) index|index (\w+)', request_lower)
    if index_match:
        index_name = index_match.group(1) or index_match.group(2)
        spl_parts.append(f"index={index_name}")
    else:
        spl_parts.append("index=*")
    
    # Field extraction for "top X field" patterns
    top_match = re.search(r'top (\d+) (\w+)', request_lower)
    if top_match:
        count = top_match.group(1)
        field = top_match.group(2)
        spl_parts.append(f"| top {count} {field}")
    
    # Search terms
    if 'failed login' in request_lower or 'login fail' in request_lower:
        spl_parts.append('action=failure OR result=fail OR success=false')
    elif 'error' in request_lower:
        spl_parts.append('error OR ERROR')
    elif 'network traffic' in request_lower:
        spl_parts.append('src_ip=* dest_ip=*')
    
    # Time range
    if 'all time' in request_lower:
        # This will be handled by earliest/latest parameters
        pass
    
    return ' '.join(spl_parts) if spl_parts else "index=* | head 10"

def extract_search_name_from_request(user_request):
    """Extract search name from user request"""
    import re
    
    patterns = [
        r"save.*?(?:as|it as)\s*['\"]([^'\"]+)['\"]",
        r"name.*?['\"]([^'\"]+)['\"]",
        r"call.*?['\"]([^'\"]+)['\"]"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, user_request, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return None

def extract_saved_search_name_from_request(user_request):
    """Extract saved search name to run from user request"""
    import re
    
    patterns = [
        r"run.*?['\"]([^'\"]+)['\"]",
        r"execute.*?['\"]([^'\"]+)['\"]"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, user_request, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return "default_search"

def run_task_sequence(task_sequence):
    """Execute sequence with proper task chaining and dependency management"""
    
    print(f"🔗 Starting task sequence with {len(task_sequence)} tasks")
    
    # Execute tasks in dependency order
    completed_tasks = {}
    
    for i, task_info in enumerate(task_sequence):
        print(f"\n🚀 Executing task {i+1}/{len(task_sequence)}: {task_info['task']}")
        
        # Check if this task depends on another
        depends_on = task_info.get('depends_on')
        context_data = {}
        
        if depends_on is not None:
            if depends_on not in completed_tasks:
                print(f"❌ Task {i+1} depends on task {depends_on+1} which hasn't completed yet")
                continue
            
            # Use output from dependency
            dependency_output = completed_tasks[depends_on]
            context_data[depends_on] = dependency_output
            print(f"📥 Using output from task {depends_on+1} as context")
        
        # Create task with proper context
        task = create_task_from_info_with_context(task_info, i, context_data)
        
        # Create a mini-crew for this single task
        agent = get_specialized_agent(task_info['task'])
        single_task_crew = Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=True
        )
        
        try:
            print(f"🚀 Starting execution of task {i+1}: {task_info['task']}")
            
            # Execute the single task
            result = single_task_crew.kickoff()
            
            # Store the result for future dependent tasks
            if hasattr(result, 'raw'):
                task_output = result.raw
            elif hasattr(result, 'tasks_output') and result.tasks_output:
                task_output = str(result.tasks_output[0])
            else:
                task_output = str(result)
            
            completed_tasks[i] = task_output
            print(f"✅ Task {i+1} completed successfully")
            print(f"📤 Output preview: {task_output[:2000]}...")
            
            # Print delimiter for streamlit parsing
            print("-----END TASK-----")
            
        except Exception as e:
            error_msg = f"Task {i+1} failed: {str(e)}"
            completed_tasks[i] = error_msg
            print(f"❌ {error_msg}")
            print("-----END TASK-----")
    
    # Return summary of all completed tasks
    return {
        'completed_tasks': len(completed_tasks),
        'total_tasks': len(task_sequence),
        'outputs': completed_tasks
    }



# In crewFlow.py - Update the main execution logic
def run(task_name: str = None, task_sequence: str = None):
    if task_sequence:
        # Handle multiple tasks
        import json
        tasks_data = json.loads(task_sequence)
        return run_task_sequence(tasks_data)
    else:
        # Handle single task (current behavior)
        return run_single_task(task_name)


if __name__ == "__main__":
    task_sequence_env = os.getenv("TASK_SEQUENCE")
    
    if task_sequence_env:
        # Execute task sequence
        import json
        task_sequence = json.loads(task_sequence_env)
        result = run_task_sequence(task_sequence)
        print(result)
    elif len(sys.argv) >= 2:
        # Single task (backward compatibility)
        run(sys.argv[1])
    else:
        print("Usage: python crewFlow.py <task_name> OR set TASK_SEQUENCE environment variable")
