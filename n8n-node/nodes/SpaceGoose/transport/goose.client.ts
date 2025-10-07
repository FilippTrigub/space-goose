import axios, { type AxiosInstance } from 'axios';
import { createParser, type ParsedEvent, type ReconnectInterval } from 'eventsource-parser';
import type { IDataObject, IExecuteFunctions } from 'n8n-workflow';
import { NodeOperationError } from 'n8n-workflow';

import type {
	GooseAgentStatus,
	GooseProject,
	GooseSession,
	GooseSessionsResponse,
	GooseStreamEvent,
	GooseStreamResult,
	GooseSendResponse,
	SpaceGooseApiCredentials,
} from '../interfaces';

const DEFAULT_BASE_URL = 'https://api.spacegoose.ai';
const ACTIVATION_POLL_INTERVAL_MS = 5000;
const ACTIVATION_TIMEOUT_MS = 120_000;

export class GooseClient {
	private axiosInstancePromise: Promise<AxiosInstance> | undefined;

	constructor(private readonly context: IExecuteFunctions) {}

	private async getAxios(): Promise<AxiosInstance> {
		if (!this.axiosInstancePromise) {
			this.axiosInstancePromise = this.createAxiosInstance();
		}

		return this.axiosInstancePromise;
	}

	private async createAxiosInstance(): Promise<AxiosInstance> {
		const credentials = (await this.context.getCredentials('spaceGooseApi')) as
			| SpaceGooseApiCredentials
			| undefined;

		if (!credentials?.BLACKBOX_API_KEY) {
			throw new NodeOperationError(this.context.getNode(), 'Missing Space Goose credentials (BLACKBOX_API_KEY).');
		}

		const baseUrl = (credentials.baseUrl ?? DEFAULT_BASE_URL).trim();
		if (!baseUrl) {
			throw new NodeOperationError(this.context.getNode(), 'Space Goose base URL is not configured.');
		}

		return axios.create({
			baseURL: baseUrl.replace(/\/$/, ''),
			timeout: 120_000,
			headers: {
				'X-API-Key': credentials.BLACKBOX_API_KEY,
				'Content-Type': 'application/json',
				Accept: 'application/json',
			},
		});
	}

	async listProjects(): Promise<GooseProject[]> {
		const client = await this.getAxios();
		const response = await client.get<GooseProject[]>('/projects');
		return response.data;
	}

	async getProject(projectId: string): Promise<{ project: GooseProject; projects: GooseProject[] }> {
		const projects = await this.listProjects();
		const project = projects.find((entry) => entry.id === projectId);

		if (!project) {
			throw new NodeOperationError(this.context.getNode(), `Project ${projectId} not found or inaccessible.`);
		}

		return { project, projects };
	}

	async activateProject(projectId: string): Promise<void> {
		const client = await this.getAxios();
		await client.post(`/projects/${projectId}/activate`);
	}

	async waitForProjectReady(projectId: string): Promise<GooseAgentStatus> {
		const client = await this.getAxios();
		const startedAt = Date.now();

		while (Date.now() - startedAt <= ACTIVATION_TIMEOUT_MS) {
			try {
				const response = await client.get<GooseAgentStatus>(`/projects/${projectId}/agent/status`);
				const status = response.data;

				if (status.overall_status === 'error') {
					throw new NodeOperationError(
						this.context.getNode(),
						`Project ${projectId} failed to activate: ${status.message ?? 'unknown error'}`,
					);
				}

				if (status.project_status === 'active') {
					return status;
				}
			} catch (error) {
				if (axios.isAxiosError(error) && error.response) {
					const statusCode = error.response.status;
					if (statusCode >= 500) {
						throw new NodeOperationError(
							this.context.getNode(),
							`Space Goose API responded with ${statusCode} while waiting for activation.`,
						);
					}
					// For 404/409 while the project is still coming online just continue polling.
				} else {
					throw error;
				}
			}

			await this.sleep(ACTIVATION_POLL_INTERVAL_MS);
		}

		throw new NodeOperationError(
			this.context.getNode(),
			`Timed out after ${ACTIVATION_TIMEOUT_MS / 1000}s while waiting for project ${projectId} to become ready.`,
		);
	}

