const { Server } = require("@modelcontextprotocol/sdk/server/index.js");
const { StdioServerTransport } = require("@modelcontextprotocol/sdk/server/stdio.js");
const { CallToolRequestSchema, ErrorCode, ListResourcesRequestSchema, ListToolsRequestSchema, McpError, ReadResourceRequestSchema } = require("@modelcontextprotocol/sdk/types.js");
const express = require('express');
const cors = require('cors');
const fs = require('fs').promises;
const path = require('path');
const { exec } = require('child_process');
const util = require('util');

const execAsync = util.promisify(exec);

// Tool helper functions
async function listDirectory(path) {
  const items = await fs.readdir(path);
  return { content: items.join('\n') };
}

async function readFile(path, startLine, endLine) {
  const content = await fs.readFile(path, 'utf-8');
  let lines = content.split('\n');
  if (startLine !== undefined || endLine !== undefined) {
    const start = startLine || 0;
    const end = endLine || lines.length;
    lines = lines.slice(start, end);
  }
  return { content: lines.join('\n') };
}

async function runDockerCommand(command) {
  const result = await execAsync(`docker ${command}`);
  return { content: result.stdout || result.stderr };
}

async function runBashCommand(command) {
  const result = await execAsync(command);
  return { content: result.stdout || result.stderr };
}

class FileSystemServer {
  constructor() {
    this.server = new Server(
      {
        name: "filesystem-server",
        version: "1.0.0",
      },
      {
        capabilities: {
          tools: {},
          resources: {},
        },
      }
    );

    this.setupToolHandlers();
    this.setupResourceHandlers();
  }

  setupToolHandlers() {
    // List directory contents
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      return {
        tools: [
          {
            name: "list_directory",
            description: "List contents of a directory",
            inputSchema: {
              type: "object",
              properties: {
                path: {
                  type: "string",
                  description: "Path to the directory to list",
                },
              },
              required: ["path"],
            },
          },
          {
            name: "read_file",
            description: "Read contents of a file",
            inputSchema: {
              type: "object",
              properties: {
                path: {
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
              required: ["path"],
            },
          },
          {
            name: "run_docker_command",
            description: "Run a Docker command",
            inputSchema: {
              type: "object",
              properties: {
                command: {
                  type: "string",
                  description: "Docker command to run",
                },
              },
              required: ["command"],
            },
          },
          {
            name: "run_bash_command",
            description: "Run a bash command",
            inputSchema: {
              type: "object",
              properties: {
                command: {
                  type: "string",
                  description: "Bash command to run",
                },
              },
              required: ["command"],
            },
          },
        ],
      };
    });

    // Handle tool calls
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      try {
        let result;
        switch (name) {
          case "list_directory":
            result = await listDirectory(args.path);
            break;
          case "read_file":
            result = await readFile(args.path, args.start_line, args.end_line);
            break;
          case "run_docker_command":
            result = await runDockerCommand(args.command);
            break;
          case "run_bash_command":
            result = await runBashCommand(args.command);
            break;
          default:
            throw new McpError(
              ErrorCode.MethodNotFound,
              `Unknown tool: ${name}`
            );
        }
        return {
          content: [
            {
              type: "text",
              text: result.content,
            },
          ],
        };
      } catch (error) {
        return {
          content: [
            {
              type: "text",
              text: `Error: ${error.message}`,
            },
          ],
          isError: true,
        };
      }
    });
  }

  setupResourceHandlers() {
    // List resources (for now, empty)
    this.server.setRequestHandler(ListResourcesRequestSchema, async () => {
      return {
        resources: [],
      };
    });

    // Read resource
    this.server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
      throw new McpError(
        ErrorCode.MethodNotFound,
        `Resource not found: ${request.params.uri}`
      );
    });
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error("MCP Filesystem server running on stdio");
  }
}

// Express server for health check and API
const app = express();
app.use(cors());
app.use(express.json());

app.get('/health', (req, res) => {
  res.json({ status: 'healthy' });
});

// HTTP API for tools
app.post('/tools/list_directory', async (req, res) => {
  try {
    const { path } = req.body;
    if (!path) return res.status(400).json({ error: 'Missing path' });
    const result = await listDirectory(path);
    res.json(result);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/tools/read_file', async (req, res) => {
  try {
    const { path, start_line, end_line } = req.body;
    if (!path) return res.status(400).json({ error: 'Missing path' });
    const result = await readFile(path, start_line, end_line);
    res.json(result);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/tools/run_docker_command', async (req, res) => {
  try {
    const { command } = req.body;
    if (!command) return res.status(400).json({ error: 'Missing command' });
    const result = await runDockerCommand(command);
    res.json(result);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/tools/run_bash_command', async (req, res) => {
  try {
    const { command } = req.body;
    if (!command) return res.status(400).json({ error: 'Missing command' });
    const result = await runBashCommand(command);
    res.json(result);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

const PORT = process.env.MCP_SERVER_PORT || 3000;
app.listen(PORT, () => {
  console.error(`Health check server listening on port ${PORT}`);
});

// Run MCP server
const server = new FileSystemServer();
server.run().catch(console.error);