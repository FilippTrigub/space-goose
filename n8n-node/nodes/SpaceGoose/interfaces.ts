import type { IDataObject } from 'n8n-workflow';

export interface SpaceGooseApiCredentials {
	BLACKBOX_API_KEY: string;
	baseUrl?: string;
}

export interface GooseProject {
	id: string;
	status: string;
	sessions?: GooseSession[];
	endpoint?: string;
}

export interface GooseSession {
	session_id: string;
	name?: string;
	created_at?: string;
	message_count?: number;
	[key: string]: unknown;
}

export interface GooseSessionsResponse {
	sessions: GooseSession[];
}

export interface GooseAgentStatus {
	overall_status: string;
	project_status: string;
	active_sessions?: number;
	total_processed?: number;
	uptime_seconds?: number;
	message?: string;
	[key: string]: unknown;
}

export interface GooseSendResponse {
	message: string;
	result: IDataObject | IDataObject[] | null;
	session_id: string;
	[key: string]: unknown;
}

export interface GooseStreamEvent {
	type: string;
	content?: IDataObject | IDataObject[] | string | null;
	[key: string]: unknown;
}

export interface GooseStreamResult {
	responseText: string;
	rawEvents: GooseStreamEvent[];
	toolEvents: IDataObject[];
}

export interface SendMessageOptions {
	message: string;
	projectId: string;
	sessionId: string;
	captureOutput: boolean;
}

export interface ProjectLookupResult {
	project: GooseProject;
	projects: GooseProject[];
}

