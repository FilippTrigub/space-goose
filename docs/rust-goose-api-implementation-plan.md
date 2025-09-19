# Rust Goose API Implementation Plan

## Executive Summary

This document outlines a comprehensive plan to **extend the existing Goose CLI** with REST API capabilities by adding a new web server mode. Rather than building a standalone API service, we will enhance the Goose CLI application to include an API server command that provides session management with PostgreSQL persistence and real-time streaming responses using Server-Sent Events (SSE). 

The implementation follows the existing Goose architecture patterns found in `goose-bbai` and extends the current `goose web` command to provide full REST API functionality alongside the existing WebSocket-based interface.

**Key Features:**
- **Extended Goose CLI** with new `goose api-server` command
- Session management with PostgreSQL persistence (hybrid with existing .jsonl files)
- Real-time streaming responses via SSE using existing `AgentEvent` system
- Direct integration with Goose's agent system (no subprocess execution)
- Full compatibility with existing Goose CLI commands and session management
- High-performance async architecture leveraging existing Axum infrastructure

**Architecture Approach:**
Instead of creating a separate API service, we extend the existing Goose CLI with a new web server mode that:
1. Reuses the existing Axum infrastructure from `commands/web.rs`
2. Integrates directly with Goose's agent system and session management
3. Adds REST endpoints alongside the existing WebSocket interface
4. Provides hybrid PostgreSQL storage while maintaining .jsonl compatibility

---

## 1. Technology Research & Recommendations

### 1.1 Database SDKs for Rust

Based on research, the top PostgreSQL and MongoDB options are:

#### PostgreSQL Options:
1. **SQLx** (Recommended)
   - Async, pure Rust SQL crate with compile-time checked queries
   - No DSL - uses raw SQL for transparency
   - Excellent connection pooling
   - Built-in migration support
   - Active community and maintenance

2. **Diesel** (Alternative)
   - Mature ORM with strong type safety
   - Code generation from schema
   - More opinionated but feature-rich

3. **tokio-postgres** (Low-level)
   - Direct PostgreSQL client
   - More manual but maximum control

#### MongoDB Options:
1. **mongodb** crate (Official)
   - Officially supported MongoDB Rust driver
   - Full async API with tokio support
   - Built-in BSON support
   - Comprehensive feature set

**Recommendation:** SQLx for PostgreSQL due to its balance of performance, safety, and ease of use.

### 1.2 Streaming Response Capabilities

Rust web frameworks provide excellent support for Server-Sent Events (SSE) with `text/event-stream`:

#### Web Framework Comparison:
1. **Axum** (Recommended)
   - Built on tokio/hyper stack
   - Native SSE support via `axum::response::sse`
   - Excellent performance and ergonomics
   - Part of the tokio ecosystem

2. **Actix Web** (High Performance Alternative)
   - Slightly better raw performance
   - SSE support via `actix-web-lab::sse`
   - More complex but very mature

3. **Warp** (Functional Alternative)
   - Filter-based architecture
   - Good SSE support but less ergonomic

**Recommendation:** Axum for its balance of performance, ergonomics, and ecosystem integration.

---

## 2. CLI Extension Strategy: Converting to Web API Server

### 2.1 Analysis of Existing `goose web` Command

After analyzing `crates/goose-cli/src/commands/web.rs`, we discovered that Goose already has web server capabilities:

#### Current Web Interface Features:
- **Axum-based web server** with WebSocket support
- **Agent integration** - Direct use of `Agent` struct and `agent.reply()` streaming
- **Session management** - Integration with existing `.jsonl` session files
- **Real-time communication** via WebSockets
- **CORS support** for web client access
- **Static file serving** for HTML/CSS/JS assets

