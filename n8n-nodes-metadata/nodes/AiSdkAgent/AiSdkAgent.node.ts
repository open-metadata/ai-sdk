import {
	IDataObject,
	IExecuteFunctions,
	INodeExecutionData,
	INodeType,
	INodeTypeDescription,
	NodeApiError,
	NodeOperationError,
} from 'n8n-workflow';

import {
	AiSdk,
	AiSdkError,
	AuthenticationError,
	AgentNotFoundError,
	AgentNotEnabledError,
	AgentExecutionError,
} from '@openmetadata/ai-sdk';

export class AiSdkAgent implements INodeType {
	description: INodeTypeDescription = {
		displayName: 'AI SDK Agent',
		name: 'aiSdkAgent',
		icon: 'file:metadata.png',
		group: ['transform'],
		version: 1,
		subtitle: '={{$parameter["agentName"]}}',
		description: 'Invoke an OpenMetadata DynamicAgent',
		defaults: {
			name: 'AI SDK Agent',
		},
		inputs: ['main'],
		outputs: ['main'],
		credentials: [
			{
				name: 'aiSdkApi',
				required: true,
			},
		],
		properties: [
			{
				displayName: 'Agent Name',
				name: 'agentName',
				type: 'string',
				default: '',
				placeholder: 'my-agent',
				description: 'The name of the DynamicAgent to invoke',
				required: true,
			},
			{
				displayName: 'Message',
				name: 'message',
				type: 'string',
				typeOptions: {
					rows: 4,
				},
				default: '',
				placeholder: 'Enter your message or query for the agent',
				description: 'The message to send to the agent',
				required: true,
			},
			{
				displayName: 'Conversation ID',
				name: 'conversationId',
				type: 'string',
				default: '',
				placeholder: 'Optional: continue a conversation',
				description: 'Optional conversation ID for multi-turn conversations',
				required: false,
			},
		],
	};

	async execute(this: IExecuteFunctions): Promise<INodeExecutionData[][]> {
		const items = this.getInputData();
		const returnData: INodeExecutionData[] = [];

		const credentials = await this.getCredentials('aiSdkApi');
		const serverUrl = credentials.serverUrl as string;
		const jwtToken = credentials.jwtToken as string;

		const client = new AiSdk({
			host: serverUrl,
			token: jwtToken,
			timeout: 300000, // 5 minute timeout to match API
		});

		for (let i = 0; i < items.length; i++) {
			try {
				const agentName = this.getNodeParameter('agentName', i) as string;
				const message = this.getNodeParameter('message', i) as string;
				const conversationId = this.getNodeParameter('conversationId', i, '') as string;

				// Validate required fields
				if (!agentName) {
					throw new NodeOperationError(this.getNode(), 'Agent Name is required', { itemIndex: i });
				}
				if (!message) {
					throw new NodeOperationError(this.getNode(), 'Message is required', { itemIndex: i });
				}

				// Invoke the agent using the SDK
				const response = await client.agent(agentName).invoke(message, {
					conversationId: conversationId || undefined,
				});

				// Build response object, excluding toolsUsed to match original behavior
				const result: IDataObject = {
					conversationId: response.conversationId,
					response: response.response,
				};

				// Include usage if present
				if (response.usage) {
					result.usage = {
						promptTokens: response.usage.promptTokens,
						completionTokens: response.usage.completionTokens,
						totalTokens: response.usage.totalTokens,
					};
				}

				returnData.push({
					json: result,
					pairedItem: { item: i },
				});
			} catch (error) {
				if (this.continueOnFail()) {
					const errorMessage = error instanceof Error ? error.message : 'Unknown error';
					returnData.push({
						json: { error: errorMessage },
						pairedItem: { item: i },
					});
					continue;
				}

				if (error instanceof NodeApiError || error instanceof NodeOperationError) {
					throw error;
				}

				// Convert SDK errors to n8n NodeApiError with descriptive messages
				const agentName = this.getNodeParameter('agentName', i) as string;
				let errorMessage: string;
				let httpCode: string;

				if (error instanceof AuthenticationError) {
					errorMessage = 'Authentication failed: Invalid or expired JWT token';
					httpCode = '401';
				} else if (error instanceof AgentNotEnabledError) {
					errorMessage = 'Agent is not API-enabled. Enable API access in the OpenMetadata UI.';
					httpCode = '403';
				} else if (error instanceof AgentNotFoundError) {
					errorMessage = `Agent "${agentName}" not found`;
					httpCode = '404';
				} else if (error instanceof AgentExecutionError) {
					errorMessage = 'Agent execution failed. Check the agent configuration in OpenMetadata.';
					httpCode = '500';
				} else if (error instanceof AiSdkError) {
					errorMessage = error.message || 'OpenMetadata API error occurred';
					httpCode = String(error.statusCode || 500);
				} else {
					const unknownError = error as { message?: string; statusCode?: number };
					errorMessage = unknownError.message || 'Unknown error occurred';
					httpCode = String(unknownError.statusCode || 500);
				}

				throw new NodeApiError(this.getNode(), {
					message: errorMessage,
					httpCode,
				}, {
					itemIndex: i,
				});
			}
		}

		return [returnData];
	}
}
