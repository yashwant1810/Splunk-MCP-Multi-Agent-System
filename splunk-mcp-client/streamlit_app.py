import streamlit as st 
import subprocess
import os
from dotenv import load_dotenv
from crewai import LLM
import json
import re
import time
import html  # For escaping HTML characters in stdout
load_dotenv()

gemini_llm = LLM(
    model="gemini/gemini-2.0-flash",
    provider="google",
    api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.3
)

def determine_task_sequence(user_input):
    """Determine if user wants multiple tasks and what they are"""
    routing_prompt = f"""
You are a strict task planner for a Splunk assistant. Break the user's request into **atomic Splunk tasks**.

Available tools:
- validate_spl: Validate an SPL query for safety
- search_oneshot: Run an SPL query  
- get_indexes: List available indexes
- run_saved_search: Run existing saved search
- search_export: Export search results
- get_saved_searches: List all saved searches
- get_config: Show Splunk configuration

Return ONLY a valid JSON array. Each task must have:
- "task": exact tool name from list above
- "description": what this step does
- "depends_on": task index it depends on (or null)

Example for "Search failed logins and then show saved searches":
[
  {{"task": "search_oneshot", "description": "Search for failed logins", "depends_on": null}},
  {{"task": "get_saved_searches", "description": "Show all saved searches", "depends_on": null}}
]

User request: "{user_input}"

Return only the JSON array, no other text:"""

    try:
        result = gemini_llm.call(routing_prompt).strip()
        print("🧠 GEMINI RAW PLAN:")
        print(result)
        
        # Clean up the response - remove markdown formatting if present
        if '```json' in result:
            result = result.split('```json')[1].split('```')[0].strip()
        elif '```' in result:
            result = result.split('```')[1].strip()
        
        # Find JSON array in the response
        import re
        json_match = re.search(r'\[.*\]', result, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            parsed_tasks = json.loads(json_str)
            
            # Validate the parsed tasks
            valid_tools = ['validate_spl', 'search_oneshot', 'get_indexes', 'run_saved_search', 
                          'search_export', 'get_saved_searches', 'get_config']
            
            validated_tasks = []
            for task in parsed_tasks:
                if isinstance(task, dict) and 'task' in task and 'description' in task:
                    if task['task'] in valid_tools:
                        validated_tasks.append({
                            'task': task['task'],
                            'description': task['description'],
                            'depends_on': task.get('depends_on')
                        })
            
            if validated_tasks:
                print(f"✅ Parsed {len(validated_tasks)} valid tasks")
                return validated_tasks
            else:
                print("❌ No valid tasks found in response")
        else:
            print("❌ No JSON array found in response")
            
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {e}")
        print(f"Raw response: {result}")
    except Exception as e:
        print(f"❌ Error in task planning: {e}")
    
    # Fallback: Create a reasonable task sequence based on common patterns
    print("🔄 Using fallback task planning...")
    return create_fallback_task_sequence(user_input)

def create_fallback_task_sequence(user_input):
    """Create a reasonable task sequence when AI planning fails"""
    user_lower = user_input.lower()
    tasks = []
    
    # Check if it's a search request
    if any(keyword in user_lower for keyword in ['find', 'search', 'show', 'get', 'top', 'list']):
        if 'index' in user_lower and not 'saved search' in user_lower:
            # It's a data search request
            tasks.append({
                "task": "search_oneshot",
                "description": "Execute the search query",
                "depends_on": None
            })
            
            # Check if they want to save it
            if any(save_word in user_lower for save_word in ['save', 'store', 'keep']):
                tasks.append({
                    "task": "save_search", 
                    "description": "Save the search query",
                    "depends_on": 0
                })
        
        # Check if they want to see saved searches
        if 'saved search' in user_lower and ('show' in user_lower or 'list' in user_lower or 'display' in user_lower):
            tasks.append({
                "task": "get_saved_searches",
                "description": "Show all saved searches", 
                "depends_on": None
            })
        
        # Check if they want to see indexes
        if 'index' in user_lower and ('show' in user_lower or 'list' in user_lower):
            tasks.append({
                "task": "get_indexes",
                "description": "Show available indexes",
                "depends_on": None
            })
    
    # If no tasks were created, default to a search
    if not tasks:
        tasks = [{
            "task": "search_oneshot",
            "description": "Execute search based on user request",
            "depends_on": None
        }]
    
    print(f"🔧 Fallback created {len(tasks)} tasks: {[t['task'] for t in tasks]}")
    return tasks



def extract_time_range(user_input):
    """Extract time range from natural language"""
    routing_prompt = f"""
Extract the time range from this natural language request and convert it to Splunk time format.
Return in format: earliest_time,latest_time

Examples:
- "last 24 hours" -> "-24h,now"
- "past week" -> "-1w,now" 
- "last hour" -> "-1h,now"
- "today" -> "@d,now"
- "yesterday" -> "-1d@d,-0d@d"
- "last 30 minutes" -> "-30m,now"
- "all time" -> "0,now"

If no time range is specified, return "-24h,now"

User request: {user_input}
"""
    result = gemini_llm.call(routing_prompt).strip()
    try:
        earliest, latest = result.split(',')
        return earliest.strip(), latest.strip()
    except:
        return "-24h", "now"

def detect_task_success(step_content, return_code):
    """Improved success detection logic for Splunk tasks"""
    
    # If the process failed, it's definitely a failure
    if return_code != 0:
        return False
    
    step_lower = step_content.lower()
    
    # Clear failure indicators
    failure_indicators = [
        'error occurred',
        'exception',
        'failed to',
        'could not',
        'unable to',
        'connection failed',
        'authentication failed',
        'query failed',
        'search failed',
        'timeout',
        'permission denied'
    ]
    
    # Check for actual failure patterns (not just the word "failed")
    for indicator in failure_indicators:
        if indicator in step_lower:
            return False
    
    # Success indicators
    success_indicators = [
        'generated_spl:',
        'found:',
        'query:',
        'search results',
        'event_count',
        'content":',
        '"format":'
    ]
    
    # Check for success patterns
    for indicator in success_indicators:
        if indicator in step_lower:
            return True
    
    # If we have JSON-like structure, it's probably successful
    if ('{' in step_content and '}' in step_content and 
        ('query' in step_lower or 'results' in step_lower or 'content' in step_lower)):
        return True
    
    # If we have a table-like structure (markdown table), it's successful
    if '|' in step_content and '---' in step_content:
        return True
    
    # Default: if no clear failure indicators and we have substantial content, consider it success
    return len(step_content.strip()) > 50


# Updated execute_task_sequence function with better success detection
def execute_task_sequence(task_sequence, user_request, manual_earliest, manual_latest, manual_index, max_count, output_format):
    """Execute entire sequence with better error handling and logging"""
    
    print(f"🚀 Starting execution of {len(task_sequence)} tasks")
    print(f"📋 Task sequence: {[task['task'] for task in task_sequence]}")
    
    # Set up environment for the entire sequence
    env = os.environ.copy()
    env["USER_REQUEST"] = user_request
    env["TASK_SEQUENCE"] = json.dumps(task_sequence)
    env["EARLIEST"] = manual_earliest if manual_earliest else extract_time_range(user_request)[0]
    env["LATEST"] = manual_latest if manual_latest else extract_time_range(user_request)[1]
    env["MAX_COUNT"] = str(max_count)
    env["OUTPUT_FORMAT"] = output_format
    
    if manual_index:
        env["FORCE_INDEX"] = manual_index
    
    print(f"🔧 Environment setup:")
    print(f"   - Time range: {env['EARLIEST']} to {env['LATEST']}")
    print(f"   - Max count: {env['MAX_COUNT']}")
    print(f"   - Output format: {env['OUTPUT_FORMAT']}")
    if manual_index:
        print(f"   - Forced index: {manual_index}")
    
    try:
        # Execute the entire workflow
        print("🏃 Running crewFlow.py...")
        result = subprocess.run(
            ["python", "crewFlow.py"],
            capture_output=True,
            text=True,
            env=env,
            timeout=600
        )
        
        print(f"📊 Process completed with return code: {result.returncode}")
        
        if result.stdout:
            print("📤 STDOUT:")
            print(result.stdout[:500] + "..." if len(result.stdout) > 500 else result.stdout)
        
        if result.stderr:
            print("📢 STDERR:")
            print(result.stderr[:500] + "..." if len(result.stderr) > 500 else result.stderr)
        
        # Split output per step using delimiter
        steps_output = result.stdout.split('-----END TASK-----')
        
        # Filter out empty steps and create results with improved success detection
        results = []
        for i, step in enumerate(steps_output):
            step_content = step.strip()
            # Only process non-empty steps and ensure we don't exceed task_sequence length
            if step_content and i < len(task_sequence):
                task_info = task_sequence[i]
                
                # Use improved success detection
                is_successful = detect_task_success(step_content, result.returncode)
                
                results.append({
                    'success': is_successful,
                    'stdout': step_content,
                    'stderr': result.stderr if result.stderr else '',
                    'task': task_info['task']
                })
                
                # Debug logging
                print(f"🔍 Task {i+1} ({task_info['task']}): {'✅ SUCCESS' if is_successful else '❌ FAILED'}")
        
        # If no results were parsed but we have output, create a single result
        if not results and result.stdout:
            # Use the first task info as fallback
            first_task = task_sequence[0] if task_sequence else {'task': 'unknown_task'}
            is_successful = detect_task_success(result.stdout, result.returncode)
            
            results = [{
                'success': is_successful,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'task': first_task['task']
            }]
        
        print(f"📋 Parsed {len(results)} task results")
        return results
        
    except subprocess.TimeoutExpired:
        print("⏰ Process timed out after 600 seconds")
        return [{
            'success': False,
            'stdout': '',
            'stderr': 'Process timed out after 600 seconds',
            'task': 'timeout'
        }]
    except Exception as e:
        print(f"❌ Error executing workflow: {e}")
        return [{
            'success': False,
            'stdout': '',
            'stderr': f'Execution error: {str(e)}',
            'task': 'error'
        }]
        

def parse_and_display_splunk_output(result_stdout):
    """Parse Splunk output and display it properly in Streamlit"""
    
    # Check if it's JSON-formatted Splunk output
    if '{' in result_stdout and 'query' in result_stdout and 'content' in result_stdout:
        try:
            # Extract JSON from the output (might have SPL prefix)
            json_match = re.search(r'\{.*\}', result_stdout, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                data = json.loads(json_str)
                
                # Display the SPL query
                if 'GENERATED_SPL:' in result_stdout:
                    spl_match = re.search(r'GENERATED_SPL:\s*(.+)', result_stdout)
                    if spl_match:
                        st.code(spl_match.group(1), language='sql')
                
                # Display query info
                st.write(f"**Query:** `{data.get('query', 'N/A')}`")
                st.write(f"**Events Found:** {data.get('event_count', 'N/A')}")
                
                # Parse and display the table content
                content = data.get('content', '')
                if '|' in content and ('---' in content or 'count' in content):
                    # Convert escaped newlines to actual newlines
                    content_with_newlines = content.replace('\\n', '\n')
                    
                    # Extract the markdown table
                    lines = content_with_newlines.split('\n')
                    table_lines = []
                    for line in lines:
                        if '|' in line and line.strip() and not line.strip().startswith('Query:') and not line.strip().startswith('Found:'):
                            table_lines.append(line.strip())
                    
                    if len(table_lines) >= 2:  # Header + separator + data (or header + data)
                        # Create proper Streamlit table
                        header_line = table_lines[0]
                        header = [col.strip() for col in header_line.split('|') if col.strip()]
                        
                        # Skip separator line if it exists (contains dashes)
                        data_start_idx = 2 if len(table_lines) > 1 and '-' in table_lines[1] else 1
                        
                        data_rows = []
                        for line in table_lines[data_start_idx:]:
                            if '|' in line and not '-' in line:
                                row = [col.strip() for col in line.split('|') if col.strip()]
                                if len(row) == len(header):  # Ensure row matches header length
                                    data_rows.append(row)
                        
                        # Display as Streamlit table
                        if data_rows:
                            import pandas as pd
                            df = pd.DataFrame(data_rows, columns=header)
                            
                            # Try to convert numeric columns
                            for col in df.columns:
                                if col.lower() in ['count', 'percent', '_tc', 'total']:
                                    try:
                                        df[col] = pd.to_numeric(df[col], errors='ignore')
                                    except:
                                        pass
                            
                            st.dataframe(df, use_container_width=True)
                        else:
                            st.write("No valid data rows found")
                            st.code(content_with_newlines, language='text')
                    else:
                        # Fallback: display content as code
                        st.code(content_with_newlines, language='text')
                else:
                    # Display non-table content with proper newlines
                    content_with_newlines = content.replace('\\n', '\n')
                    st.text(content_with_newlines)
                
                # Display search parameters
                if 'search_params' in data:
                    with st.expander("Search Parameters"):
                        st.json(data['search_params'])
                
                return True  # Successfully parsed
                
        except json.JSONDecodeError:
            pass  # Fall through to raw display
    
    return False  # Couldn't parse as Splunk JSON

# Replace your current output display section in streamlit_app.py with this:
def display_task_output(result):
    """Display task output with proper formatting"""
    
    if result.get('stdout'):
        # Try to parse as structured Splunk output
        if not parse_and_display_splunk_output(result['stdout']):
            # Fallback: display as raw text but properly formatted
            clean_output = result['stdout']
            
            # Use st.code for better formatting - show full output with scrolling
            st.code(clean_output, language='text')

# Streamlit App
st.set_page_config(page_title="Splunk Multi-Task Assistant", layout="wide")
st.title("🔍 Splunk Multi-Task Assistant")
st.markdown("Chain multiple Splunk operations together in natural language!")

# Initialize session state for workflow history
if 'workflow_history' not in st.session_state:
    st.session_state.workflow_history = []

# Main natural language input
user_request = st.text_area(
    "What would you like to do?", 
    placeholder="Examples:\n• Find top 10 MAC addresses from botsv3\n• Search for failed logins, export to CSV, then list all saved searches\n• Show me network traffic\n• List all indexes, then search for errors in the main index",
    height=120
)

# Manual overrides
with st.expander("🔧 Manual Overrides (Optional)"):
    col1, col2, col3 = st.columns(3)
    with col1:
        manual_earliest = st.text_input("Override earliest time", placeholder="e.g., -24h")
    with col2:
        manual_latest = st.text_input("Override latest time", placeholder="e.g., now")  
    with col3:
        manual_index = st.text_input("Force specific index", placeholder="e.g., botsv3")

    col4, col5 = st.columns(2)
    with col4:
        max_count = st.number_input("Max results", min_value=1, max_value=10000, value=100)
    with col5:
        output_format = st.selectbox("Export format", ["json", "csv", "xml"], index=0)

if st.button("🚀 Execute Workflow", type="primary"):
    if not user_request.strip():
        st.warning("Please enter a request.")
    else:
        # Analyze the request for task sequence
        with st.spinner("Planning workflow..."):
            task_sequence = determine_task_sequence(user_request)
        
        # Display planned workflow
        st.subheader("📋 Planned Workflow")
        workflow_col1, workflow_col2 = st.columns([2, 1])
        
        with workflow_col1:
            for i, task_info in enumerate(task_sequence):
                depends_text = ""
                if task_info.get('depends_on') is not None:
                    depends_text = f" (depends on step {task_info['depends_on'] + 1})"
                st.write(f"**Step {i+1}:** {task_info['description']}{depends_text}")
        
        with workflow_col2:
            st.info(f"**Total Steps:** {len(task_sequence)}")
            estimated_time = len(task_sequence) * 30  # Rough estimate
            st.info(f"**Est. Time:** ~{estimated_time}s")
        
        # Execute the workflow
        st.markdown("---")
        st.subheader("⚡ Execution")
        
        start_time = time.time()
        results = execute_task_sequence(
            task_sequence, user_request, manual_earliest, manual_latest, 
            manual_index, max_count, output_format
        )
        end_time = time.time()
        
        # Summary
        st.markdown("---")
        st.subheader("📊 Workflow Summary")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            successful_tasks = sum(1 for r in results if r.get('success', False))
            st.metric("Successful Steps", successful_tasks, f"out of {len(results)}")
        with col2:
            st.metric("Total Time", f"{end_time - start_time:.1f}s")
        with col3:
            success_rate = (successful_tasks / len(results)) * 100 if results else 0
            st.metric("Success Rate", f"{success_rate:.0f}%")
        
        # Store in history
        workflow_record = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'request': user_request,
            'tasks': len(task_sequence),
            'successful': successful_tasks,
            'total_time': end_time - start_time
        }
        st.session_state.workflow_history.append(workflow_record)
        
        # Detailed results
        with st.expander("📋 Detailed Results"):
            for i, result in enumerate(results):
                st.write(f"**Step {i+1}: {result['task']}**")
                status = "✅ Success" if result.get('success') else "❌ Failed"
                st.write(f"Status: {status}")
                if result.get('stdout'):
                    display_task_output(result)
                st.markdown("---")

# Sidebar with workflow history and examples
with st.sidebar:
    st.header("📈 Workflow History")
    if st.session_state.workflow_history:
        for i, record in enumerate(reversed(st.session_state.workflow_history[-10:])):  # Show last 10
            with st.expander(f"Workflow {len(st.session_state.workflow_history) - i}"):
                st.write(f"**Time:** {record['timestamp']}")
                st.write(f"**Request:** {record['request'][:100]}...")
                st.write(f"**Tasks:** {record['successful']}/{record['tasks']} successful")
                st.write(f"**Duration:** {record['total_time']:.1f}s")
    else:
        st.info("No workflows executed yet")
    
    if st.button("Clear History"):
        st.session_state.workflow_history = []
        st.rerun()
    


# Handle example selection
if 'example_selected' in st.session_state:
    user_request = st.session_state.example_selected
    del st.session_state.example_selected
    st.rerun()