#### Key Infrastructure Already Present:
```rust
// From commands/web.rs - shows existing patterns to extend:

#[derive(Clone)]
struct AppState {
    agent: Arc<Agent>,                    // Direct agent integration
    sessions: SessionStore,               // In-memory session cache
    cancellations: CancellationStore,     // Task cancellation support
}

// Existing streaming implementation:
async fn process_message_streaming(
    agent: &Agent,
    session_messages: Arc<Mutex<Conversation>>,
    session_file: std::path::PathBuf,
    content: String,
    sender: Arc<Mutex<futures::stream::SplitSink<WebSocket, Message>>>,
) -> Result<()> {
    // Uses agent.reply() which returns AgentEvent stream
    match agent.reply(messages.clone(), Some(session_config), None).await {
        Ok(mut stream) => {
            while let Some(result) = stream.next().await {
                match result {
                    Ok(AgentEvent::Message(message)) => {
                        // Handle message streaming
                    }
                    Ok(AgentEvent::McpNotification(_)) => {
                        // Handle tool notifications  
                    }
                    Ok(AgentEvent::HistoryReplaced(new_messages)) => {
                        // Handle context compaction
                    }
                    // ... other events
                }
            }
        }
    }
}
```

### 2.2 Enhanced CLI Command Structure

Extend the existing CLI with a new API server mode:

```rust
// Enhanced CLI structure in cli.rs:
#[derive(Subcommand)]
enum Command {
    // ... existing commands ...
    
    /// Start REST API server with optional web interface
    #[command(about = "Start REST API server with optional web interface")]
    ApiServer {
        /// Port to run the API server on
        #[arg(short, long, default_value = "3000")]
        port: u16,

        /// Host to bind the server to
        #[arg(long, default_value = "127.0.0.1")]
        host: String,

        /// Enable web interface alongside API
        #[arg(long, help = "Enable web interface alongside REST API")]
        with_web: bool,

        /// Database URL for PostgreSQL
        #[arg(long, env = "DATABASE_URL")]
        database_url: Option<String>,

        /// Enable hybrid session storage (PostgreSQL + .jsonl)
        #[arg(long, help = "Enable hybrid session storage")]
        hybrid_storage: bool,

        /// API prefix path
        #[arg(long, default_value = "/api/v1")]
        api_prefix: String,
    },
}
```

### 2.3 Enhanced System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Client App    │───▶│   Goose CLI      │───▶│   PostgreSQL    │
│   (HTTP/SSE)    │◀───│   (api-server)   │◀───│   Database      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                        ┌──────────────────┐
                        │   Agent System   │
                        │   (.jsonl files) │
                        └──────────────────┘
```

---

## 3. Implementation Plan

### 3.1 Extended Project Structure

Building upon the existing `goose-cli` crate structure:

```
crates/goose-cli/src/
├── commands/
│   ├── web.rs (existing - to be enhanced)
│   ├── api_server.rs (new)
│   └── mod.rs
├── api/
│   ├── mod.rs
│   ├── handlers/
│   │   ├── mod.rs
│   │   ├── sessions.rs
│   │   └── streaming.rs
│   ├── models/
│   │   ├── mod.rs
│   │   ├── api_session.rs
│   │   └── api_message.rs
│   ├── services/
│   │   ├── mod.rs
│   │   ├── hybrid_session_manager.rs
│   │   └── streaming_service.rs
│   └── database/
│       ├── mod.rs
│       └── schema.sql
└── cli.rs (enhanced)
```

### 3.2 Key Dependencies (Addition to existing Cargo.toml)

```toml
[dependencies]
# Database (add to existing dependencies)
sqlx = { version = "0.8", features = ["runtime-tokio-rustls", "postgres", "uuid", "chrono", "json"], optional = true }

# Async streaming (add to existing)
async-stream = "0.3"
tokio-util = "0.7"

# Features
[features]
default = []
api-server = ["sqlx"]  # Optional feature for API server mode
```

### 3.3 Core Implementation Components

#### 3.3.1 Enhanced Web Command (api_server.rs)

```rust
use anyhow::Result;
use axum::{
    extract::State,
    response::sse::{Event, KeepAlive, Sse},
    routing::{get, post, delete},
    Json, Router,
};
use futures::Stream;
use std::{net::SocketAddr, sync::Arc};
use tower_http::cors::{Any, CorsLayer};

