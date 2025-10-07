import type { IAuthenticateGeneric, ICredentialTestRequest, ICredentialType, INodeProperties } from 'n8n-workflow';

export class SpaceGooseApi implements ICredentialType {
	name = 'spaceGooseApi';

	displayName = 'Space Goose API';

	documentationUrl = 'https://docs.spacegoose.ai';

	properties: INodeProperties[] = [
		{
			displayName: 'BLACKBOX_API_KEY',
			name: 'BLACKBOX_API_KEY',
			type: 'string',
			required: true,
			default: '',
			placeholder: 'sk-...',
			description: 'API key used to authenticate with the Space Goose control plane.',
			typeOptions: {
				password: true,
			},
		},
		{
			displayName: 'Base URL',
			name: 'baseUrl',
			type: 'string',
			default: 'http://localhost:8000',
			description: 'Override the Space Goose API base URL if needed.',
		},
	];

	authenticate: IAuthenticateGeneric = {
		type: 'generic',
		properties: {
			headers: {
				'X-API-Key': '={{$credentials.BLACKBOX_API_KEY}}',
			},
		},
	};

	test: ICredentialTestRequest = {
		request: {
			method: 'GET',
			url: '={{ $credentials.baseUrl ? ($credentials.baseUrl.endsWith("/") ? $credentials.baseUrl.slice(0, -1) : $credentials.baseUrl) : "http://localhost:8000" }}/projects',
		},
	};
}
