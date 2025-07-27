# Splunk MCP Multi-Agent System

A comprehensive Splunk assistant platform that combines Model Context Protocol (MCP) client functionality, a Streamlit web interface, and AI agent crews for intelligent Splunk operations and analysis.

## Features

🤖 **AI Agent Crew** - Automated Splunk operations using CrewAI framework  
🌐 **Web Interface** - Interactive Streamlit dashboard for Splunk management  
🔌 **MCP Client** - Direct integration with Splunk via Model Context Protocol  
📊 **Data Analysis** - Intelligent log analysis and insights generation  
⚡ **Workflow Automation** - Streamlined Splunk query and monitoring workflows  

## Project Structure

```
SPLUNK_MCP/
├── .venv/                    # Virtual environment
├── splunk-mcp-client/        # Main application directory
│   ├── client.py            # MCP client for Splunk integration
│   ├── streamlit_app.py     # Web-based Splunk dashboard
│   ├── crewFlow.py          # AI agent crew workflows
│   ├── .env                 # Environment configuration
│   ├── __pycache__/         # Python cache files
│   └── [config files]       # Additional configuration files
```

## Components

### 1. MCP Client (`client.py`)
- Direct Model Context Protocol integration with Splunk
- Real-time data retrieval and query execution
- Secure authentication and connection management

### 2. Streamlit Web Interface (`streamlit_app.py`)
- Interactive web dashboard for Splunk operations
- Visual query builder and data visualization
- User-friendly interface for non-technical users
- Real-time monitoring and alerting capabilities

### 3. AI Agent Crew (`crewFlow.py`)
- Intelligent automation using CrewAI framework
- Multi-agent collaboration for complex Splunk tasks
- Automated incident response and analysis
- Smart recommendations and insights generation

## External Dependencies

This project requires the `splunk-mcp-server2` to be running separately. This is an external public repository that provides the MCP server functionality for Splunk integration.

## Prerequisites

- Python 3.12+
- Splunk Enterprise or Splunk Cloud instance
- Access to Splunk REST API
- Virtual environment (recommended)

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yashwant1810/Splunk-MCP-Multi-Agent-System.git
   cd Splunk-MCP-Multi-Agent-System
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up the MCP server (required external dependency):
   ```bash
   # Clone the MCP server in a separate directory
   cd ..
   git clone splunk-mcp-server2/python/server.py
   cd splunk-mcp-server2/python
   
   # Set up the server environment
   cp .env.example .env
   ```

5. Configure the MCP server:
   Edit the `.env` file in the `splunk-mcp-server2/python/` directory:
   ```bash
   # Required: Set transport to stdio
   TRANSPORT=stdio
   
   # Required: Add your Splunk authentication token
   SPLUNK_TOKEN=your-splunk-authentication-token
   
   # Optional: Other Splunk configuration
   SPLUNK_HOST=your-splunk-instance.com
   SPLUNK_PORT=8089
   ```

6. Install MCP server dependencies:
   ```bash
   # Still in splunk-mcp-server2/python directory
   pip install -r requirements.txt
   ```

7. Return to your project directory:
   ```bash
   cd ../../Splunk-MCP-Multi-Agent-System
   ```

## Configuration

1. Copy the example environment file for your client:
   ```bash
   cp splunk-mcp-client/.env.example splunk-mcp-client/.env
   ```

2. Edit your client's `.env` file:
   ```bash
   # Splunk Configuration (for direct access if needed)
   SPLUNK_HOST=your-splunk-instance.com
   SPLUNK_USERNAME=your-username
   SPLUNK_PASSWORD=your-password
   
   # MCP Client Configuration (connects to the external MCP server)
   MCP_SERVER_PATH=../splunk-mcp-server2/python/
   
   # Google AI Configuration (for CrewAI agents)
   GOOGLE_API_KEY=your-google-ai-api-key
   ```

3. Get a Google AI API key:
   - Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
   - Sign in with your Google account
   - Click "Create API Key"
   - Copy the generated API key and paste it in your `.env` file

4. Ensure the MCP server is properly configured (as mentioned in installation steps):
   - `TRANSPORT=stdio` in the MCP server's `.env`
   - `SPLUNK_TOKEN=your-token` in the MCP server's `.env`

## Usage