#[cfg(feature = "api-server")]
use sqlx::PgPool;

use crate::api::services::hybrid_session_manager::HybridSessionManager;
use crate::api::handlers::{sessions, streaming};

pub async fn handle_api_server(
    port: u16,
    host: String,
    with_web: bool,
    database_url: Option<String>,
    hybrid_storage: bool,
    api_prefix: String,
) -> Result<()> {
    // Setup logging
    crate::logging::setup_logging(Some("goose-api"), None)?;

    // Load config and create agent (reuse from web.rs)
    let agent = create_configured_agent().await?;

    // Setup database if enabled
    let db_pool = if let Some(url) = database_url {
        #[cfg(feature = "api-server")]
        {
            Some(create_database_pool(&url).await?)
        }
        #[cfg(not(feature = "api-server"))]
        {
            return Err(anyhow::anyhow!("API server feature not enabled. Compile with --features api-server"));
        }
    } else {
        None
    };

    // Create enhanced app state
    let state = create_api_app_state(agent, db_pool, hybrid_storage).await?;

    // Build router with both REST API and optionally web interface
    let mut app = Router::new();

    // Add REST API routes
    app = app.nest(&api_prefix, create_api_routes(state.clone()));

    // Add web interface if enabled
    if with_web {
        app = app.merge(create_web_routes(state.clone()));
    }

    // Add middleware
    app = app.layer(
        CorsLayer::new()
            .allow_origin(Any)
            .allow_methods(Any)
            .allow_headers(Any),
    );

    let addr: SocketAddr = format!("{}:{}", host, port).parse()?;

    println!("\n🪿 Starting Goose API server");
    if hybrid_storage {
        println!("   Storage: Hybrid (PostgreSQL + .jsonl)");
    } else {
        println!("   Storage: .jsonl files only");
    }
    println!("   API: http://{}{}", addr, api_prefix);
    if with_web {
        println!("   Web: http://{}", addr);
    }
    println!("   Press Ctrl+C to stop\n");

    let listener = tokio::net::TcpListener::bind(addr).await?;
    axum::serve(listener, app).await?;

    Ok(())
}

fn create_api_routes(state: Arc<ApiAppState>) -> Router {
    Router::new()
        // Session management
        .route("/sessions", post(sessions::create_session))
        .route("/sessions", get(sessions::list_sessions))
        .route("/sessions/:id", get(sessions::get_session))
        .route("/sessions/:id", delete(sessions::delete_session))
        
        // Streaming chat
        .route("/sessions/:id/messages", post(streaming::send_message_stream))
        
        // Health and status
        .route("/health", get(health_check))
        .route("/status", get(server_status))
        
        .with_state(state)
}
```

#### 3.3.2 Hybrid Session Manager

```rust
use sqlx::PgPool;
use goose::session::{SessionMetadata, Identifier};
use goose::conversation::{Conversation, message::Message};

pub struct HybridSessionManager {
    pool: Option<PgPool>,
    use_database: bool,
}

impl HybridSessionManager {
    pub fn new(pool: Option<PgPool>) -> Self {
        Self {
            use_database: pool.is_some(),
            pool,
        }
    }

