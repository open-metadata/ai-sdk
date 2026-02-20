import {
	IAuthenticateGeneric,
	ICredentialTestRequest,
	ICredentialType,
	INodeProperties,
} from 'n8n-workflow';

export class AiSdkApi implements ICredentialType {
	name = 'aiSdkApi';
	displayName = 'OpenMetadata API';
	documentationUrl = 'https://docs.open-metadata.org';
	properties: INodeProperties[] = [
		{
			displayName: 'Server URL',
			name: 'serverUrl',
			type: 'string',
			default: '',
			placeholder: 'https://your-openmetadata-instance.com',
			description: 'The URL of your OpenMetadata instance',
			required: true,
		},
		{
			displayName: 'JWT Token',
			name: 'jwtToken',
			type: 'string',
			typeOptions: {
				password: true,
			},
			default: '',
			description: 'JWT token for authentication (bot token or personal access token)',
			required: true,
		},
	];

	authenticate: IAuthenticateGeneric = {
		type: 'generic',
		properties: {
			headers: {
				Authorization: '={{"Bearer " + $credentials.jwtToken}}',
			},
		},
	};

	test: ICredentialTestRequest = {
		request: {
			baseURL: '={{$credentials.serverUrl}}',
			url: '/api/v1/agents/dynamic',
			method: 'GET',
			qs: {
				limit: 1,
				apiEnabled: 'true',
			},
		},
	};
}