### 1. Streamlit Web Interface
Launch the interactive web dashboard:
```bash
cd splunk-mcp-client
streamlit run streamlit_app.py
```
Access the interface at `http://localhost:8501`

**Features:**
- Interactive Splunk query builder
- Real-time data visualization
- Dashboard creation and management
- Alert configuration and monitoring

### 2. MCP Client (Direct Integration)
Use the MCP client for programmatic Splunk access:
```bash
cd splunk-mcp-client
python client.py
```

**Capabilities:**
- Execute Splunk searches programmatically
- Retrieve and process log data
- Manage Splunk configurations
- Real-time data streaming

### 3. AI Agent Crew (Automated Operations)
Run intelligent automation workflows:
```bash
cd splunk-mcp-client
python crewFlow.py
```

**Agent Capabilities:**
- Automated incident detection and response
- Intelligent log analysis and pattern recognition
- Proactive monitoring and alerting
- Security threat analysis
- Performance optimization recommendations

## Use Cases

### Security Operations
- Automated threat detection and analysis
- Security incident response workflows
- Compliance reporting and monitoring
- Anomaly detection in security logs

### IT Operations
- Infrastructure monitoring and alerting
- Performance bottleneck identification
- Automated troubleshooting workflows
- Capacity planning and optimization

### Business Analytics
- Customer behavior analysis
- Application performance monitoring
- Business KPI tracking and reporting
- Predictive analytics and forecasting

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Streamlit     │    │   CrewAI Agents  │    │   MCP Client    │
│   Web Interface │    │   (crewFlow.py)  │    │   (client.py)   │
└─────────┬───────┘    └─────────┬────────┘    └─────────┬───────┘
          │                      │                       │
          └──────────────────────┼───────────────────────┘
                                 │
                    ┌────────────▼─────────────┐
                    │    splunk-mcp-server2    │
                    │    (External Repo)       │
                    └────────────┬─────────────┘
                                 │
                    ┌────────────▼─────────────┐
                    │      Splunk Instance     │
                    │   (Enterprise/Cloud)     │
                    └──────────────────────────┘
```

## Dependencies

### Core Libraries
- `streamlit` - Web interface framework
- `crewai` - AI agent orchestration
- `mcp` - Model Context Protocol client
- `python-dotenv` - Environment management
- `pydantic` - Data validation

### AI/ML Libraries
- LLM provider libraries (OpenAI, Anthropic, etc.)
- Additional ML libraries as needed by agents

## Development

### Adding New Agents
1. Define agent roles in `crewFlow.py`
2. Create specific tasks for Splunk operations
3. Configure agent collaboration workflows
4. Test with your Splunk environment

### Extending the Web Interface
1. Add new Streamlit components in `streamlit_app.py`
2. Integrate with MCP client for data retrieval
3. Create interactive visualizations
4. Implement real-time updates

### Custom MCP Operations
1. Extend the MCP client in `client.py`
2. Add new Splunk API integrations
3. Implement custom data processing
4. Add error handling and logging

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Important Notes

- **MCP Server Dependency**: This client requires the `splunk-mcp-server2` to be running. Make sure to clone and set up that repository separately before using this client.
- **MCP Server Configuration**: 
  - Use the `/python` folder from the splunk-mcp-server2 repository
  - Copy `.env.example` to `.env` in that directory
  - Set `TRANSPORT=stdio` in the MCP server's `.env` file
  - Add your `SPLUNK_TOKEN` to the MCP server's `.env` file
- **Server Connection**: Update your client's `.env` file with the correct MCP server configuration after setting up the external server.
- **API Keys**: Ensure you have a valid Google AI API key from [Google AI Studio](https://aistudio.google.com/app/apikey) when using the AI agent crew functionality.
- **Splunk Permissions**: Make sure your Splunk user has appropriate permissions for the operations you want to perform.

## Support

If you encounter any issues or have questions:
1. Check the [Issues](../../issues) page for existing solutions
2. Review the external `splunk-mcp-server2` documentation
3. Ensure all environment variables are properly configured
4. Verify Splunk connectivity and permissions

## Acknowledgments

- This project requires [splunk-mcp-server2](https://github.com/[original-author]/splunk-mcp-server2) to be running as a separate service
- Built with the Model Context Protocol specification
- Powered by CrewAI for intelligent agent orchestration
- Uses Streamlit for modern web interface design