    /// Create session with hybrid storage
    pub async fn create_session(
        &self,
        working_dir: PathBuf,
        name: Option<String>,
    ) -> Result<(String, Option<Uuid>), anyhow::Error> {
        let goose_session_id = goose::session::generate_session_id();
        
        // Always create .jsonl session (for CLI compatibility)
        let session_path = goose::session::get_path(
            Identifier::Name(goose_session_id.clone())
        )?;
        
        let metadata = SessionMetadata::new(working_dir.clone());
        let empty_conversation = Conversation::empty();
        goose::session::storage::save_messages_with_metadata(
            &session_path,
            &metadata,
            &empty_conversation,
        )?;

        // Additionally store in PostgreSQL if enabled
        let uuid = if self.use_database {
            if let Some(pool) = &self.pool {
                let display_name = name.unwrap_or_else(|| {
                    format!("API Session {}", &goose_session_id[9..])
                });
                
                let row = sqlx::query!(
                    r#"
                    INSERT INTO sessions (goose_session_id, name, working_dir, description)
                    VALUES ($1, $2, $3, $4)
                    RETURNING id
                    "#,
                    goose_session_id,
                    display_name,
                    working_dir.to_string_lossy().to_string(),
                    "API created session"
                )
                .fetch_one(pool)
                .await?;
                
                Some(row.id)
            } else {
                None
            }
        } else {
            None
        };

        Ok((goose_session_id, uuid))
    }

    /// Load conversation using hybrid approach
    pub async fn load_conversation(
        &self, 
        goose_session_id: &str
    ) -> Result<Conversation, anyhow::Error> {
        // Primary: Load from .jsonl file (always authoritative)
        let session_path = goose::session::get_path(
            Identifier::Name(goose_session_id.to_string())
        )?;
        
        if session_path.exists() {
            return Ok(goose::session::read_messages(&session_path)?);
        }

        // Fallback: Load from PostgreSQL if available
        if self.use_database {
            if let Some(pool) = &self.pool {
                return self.load_from_database(goose_session_id, pool).await;
            }
        }

        // Default: Empty conversation
        Ok(Conversation::empty())
    }

    async fn load_from_database(
        &self,
        goose_session_id: &str,
        pool: &PgPool,
    ) -> Result<Conversation, anyhow::Error> {
        let messages = sqlx::query!(
            r#"
            SELECT role, content, message_index
            FROM session_messages
            WHERE goose_session_id = $1
            ORDER BY message_index ASC
            "#,
            goose_session_id
        )
        .fetch_all(pool)
        .await?;

        let mut conversation_messages = Vec::new();
        for row in messages {
            let role = match row.role.as_str() {
                "user" => rmcp::model::Role::User,
                "assistant" => rmcp::model::Role::Assistant,
                _ => continue,
            };

            let content: Vec<goose::conversation::message::MessageContent> = 
                serde_json::from_value(row.content)?;

            let message = Message { role, content };
            conversation_messages.push(message);
        }

        Ok(Conversation::new_unvalidated(conversation_messages))
    }
}
```

#### 3.3.3 Enhanced Streaming Service

```rust
use futures::Stream;
use tokio_stream::StreamExt;
use goose::agents::{Agent, AgentEvent, SessionConfig};
use goose::conversation::{Conversation, message::Message};

pub struct ApiStreamingService {
    session_manager: HybridSessionManager,
}

impl ApiStreamingService {
    pub fn new(session_manager: HybridSessionManager) -> Self {
        Self { session_manager }
    }

