import {
  IExecuteFunctions,
  INodeExecutionData,
  INodeType,
  INodeTypeDescription,
  NodeOperationError,
} from 'n8n-workflow';

export class BFAgentMCP implements INodeType {
  description: INodeTypeDescription = {
    displayName: 'BF Agent MCP',
    name: 'bfAgentMcp',
    icon: 'file:bfagent.svg',
    group: ['transform'],
    version: 1,
    subtitle: '={{$parameter["operation"] + ": " + $parameter["server"]}}',
    description: 'Execute tools from BF Agent MCP servers',
    defaults: {
      name: 'BF Agent MCP',
    },
    inputs: ['main'],
    outputs: ['main'],
    credentials: [
      {
        name: 'bfAgentApi',
        required: true,
      },
    ],
    properties: [
      {
        displayName: 'Operation',
        name: 'operation',
        type: 'options',
        noDataExpression: true,
        options: [
          {
            name: 'Execute Tool',
            value: 'execute',
            description: 'Execute a tool from any MCP server',
            action: 'Execute a tool',
          },
          {
            name: 'List Servers',
            value: 'listServers',
            description: 'List all available MCP servers',
            action: 'List all MCP servers',
          },
          {
            name: 'List Tools',
            value: 'listTools',
            description: 'List tools for a server',
            action: 'List tools for a server',
          },
        ],
        default: 'execute',
      },
      {
        displayName: 'MCP Server',
        name: 'server',
        type: 'options',
        displayOptions: {
          show: {
            operation: ['execute', 'listTools'],
          },
        },
        options: [
          {
            name: 'BF Agent MCP',
            value: 'bfagent-mcp',
            description: 'Core platform functionality',
          },
          {
            name: 'Book Writing MCP',
            value: 'book-writing-mcp',
            description: 'Book writing workflow tools',
          },
          {
            name: 'CAD MCP',
            value: 'cad-mcp',
            description: 'BIM/CAD processing tools',
          },
        ],
        default: 'bfagent-mcp',
        required: true,
        description: 'Select the MCP server to use',
      },
      {
        displayName: 'Tool Name',
        name: 'tool',
        type: 'string',
        displayOptions: {
          show: {
            operation: ['execute'],
          },
        },
        default: '',
        required: true,
        description: 'Name of the tool to execute',
        placeholder: 'book_create_project',
      },
      {
        displayName: 'Parameters',
        name: 'parameters',
        type: 'json',
        displayOptions: {
          show: {
            operation: ['execute'],
          },
        },
        default: '{}',
        description: 'Tool parameters as JSON object',
        placeholder: '{"title": "My Book", "genre": "Fantasy"}',
      },
      {
        displayName: 'Context ID',
        name: 'contextId',
        type: 'string',
        displayOptions: {
          show: {
            operation: ['execute'],
          },
        },
        default: '',
        description: 'Workflow context ID to link multiple tool calls',
        placeholder: 'workflow_{{$workflow.id}}',
      },
      {
        displayName: 'Merge Previous Result',
        name: 'mergePreviousResult',
        type: 'boolean',
        displayOptions: {
          show: {
            operation: ['execute'],
          },
        },
        default: false,
        description: 'Whether to merge result from previous node into parameters',
      },
    ],
  };

  async execute(this: IExecuteFunctions): Promise<INodeExecutionData[][]> {
    const items = this.getInputData();
    const returnData: INodeExecutionData[] = [];
    const operation = this.getNodeParameter('operation', 0) as string;

    // Get credentials
    const credentials = await this.getCredentials('bfAgentApi');
    const baseUrl = credentials.baseUrl as string;
    const apiToken = credentials.apiToken as string;

    for (let i = 0; i < items.length; i++) {
      try {
        let responseData: any;

        if (operation === 'listServers') {
          // List all MCP servers
          const response = await this.helpers.request({
            method: 'GET',
            url: `${baseUrl}/api/mcp/servers`,
            headers: {
              'Authorization': `Bearer ${apiToken}`,
              'Content-Type': 'application/json',
            },
            json: true,
          });

          responseData = response;

        } else if (operation === 'listTools') {
          // List tools for specific server
          const server = this.getNodeParameter('server', i) as string;

          const response = await this.helpers.request({
            method: 'GET',
            url: `${baseUrl}/api/mcp/tools?server=${server}`,
            headers: {
              'Authorization': `Bearer ${apiToken}`,
              'Content-Type': 'application/json',
            },
            json: true,
          });

          responseData = response;

        } else if (operation === 'execute') {
          // Execute tool
          const server = this.getNodeParameter('server', i) as string;
          const tool = this.getNodeParameter('tool', i) as string;
          let parameters = this.getNodeParameter('parameters', i) as string;
          const contextId = this.getNodeParameter('contextId', i, '') as string;
          const mergePreviousResult = this.getNodeParameter('mergePreviousResult', i, false) as boolean;

          // Parse parameters
          let params: any;
          try {
            params = typeof parameters === 'string' ? JSON.parse(parameters) : parameters;
          } catch (error) {
            throw new NodeOperationError(
              this.getNode(),
              `Invalid JSON in parameters: ${error.message}`,
              { itemIndex: i }
            );
          }

          // Merge previous result if enabled
          if (mergePreviousResult && items[i].json) {
            params = { ...params, ...items[i].json };
          }

          // Build request body
          const body: any = {
            server,
            tool,
            params,
          };

          if (contextId) {
            body.context_id = contextId;
          }

          // Execute tool
          const response = await this.helpers.request({
            method: 'POST',
            url: `${baseUrl}/api/mcp/execute`,
            headers: {
              'Authorization': `Bearer ${apiToken}`,
              'Content-Type': 'application/json',
            },
            body,
            json: true,
          });

          responseData = response;
        }

        // Add execution metadata
        const executionData = {
          json: {
            ...responseData,
            _metadata: {
              operation,
              timestamp: new Date().toISOString(),
              itemIndex: i,
            },
          },
        };

        returnData.push(executionData);

      } catch (error) {
        if (this.continueOnFail()) {
          returnData.push({
            json: {
              error: error.message,
              _metadata: {
                operation,
                failed: true,
                itemIndex: i,
              },
            },
          });
          continue;
        }
        throw error;
      }
    }

    return [returnData];
  }
}
