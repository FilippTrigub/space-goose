import type {
	IDataObject,
	IExecuteFunctions,
	INodeExecutionData,
	INodeType,
	INodeTypeDescription,
} from 'n8n-workflow';
import { NodeOperationError } from 'n8n-workflow';
import { GooseClient } from './transport/goose.client';
import type { GooseStreamResult } from './interfaces';

const nodeDescription: INodeTypeDescription = {
	displayName: 'Space Goose',
	name: 'spaceGoose',
	group: ['transform'],
	version: 1,
	description: 'Send instructions to a Space Goose project session',
	defaults: {
		name: 'Space Goose',
	},
	inputs: ['main'],
	outputs: ['main'],
	credentials: [
		{
			name: 'spaceGooseApi',
			required: true,
		},
	],
	properties: [
		{
			displayName: 'Project ID',
			name: 'projectId',
			type: 'string',
			required: true,
			default: '',
			description: 'Identifier of the Space Goose project to target',
		},
		{
			displayName: 'Message',
			name: 'message',
			type: 'string',
			required: true,
			default: '',
			description: 'Content to send to the agent. You can reference input data via expressions.',
		},
		{
			displayName: 'Capture Output',
			name: 'captureOutput',
			type: 'boolean',
			default: true,
			description:
				'Whether to stream the assistant response and return the aggregated text (disable to send without waiting for output)',
		},
		{
			displayName: 'Session ID',
			name: 'sessionId',
			type: 'string',
			default: '',
			description: 'Existing session to reuse. Leave blank to create a new session automatically.',
		},
		{
			displayName: 'Session Name',
			name: 'sessionName',
			type: 'string',
			default: '',
			description:
				'Friendly name for the session that will be created when no Session ID is supplied',
			displayOptions: {
				show: {
					sessionId: [''],
				},
			},
		},
	],
};

function extractTextFromResult(result: unknown): string | undefined {
	if (result === undefined || result === null) {
		return undefined;
	}

	if (typeof result === 'string') {
		return result;
	}

	if (Array.isArray(result)) {
		return result
			.filter((entry) => typeof entry === 'string')
			.join('\n') || undefined;
	}

	if (typeof result === 'object') {
		const data = result as IDataObject;
		if (typeof data.text === 'string') {
			return data.text;
		}

		if (data.Ok !== undefined) {
			return extractTextFromResult(data.Ok);
		}

		if (data.Err !== undefined) {
			return extractTextFromResult(data.Err);
		}

		try {
			return JSON.stringify(result);
		} catch (error) {
			return undefined;
		}
	}

	return undefined;
}

export class SpaceGoose implements INodeType {
	description = nodeDescription;

	async execute(this: IExecuteFunctions): Promise<INodeExecutionData[][]> {
		const items = this.getInputData();
		const gooseClient = new GooseClient(this);
		const returnData: INodeExecutionData[] = [];
		const continueOnFail = this.continueOnFail();

		const ensureProjectReady = async (projectId: string) => {
			const { project } = await gooseClient.getProject(projectId);

			if (project.status === 'active') {
				return;
			}

			await gooseClient.activateProject(projectId);
			await gooseClient.waitForProjectReady(projectId);
		};

		for (let itemIndex = 0; itemIndex < items.length; itemIndex += 1) {
			try {
				const projectId = this.getNodeParameter('projectId', itemIndex) as string;
				const message = this.getNodeParameter('message', itemIndex) as string;
				const captureOutput = this.getNodeParameter('captureOutput', itemIndex) as boolean;
				const sessionIdInput = (this.getNodeParameter('sessionId', itemIndex, '') as string).trim();
				const sessionNameInput = (this.getNodeParameter('sessionName', itemIndex, '') as string).trim();

				if (!message) {
					throw new NodeOperationError(this.getNode(), 'Message content is required.');
				}

				await ensureProjectReady(projectId);

				let sessionId = sessionIdInput;
				let createdSession = false;

				if (!sessionId) {
					const fallbackName = sessionNameInput || `n8n ${new Date().toISOString()}`;
					const session = await gooseClient.createSession(projectId, fallbackName);
					sessionId = session.session_id;
					createdSession = true;
				} else {
					const sessions = await gooseClient.listSessions(projectId);
					const exists = sessions.some((session) => session.session_id === sessionId);
					if (!exists) {
						throw new NodeOperationError(this.getNode(), `Session ${sessionId} not found in project ${projectId}.`);
					}
				}

				const output: IDataObject = {
					projectId,
					sessionId,
					mode: captureOutput ? 'stream' : 'send',
					createdSession,
				};

				if (captureOutput) {
					const streamResult = (await gooseClient.streamMessage({
						projectId,
						sessionId,
						message,
					})) as GooseStreamResult;

					Object.assign(output, {
						responseText: streamResult.responseText,
						rawEvents: streamResult.rawEvents,
						toolEvents: streamResult.toolEvents,
					});
				} else {
					const response = await gooseClient.sendMessage({
						projectId,
						sessionId,
						message,
					});

					Object.assign(output, {
						responseText: extractTextFromResult(response.result) ?? response.message,
						rawResponse: response,
					});
				}

				returnData.push({ json: output, pairedItem: { item: itemIndex } });
			} catch (error) {
				if (continueOnFail) {
					returnData.push({
						json: { error: (error as Error).message },
						pairedItem: { item: itemIndex },
					});
					continue;
				}

				throw error;
			}
		}

		return [returnData];
	}
}