    /// Execute Goose command with SSE streaming (reuses existing agent.reply)
    pub async fn execute_streaming(
        &self,
        agent: &Agent,
        goose_session_id: &str,
        user_message: &str,
    ) -> Result<impl Stream<Item = Result<SseEvent, anyhow::Error>>, anyhow::Error> {
        // Load existing conversation
        let mut conversation = self.session_manager
            .load_conversation(goose_session_id)
            .await?;
        
        // Add user message
        let user_msg = Message::user().with_text(user_message);
        conversation.push(user_msg.clone());

        // Get session path for .jsonl persistence
        let session_path = goose::session::get_path(
            goose::session::Identifier::Name(goose_session_id.to_string())
        )?;

        // Save user message immediately (to .jsonl file)
        let provider = agent.provider().await?;
        let working_dir = Some(std::env::current_dir()?);
        goose::session::persist_messages(
            &session_path,
            &conversation,
            Some(provider.clone()),
            working_dir.clone(),
        ).await?;

        // Create session config (reuse from existing web.rs patterns)
        let session_config = SessionConfig {
            id: goose::session::Identifier::Name(goose_session_id.to_string()),
            working_dir: working_dir.unwrap_or_default(),
            schedule_id: None,
            execution_mode: None,
            max_turns: None,
            retry_config: None,
        };

        // Create the stream using existing agent.reply method
        let mut agent_stream = agent
            .reply(conversation.clone(), Some(session_config), None)
            .await?;

        let session_path_clone = session_path.clone();
        let working_dir_clone = working_dir;

        let event_stream = async_stream::try_stream! {
            let mut current_conversation = conversation;
            
            while let Some(result) = agent_stream.next().await {
                match result {
                    Ok(AgentEvent::Message(message)) => {
                        // Update conversation and persist to .jsonl
                        current_conversation.push(message.clone());
                        
                        // Persist to .jsonl file (authoritative storage)
                        let _ = goose::session::persist_messages(
                            &session_path_clone,
                            &current_conversation,
                            None, // No provider needed for assistant messages
                            working_dir_clone.clone(),
                        ).await;

                        // Yield SSE event for user-visible messages
                        if message.is_user_visible() {
                            yield SseEvent {
                                event_type: "message".to_string(),
                                data: serde_json::to_string(&MessageEvent {
                                    role: "assistant".to_string(),
                                    content: message.as_concat_text(),
                                    timestamp: chrono::Utc::now(),
                                })?,
                                id: Some(uuid::Uuid::new_v4().to_string()),
                            };
                        }
                    }
                    Ok(AgentEvent::McpNotification((req_id, notification))) => {
                        yield SseEvent {
                            event_type: "notification".to_string(),
                            data: serde_json::to_string(&NotificationEvent {
                                request_id: req_id,
                                message: notification,
                            })?,
                            id: Some(uuid::Uuid::new_v4().to_string()),
                        };
                    }
                    Ok(AgentEvent::HistoryReplaced(new_messages)) => {
                        // Handle context compaction
                        current_conversation = Conversation::new_unvalidated(new_messages);
                        
                        // Persist compacted conversation
                        let _ = goose::session::persist_messages(
                            &session_path_clone,
                            &current_conversation,
                            None,
                            working_dir_clone.clone(),
                        ).await;
                        
                        yield SseEvent {
                            event_type: "context_compacted".to_string(),
                            data: serde_json::to_string(&ContextEvent {
                                message: "Context has been compacted to stay within limits".to_string(),
                                new_message_count: current_conversation.len(),
                            })?,
                            id: Some(uuid::Uuid::new_v4().to_string()),
                        };
                    }
                    Ok(AgentEvent::ModelChange { model, mode }) => {
                        yield SseEvent {
                            event_type: "model_change".to_string(),
                            data: serde_json::to_string(&ModelChangeEvent { model, mode })?,
                            id: Some(uuid::Uuid::new_v4().to_string()),
                        };
                    }
                    Err(e) => {
                        yield SseEvent {
                            event_type: "error".to_string(),
                            data: serde_json::to_string(&ErrorEvent {
                                error: e.to_string(),
                                recoverable: false,
                            })?,
                            id: Some(uuid::Uuid::new_v4().to_string()),
                        };
                        break;
                    }
                }
            }

            // Final completion event
            yield SseEvent {
                event_type: "complete".to_string(),
                data: serde_json::to_string(&CompleteEvent {
                    final_message_count: current_conversation.len(),
                    session_id: goose_session_id.to_string(),
                })?,
                id: Some(uuid::Uuid::new_v4().to_string()),
            };
        };

        Ok(event_stream)
    }
}
```

#### 3.3.4 REST API Handlers

```rust
// sessions.rs
use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    Json,
};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

#[derive(Deserialize)]
pub struct CreateSessionRequest {
    pub name: String,
    pub description: Option<String>,
    pub working_dir: Option<String>,
}

