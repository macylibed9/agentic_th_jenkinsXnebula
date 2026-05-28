# Intelligent Test Harness Agent Project

## Project Overview

This project develops an **Intelligent Test Harness Agent** - an AI assistant that orchestrates automated testing workflows across multiple tools and systems using MCP (Model Context Protocol) servers.

### Current Status
- ✅ **Jenkins MCP Server**: Built and functional for Jenkins CI/CD integration
- ✅ **Claude Agent**: Implemented using Portkey/ADI Hub with natural language interface
- 🔄 **In Progress**: Addressing token limitations and expanding MCP tool ecosystem
- 🎯 **Goal**: Multi-tool orchestration for comprehensive test automation

## Architecture

### Core Components
- **Claude Agent** ([claude_jenkins_agent.py](claude_jenkins_agent.py)): Main agent using Claude Sonnet 4 via Portkey
- **Jenkins MCP Server** ([jenkins_mcp_server.py](jenkins_mcp_server.py)): REST API wrapper for Jenkins
- **FastMCP Implementation** ([jenkins_mcp_server_fastmcp.py](jenkins_mcp_server_fastmcp.py)): Cleaner server implementation

### Technology Stack
- **AI Model**: Claude Sonnet 4 (@bedrock-global/us.anthropic.claude-sonnet-4-20250514-v1:0)
- **API Gateway**: Portkey AI (ADI Hub)
- **Protocol**: MCP (Model Context Protocol) for tool integration
- **CI/CD**: Jenkins REST API integration
- **Language**: Python 3.11+ with async/await

### Agent System Prompt
The agent is designed as an "Intelligent Test Harness Agent" with these capabilities:
- Monitor test execution and analyze results
- Orchestrate workflows across CI/CD, version control, issue tracking
- Provide actionable insights and automate repetitive tasks
- Chain multiple tools together for complex workflows
- Adapt to any available MCP servers

## Current Challenges & Solutions

### Token Limitation Issues
**Problem**: Agent hits token limits when requesting help or processing large outputs
**Solutions in Progress**:
- Implement output truncation in MCP servers (console logs limited to 10KB)
- Use streaming responses for large data
- Implement result summarization before sending to Claude
- Consider context compression techniques

### Future MCP Integrations
**Target Tools**:
- Git/GitHub (version control operations)
- Jira/Issue Tracking (ticket management)
- Monitoring Systems (log analysis, alerts)
- Notification Systems (Slack, Teams, email)
- Database Tools (test data management)

## Coding Standards & Preferences

### Python Standards
- **Version**: Python 3.11+ features preferred
- **Style**: Follow PEP 8 with clear, readable code
- **Async**: Use async/await for all I/O operations
- **Error Handling**: Comprehensive error handling with meaningful messages
- **Documentation**: Clear docstrings for complex functions

### File Organization
```
├── claude_jenkins_agent.py     # Main Claude agent
├── jenkins_mcp_server.py       # Basic MCP server
├── jenkins_mcp_server_fastmcp.py  # FastMCP implementation
├── test_*.py                   # Test scripts
├── .env                        # Environment variables
└── requirements.txt           # Dependencies
```

### Environment Configuration
Required environment variables:
```bash
# ADI Hub/Portkey
PORTKEY_API_KEY=your_portkey_key

# Jenkins
JENKINS_URL=https://your-jenkins.com
JENKINS_USERNAME=your_username
JENKINS_TOKEN=your_api_token
```

## Development Guidelines

### Token Efficiency
- **Summarize large outputs** before sending to Claude
- **Truncate console logs** to essential information (first/last 5KB)
- **Use structured responses** instead of raw JSON dumps
- **Implement streaming** for real-time data processing

### MCP Server Development
- **Follow MCP protocol** standards strictly
- **Implement proper error handling** for all API calls
- **Provide clear tool descriptions** for Claude understanding
- **Use appropriate input schemas** with validation
- **Format outputs** in human-readable format when possible

### Agent Behavior
- **Be proactive**: Anticipate user needs and fetch relevant data
- **Be concise**: Summarize results, offer details on request
- **Chain tools intelligently**: Use multiple MCP tools in sequence
- **Adapt to available tools**: Work with whatever MCP servers are connected
- **Focus on root causes**: When analyzing failures, identify patterns and suggest fixes

## Testing Strategy

### Current Tests
- **Connection testing** ([test_jenkins_mcp_server.py](test_jenkins_mcp_server.py))
- **Rate limit handling** ([check_rate_limit.py](check_rate_limit.py))
- **Portkey integration** ([test_portkey.py](test_portkey.py))

### Testing Approach
- Test MCP server connectivity before agent interaction
- Validate authentication and authorization
- Test tool discovery and execution
- Verify error handling and retry mechanisms
- Load test for token limitations

## Future Roadmap

### Phase 1: Optimization (Current)
- Resolve token limitation issues
- Improve output formatting and summarization
- Enhance error handling and retry logic
- Optimize MCP server performance

### Phase 2: Multi-Tool Integration
- Add Git/GitHub MCP server
- Integrate issue tracking (Jira/Linear)
- Connect monitoring and alerting systems
- Build unified workflow orchestration

### Phase 3: Intelligence Enhancement
- Pattern recognition in test failures
- Automated root cause analysis
- Predictive failure detection
- Smart workflow optimization

### Phase 4: Enterprise Features
- Multi-team workflow coordination
- Compliance and audit logging
- Advanced reporting and analytics
- Integration with existing enterprise tools

## Operational Notes

### Deployment
- Run agent via: `python claude_jenkins_agent.py`
- MCP servers start automatically via stdio
- Requires active network connection to ADI Hub and Jenkins

### Monitoring
- Agent provides debug output showing tool calls and responses
- Rate limiting includes exponential backoff (5s, 10s, 20s)
- All API errors are logged with full context

### Maintenance
- Regularly update MCP protocol implementations
- Monitor token usage and optimize where possible
- Keep Jenkins API integration current with Jenkins updates
- Review and update system prompts based on usage patterns

---

**Note**: This project leverages cutting-edge AI orchestration capabilities to revolutionize test automation workflows. The focus is on building a robust, extensible foundation that can adapt to diverse testing environments and toolchains.