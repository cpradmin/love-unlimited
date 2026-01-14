const { Server } = require("@modelcontextprotocol/sdk/server/index.js");
const { StdioServerTransport } = require("@modelcontextprotocol/sdk/server/stdio.js");
const { CallToolRequestSchema, ListToolsRequestSchema, McpError } = require("@modelcontextprotocol/sdk/types.js");
const axios = require('axios');
const fs = require('fs').promises;
const path = require('path');

// Configuration
const HUB_URL = process.env.HUB_URL || 'http://localhost:9004';
const API_KEY = process.env.HUB_API_KEY || 'lu_jon_QmZCAglY6kqsIdl6cRADpQ'; // Default to Jon's key

class HubMcpServer {
  constructor() {
    this.server = new Server(
      {
        name: "love-unlimited-hub-server",
        version: "1.0.0",
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.setupToolHandlers();
  }

  setupToolHandlers() {
    // List available tools
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      return {
        tools: [
          {
            name: "list_beings",
            description: "List all available AI beings in the Love-Unlimited hub",
            inputSchema: {
              type: "object",
              properties: {},
            },
          },
          {
            name: "get_memories",
            description: "Retrieve memories for a specific being",
            inputSchema: {
              type: "object",
              properties: {
                being_id: {
                  type: "string",
                  description: "The being ID (jon, claude, grok, etc.)",
                },
                query: {
                  type: "string",
                  description: "Search query for memories (optional)",
                },
                limit: {
                  type: "number",
                  description: "Maximum number of memories to return (default: 10)",
                },
              },
              required: ["being_id"],
            },
          },
          {
            name: "ask_being",
            description: "Send a question or message to an AI being",
            inputSchema: {
              type: "object",
              properties: {
                being_id: {
                  type: "string",
                  description: "The being ID to ask (claude, grok, etc.)",
                },
                message: {
                  type: "string",
                  description: "The message to send",
                },
              },
              required: ["being_id", "message"],
            },
          },
          {
            name: "read_file",
            description: "Read the contents of a file",
            inputSchema: {
              type: "object",
              properties: {
                file_path: {
                  type: "string",
                  description: "Path to the file to read",
                },
                start_line: {
                  type: "number",
                  description: "Starting line number (optional)",
                },
                end_line: {
                  type: "number",
                  description: "Ending line number (optional)",
                },
              },
              required: ["file_path"],
            },
          },
          {
            name: "list_directory",
            description: "List contents of a directory",
            inputSchema: {
              type: "object",
              properties: {
                dir_path: {
                  type: "string",
                  description: "Path to the directory to list",
                },
              },
              required: ["dir_path"],
            },
          },
          {
            name: "run_command_on_session",
            description: "Run a command on an active terminal session (use carefully - confirmation may be required)",
            inputSchema: {
              type: "object",
              properties: {
                session_id: {
                  type: "string",
                  description: "The session ID to run command on",
                },
                command: {
                  type: "string",
                  description: "The command to execute",
                },
              },
              required: ["session_id", "command"],
            },
          },
          {
            name: "get_session_output",
            description: "Get the current output/buffer of a terminal session",
            inputSchema: {
              type: "object",
              properties: {
                session_id: {
                  type: "string",
                  description: "The session ID to get output from",
                },
                lines: {
                  type: "number",
                  description: "Number of lines to retrieve (default: 100)",
                },
              },
              required: ["session_id"],
            },
          },
        ],
      };
    });

    // Handle tool calls
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      try {
        switch (name) {
          case "list_beings":
            return await this.listBeings();
          case "get_memories":
            return await this.getMemories(args.being_id, args.query, args.limit);
          case "ask_being":
            return await this.askBeing(args.being_id, args.message);
          case "read_file":
            return await this.readFile(args.file_path, args.start_line, args.end_line);
          case "list_directory":
            return await this.listDirectory(args.dir_path);
          case "run_command_on_session":
            return await this.runCommandOnSession(args.session_id, args.command);
          case "get_session_output":
            return await this.getSessionOutput(args.session_id, args.lines);
          default:
            throw new McpError(ErrorCode.MethodNotFound, `Unknown tool: ${name}`);
        }
      } catch (error) {
        throw new McpError(ErrorCode.InternalError, error.message);
      }
    });
  }

  async listBeings() {
    try {
      // The hub doesn't have a direct list beings endpoint, so we'll use a known list
      const beings = ["jon", "claude", "grok", "ara", "ani", "tabby", "swarm", "dream_team"];

      return {
        content: [
          {
            type: "text",
            text: `Available beings: ${beings.join(", ")}`,
          },
        ],
      };
    } catch (error) {
      throw new Error(`Failed to list beings: ${error.message}`);
    }
  }

  async getMemories(beingId, query = "", limit = 10) {
    try {
      const response = await axios.get(`${HUB_URL}/recall`, {
        params: {
          q: query,
          being_id: beingId,
          limit: limit,
        },
        headers: {
          'X-API-Key': API_KEY,
        },
      });

      const memories = response.data.memories || [];
      const text = memories.map(mem => `[${mem.timestamp}] ${mem.content}`).join('\n\n');

      return {
        content: [
          {
            type: "text",
            text: `Memories for ${beingId}:\n\n${text}`,
          },
        ],
      };
    } catch (error) {
      throw new Error(`Failed to get memories: ${error.response?.data?.detail || error.message}`);
    }
  }

  async askBeing(beingId, message) {
    try {
      const response = await axios.post(`${HUB_URL}/ask`, {
        being_id: beingId,
        message: message,
      }, {
        headers: {
          'X-API-Key': API_KEY,
          'Content-Type': 'application/json',
        },
      });

      return {
        content: [
          {
            type: "text",
            text: response.data.response || response.data.message,
          },
        ],
      };
    } catch (error) {
      throw new Error(`Failed to ask being: ${error.response?.data?.detail || error.message}`);
    }
  }

  async readFile(filePath, startLine, endLine) {
    try {
      const content = await fs.readFile(filePath, 'utf-8');
      let lines = content.split('\n');

      if (startLine !== undefined || endLine !== undefined) {
        const start = startLine || 0;
        const end = endLine || lines.length;
        lines = lines.slice(start, end);
      }

      return {
        content: [
          {
            type: "text",
            text: lines.join('\n'),
          },
        ],
      };
    } catch (error) {
      throw new Error(`Failed to read file: ${error.message}`);
    }
  }

  async listDirectory(dirPath) {
    try {
      const items = await fs.readdir(dirPath);
      const text = items.join('\n');

      return {
        content: [
          {
            type: "text",
            text: `Contents of ${dirPath}:\n${text}`,
          },
        ],
      };
    } catch (error) {
      throw new Error(`Failed to list directory: ${error.message}`);
    }
  }

  async runCommandOnSession(sessionId, command) {
    try {
      const response = await axios.post(`${HUB_URL}/terminal/${sessionId}/command`, {
        command: command,
      }, {
        headers: {
          'X-API-Key': API_KEY,
        },
      });

      return {
        content: [
          {
            type: "text",
            text: `Command executed on session ${sessionId}: ${response.data.message || 'Success'}`,
          },
        ],
      };
    } catch (error) {
      throw new Error(`Failed to run command on session: ${error.response?.data?.detail || error.message}`);
    }
  }

  async getSessionOutput(sessionId, lines = 100) {
    try {
      const response = await axios.get(`${HUB_URL}/terminal/${sessionId}/output`, {
        params: { lines: lines },
        headers: {
          'X-API-Key': API_KEY,
        },
      });

      return {
        content: [
          {
            type: "text",
            text: `Session ${sessionId} output:\n${response.data.output || 'No output'}`,
          },
        ],
      };
    } catch (error) {
      throw new Error(`Failed to get session output: ${error.response?.data?.detail || error.message}`);
    }
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error("Love-Unlimited MCP server running on stdio");
  }
}

const server = new HubMcpServer();
server.run().catch(console.error);