#[derive(Serialize)]
pub struct CreateSessionResponse {
    pub id: Option<Uuid>,  // PostgreSQL UUID (if hybrid storage enabled)
    pub session_id: String, // Goose session ID (always present)
    pub name: String,
    pub working_dir: String,
}

pub async fn create_session(
    State(state): State<Arc<ApiAppState>>,
    Json(request): Json<CreateSessionRequest>,
) -> Result<Json<CreateSessionResponse>, StatusCode> {
    let working_dir = request.working_dir
        .map(PathBuf::from)
        .unwrap_or_else(|| std::env::current_dir().unwrap_or_default());

    let (goose_session_id, uuid) = state.session_manager
        .create_session(working_dir.clone(), Some(request.name.clone()))
        .await
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    Ok(Json(CreateSessionResponse {
        id: uuid,
        session_id: goose_session_id,
        name: request.name,
        working_dir: working_dir.to_string_lossy().to_string(),
    }))
}

pub async fn list_sessions(
    State(state): State<Arc<ApiAppState>>,
) -> Result<Json<Vec<SessionInfo>>, StatusCode> {
    // Use existing Goose session listing (from .jsonl files)
    let sessions = goose::session::list_sessions()
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    let session_info: Vec<SessionInfo> = sessions
        .into_iter()
        .filter_map(|(name, path)| {
            goose::session::read_metadata(&path).ok().map(|metadata| {
                SessionInfo {
                    session_id: name,
                    name: metadata.description,
                    working_dir: metadata.working_dir.to_string_lossy().to_string(),
                    message_count: metadata.message_count,
                    created_at: None, // Could be enhanced with file creation time
                }
            })
        })
        .collect();

    Ok(Json(session_info))
}
```

#### 3.3.5 SSE Streaming Handler

```rust
// streaming.rs
use axum::{
    extract::{Path, State},
    response::sse::{Event, Sse},
    Json,
};
use futures::Stream;
use std::convert::Infallible;
use tokio_stream::StreamExt;

#[derive(Deserialize)]
pub struct SendMessageRequest {
    pub message: String,
}

pub async fn send_message_stream(
    Path(session_id): Path<String>, // Use Goose session ID as path param
    State(state): State<Arc<ApiAppState>>,
    Json(request): Json<SendMessageRequest>,
) -> Result<Sse<impl Stream<Item = Result<Event, Infallible>>>, StatusCode> {
    // Create the streaming response using existing agent integration
    let event_stream = state.streaming_service
        .execute_streaming(&state.agent, &session_id, &request.message)
        .await
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    let sse_stream = event_stream.map(|result| {
        match result {
            Ok(event) => Ok(Event::default()
                .event(&event.event_type)
                .data(&event.data)
                .id(&event.id.unwrap_or_default())),
            Err(e) => Ok(Event::default()
                .event("error")
                .data(format!("{{\"error\": \"{}\"}}", e))),
        }
    });

    Ok(Sse::new(sse_stream).keep_alive(KeepAlive::default()))
}
```

---

## 4. Development Phases

### Phase 1: CLI Extension Foundation (Week 1)
- [ ] Add new `api-server` command to CLI enum in `cli.rs`
- [ ] Create `commands/api_server.rs` extending existing `web.rs` patterns
- [ ] Setup optional PostgreSQL dependencies with feature flag
- [ ] Basic REST API router setup reusing Axum infrastructure

### Phase 2: Hybrid Session Management (Week 2) 
- [ ] Implement `HybridSessionManager` for dual storage (.jsonl + PostgreSQL)
- [ ] Enhanced database schema with Goose-compatible fields
- [ ] Session CRUD operations with `goose_session_id` mapping
- [ ] Maintain full compatibility with existing `goose session` commands

### Phase 3: Agent-Direct Streaming Integration (Week 3)
- [ ] Implement `ApiStreamingService` using existing `agent.reply()` streams
- [ ] Convert `AgentEvent` streams to SSE format
- [ ] Handle context compaction, model changes, and tool notifications
- [ ] Real-time message persistence to both storage systems

### Phase 4: Production Features (Week 4)
- [ ] Authentication and authorization middleware
- [ ] Request validation and error handling
- [ ] API documentation with OpenAPI/Swagger
- [ ] Performance optimization and connection pooling

### Phase 5: Enhanced Integration (Week 5)
- [ ] CLI command integration (sessions created via API visible in `goose session list`)
- [ ] Export functionality for API-created sessions
- [ ] Advanced Goose features (recipes, extensions) via API
- [ ] Metrics and monitoring endpoints

---

## 5. Key Advantages of CLI Extension Approach

### 5.1 Leveraging Existing Infrastructure
- **Reuse proven patterns** from `commands/web.rs`
- **Direct agent integration** - no subprocess overhead
- **Existing session compatibility** - API sessions work with `goose session` commands
- **Built-in configuration** - uses existing `goose configure` setup

### 5.2 Architecture Benefits
- **Single binary deployment** - no separate API service needed
- **Consistent behavior** - same agent, provider, and extension system
- **Simplified debugging** - unified logging and error handling
- **Native performance** - no IPC or network overhead between CLI and API

### 5.3 Development Efficiency
- **Familiar codebase** - extends existing Goose patterns
- **Incremental enhancement** - builds on working foundation
- **Shared dependencies** - leverages existing Cargo.toml setup
- **Unified testing** - can test API and CLI together

---

## 6. Enhanced System Architecture

### 6.1 Extended CLI Command Structure

```
goose
├── session [existing]
├── run [existing]  
├── web [existing] - WebSocket-based interface
└── api-server [new] - REST API + optional web interface
    ├── --port 3000
    ├── --database-url postgres://...
    ├── --hybrid-storage  
    └── --with-web