	async listSessions(projectId: string): Promise<GooseSession[]> {
		const client = await this.getAxios();
		const response = await client.get<GooseSessionsResponse>(`/projects/${projectId}/sessions`);
		return response.data.sessions ?? [];
	}

	async createSession(projectId: string, sessionName?: string): Promise<GooseSession> {
		const client = await this.getAxios();
		const payload: Record<string, string> = sessionName ? { name: sessionName } : {};
		const response = await client.post(`/projects/${projectId}/sessions`, payload);
		const session = response.data.session as GooseSession | undefined;
		if (!session?.session_id) {
			throw new NodeOperationError(this.context.getNode(), 'The API did not return a session identifier.');
		}

		return session;
	}

	async sendMessage(options: { projectId: string; sessionId: string; message: string }): Promise<GooseSendResponse> {
		const client = await this.getAxios();
		const response = await client.post<GooseSendResponse>(
			`/projects/${options.projectId}/messages/send`,
			{
				content: options.message,
				session_id: options.sessionId,
			},
		);
		return response.data;
	}

	async streamMessage(options: {
		projectId: string;
		sessionId: string;
		message: string;
	}): Promise<GooseStreamResult> {
		const client = await this.getAxios();
		const response = await client.post<NodeJS.ReadableStream>(
			`/projects/${options.projectId}/messages`,
			{
				content: options.message,
				session_id: options.sessionId,
			},
			{
				responseType: 'stream',
				headers: { Accept: 'text/event-stream' },
				validateStatus: () => true,
			},
		);

		if (response.status !== 200 || !response.data) {
			const error = await this.extractError(response);
			throw new NodeOperationError(
				this.context.getNode(),
				`Streaming request failed (${response.status}). ${error}`,
			);
		}

		return this.consumeStream(response.data);
	}

	private async extractError(response: { status: number; data?: unknown }): Promise<string> {
		const data = response.data;

		if (!data) {
			return 'No additional error details provided.';
		}

		if (typeof (data as NodeJS.ReadableStream).on === 'function') {
			const stream = data as NodeJS.ReadableStream;
			const chunks: Buffer[] = [];

			return await new Promise<string>((resolve) => {
				stream.on('data', (chunk) => chunks.push(Buffer.from(chunk)));
				stream.once('end', () => {
					resolve(Buffer.concat(chunks).toString() || '');
				});
				stream.once('error', () => {
					resolve('Failed to read error stream.');
				});
			});
		}

		if (typeof data === 'object') {
			try {
				return JSON.stringify(data);
			} catch (error) {
				return 'Failed to serialize error payload.';
			}
		}

		return String(data);
	}

	private consumeStream(stream: NodeJS.ReadableStream): Promise<GooseStreamResult> {
		return new Promise((resolve, reject) => {
			let responseText = '';
			const rawEvents: GooseStreamEvent[] = [];
			const toolEvents: IDataObject[] = [];

			const parser = createParser((event: ParsedEvent | ReconnectInterval) => {
				if (event.type !== 'event' || event.data === undefined) {
					return;
				}

				let payload: GooseStreamEvent;
				try {
					payload = JSON.parse(event.data) as GooseStreamEvent;
				} catch (error) {
					rawEvents.push({ type: 'unparsed', content: event.data });
					return;
				}

				rawEvents.push(payload);

				if (payload.type === 'message' && payload.content && typeof payload.content === 'object' && !Array.isArray(payload.content)) {
					const content = payload.content as IDataObject;
					const textChunk = content.content;
					if (typeof textChunk === 'string') {
						responseText += textChunk;
					}
				} else if (payload.type?.startsWith('tool_') && payload.content && typeof payload.content === 'object' && !Array.isArray(payload.content)) {
					toolEvents.push(payload.content as IDataObject);
				}
			});

			stream.on('data', (chunk) => {
				parser.feed(chunk.toString());
			});

			stream.once('end', () => {
				resolve({ responseText: responseText.trim(), rawEvents, toolEvents });
			});

			stream.once('error', (error) => {
				reject(error);
			});
		});
	}

	private async sleep(durationMs: number): Promise<void> {
		await new Promise((resolve) => setTimeout(resolve, durationMs));
	}
}