```

### 6.2 Hybrid Storage Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   CLI Commands  │───▶│   .jsonl files   │───▶│   File System   │
│   (session,run) │◀───│   (authoritative)│◀───│   ~/.local/...  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   API Clients   │───▶│   REST API       │───▶│   PostgreSQL    │
│   (HTTP/SSE)    │◀───│   (enhanced)     │◀───│   (optional)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                        ┌──────────────────┐
                        │   Agent System   │
                        │   (shared)       │
                        └──────────────────┘
```

### 6.3 API Endpoint Design

```
GET    /api/v1/health              - Health check
GET    /api/v1/status              - Server status and configuration
GET    /api/v1/sessions            - List all sessions
POST   /api/v1/sessions            - Create new session
GET    /api/v1/sessions/{id}       - Get session details and history
DELETE /api/v1/sessions/{id}       - Delete session
POST   /api/v1/sessions/{id}/messages - Send message with SSE streaming response
GET    /api/v1/sessions/{id}/export   - Export session as markdown
```

---

## 7. Implementation Benefits

### 7.1 Full Goose Ecosystem Integration
- **CLI Compatibility** - Sessions created via API are visible in `goose session list`
- **Shared Configuration** - Uses same provider/model settings from `goose configure`
- **Extension Support** - API inherits all enabled extensions from CLI configuration
- **Recipe Support** - Can execute recipes via API endpoints

### 7.2 Real-time Capabilities
- **Server-Sent Events** - Live streaming of agent responses using existing `AgentEvent` system
- **Tool Notifications** - Real-time updates on tool execution and MCP notifications
- **Context Management** - Live updates on context compaction and model changes
- **Cancellation Support** - Ability to cancel long-running operations

### 7.3 Production Readiness
- **Hybrid Storage** - Reliability of PostgreSQL with CLI compatibility of .jsonl files
- **Scalable Architecture** - Built on proven Axum/Tokio foundation
- **Security** - Inherits Goose's existing security patterns and validation
- **Monitoring** - Unified logging and metrics with existing Goose telemetry

This enhanced approach transforms the plan from building a separate API service to extending the existing Goose CLI with API capabilities, providing a more integrated and maintainable solution that leverages the full power of the existing Goose infrastructure.
