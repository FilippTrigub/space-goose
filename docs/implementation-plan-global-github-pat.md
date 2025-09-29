# Implementation Plan: Global GitHub PAT Management

## Overview
This plan outlines implementing a global GitHub Personal Access Token (PAT) management system that allows users to set a default GitHub token at the user level, which is automatically applied to all projects unless overridden.

## Current State Analysis

### Current GitHub Token Handling
- **Project-level only**: GitHub tokens are set per-project
- **Manual entry required**: Users must enter GitHub token for each project
- **Storage**: Tokens stored in K8s secrets per project
- **UI Flow**: Token entry in project creation and update modals
- **Database**: Project-level `github_key_set` boolean flag

### Current Routes
- `PUT /users/{user_id}/projects/{project_id}/github-key` - Update project GitHub key
- Project creation includes optional GitHub key

### Current Database Schema (MongoDB)
```javascript
// Projects collection
{
  "_id": ObjectId,
  "user_id": "string",
  "name": "string", 
  "status": "active|inactive",
  "github_key_set": boolean,
  "sessions": [],
  "created_at": Date,
  "updated_at": Date
}
```

## Task 2: Global GitHub PAT Management

### Requirements

#### User Experience
1. **Global GitHub Token Setting**: Users can set a default GitHub token in their user profile
2. **Automatic Application**: New projects automatically use the user's default GitHub token
3. **Project Override**: Individual projects can still override the global token
4. **Clear Indication**: UI shows whether project uses global or project-specific token
5. **Token Management**: Users can update/remove their global GitHub token

#### Technical Requirements
1. **User-level Storage**: Store encrypted GitHub tokens per user
2. **Automatic Inheritance**: Apply global token to new projects by default
3. **Priority System**: Project-specific token overrides global token
4. **Security**: Maintain existing security practices for token storage
5. **Backward Compatibility**: Existing projects continue working unchanged

### Database Schema Changes

#### New Users Collection (MongoDB)
```javascript
// users collection (new)
{
  "_id": ObjectId,
  "user_id": "string",     // matches existing user IDs
  "name": "string",        // user display name
  "github_token_set": boolean,
  "created_at": Date,
  "updated_at": Date
}
```

#### Projects Collection Updates
```javascript
// projects collection (updated)
{
  "_id": ObjectId,
  "user_id": "string",
  "name": "string",
  "status": "active|inactive", 
  "github_key_set": boolean,
  "github_key_source": "global|project",  // NEW: indicates token source
  "sessions": [],
  "created_at": Date,
  "updated_at": Date
}
```

### API Changes

#### New User GitHub Token Routes
```python
# New routes to add
PUT /users/{user_id}/github-key           # Set/update global GitHub token
GET /users/{user_id}/github-key           # Get global GitHub token status  
DELETE /users/{user_id}/github-key        # Remove global GitHub token
```

#### Modified Project Routes
```python
# Updated behavior for existing routes
POST /users/{user_id}/projects            # Auto-apply global token if available
PUT /users/{user_id}/projects/{project_id}/github-key  # Add option to use global token
```

### Service Layer Changes

#### New `UserService` Methods
```python
class UserService:
    def set_global_github_token(self, user_id: str, token: str) -> bool
    def get_global_github_token(self, user_id: str) -> Optional[str] 
    def remove_global_github_token(self, user_id: str) -> bool
    def has_global_github_token(self, user_id: str) -> bool
```

#### Updated `ProjectService` Methods  
```python
class ProjectService:
    def create_project_with_token_inheritance(self, user_id: str, project_data: dict) -> str
    def get_effective_github_token(self, user_id: str, project_id: str) -> Optional[str]
    def update_project_github_token_with_global_option(self, user_id: str, project_id: str, token: Optional[str], use_global: bool = False) -> bool
```

### Kubernetes Integration

#### Token Storage Strategy
1. **Global Tokens**: Store in user-specific K8s secrets (`user-{user_id}-global-secrets`)
2. **Project Tokens**: Continue using existing project-specific secrets
3. **Token Resolution**: During deployment, resolve effective token (project > global > none)

#### Secret Management
```yaml
# User-level global secret
apiVersion: v1
kind: Secret
metadata:
  name: user-{user_id}-global-secrets
  namespace: space-goose
data:
  github-token: <base64-encoded-token>
```

### UI/UX Changes

#### User Settings Panel (New)
```html
<!-- New global settings section -->
<div class="user-settings-panel">
  <h3>🔑 Global GitHub Token</h3>
  <div class="github-token-global">
    <input type="password" placeholder="ghp_xxxxxxxxxxxxxxxxxxxx">
    <button class="btn btn-primary">Set Global Token</button>
    <button class="btn btn-outline">Remove Global Token</button>
  </div>
  <small class="form-help">
    This token will be applied to all new projects by default.
    Individual projects can override this setting.
  </small>
</div>
```

#### Updated Project Creation Modal
```html
<!-- Enhanced project creation -->
<div class="form-group">
  <label for="github-key-input">GitHub Token</label>
  <select id="github-token-source">
    <option value="global">Use Global Token (recommended)</option>
    <option value="project">Set Project-Specific Token</option>
    <option value="none">No GitHub Token</option>
  </select>
  <input type="password" id="project-github-key" style="display:none;">
  <small class="form-help">
    <span id="global-token-status">✅ Global token available</span>
  </small>
</div>
```

#### Updated Project Cards
```html
<!-- Enhanced GitHub status display -->
<div class="github-token-status">
  <span class="token-indicator global">🌐 Global Token</span>
  <!-- OR -->
  <span class="token-indicator project">🔑 Project Token</span>
  <!-- OR -->
  <span class="token-indicator none">🚫 No Token</span>
</div>
```

## Implementation Steps

### Phase 1: Database & Service Layer (Backend)
1. **Create Users Collection**: Set up MongoDB users collection schema
2. **Update Models**: Add new Pydantic models for user GitHub token management
3. **Implement UserService**: Create service methods for global token management
4. **Update ProjectService**: Modify to handle token inheritance
5. **Add New Routes**: Implement user GitHub token API endpoints

### Phase 2: Kubernetes Integration
1. **User Secret Management**: Implement global secret creation/update
2. **Token Resolution Logic**: Update deployment logic to resolve effective tokens
3. **Migration Strategy**: Handle existing projects gracefully

### Phase 3: Frontend Integration
1. **User Settings UI**: Add global GitHub token management interface
2. **Project Creation Flow**: Update project creation to use global tokens
3. **Project Management**: Update project GitHub token management
4. **Visual Indicators**: Add clear indicators for token sources

### Phase 4: Migration & Testing  
1. **Data Migration**: Migrate existing users to new schema
2. **Backward Compatibility**: Ensure existing projects work unchanged
3. **Testing**: Comprehensive testing of token inheritance logic
4. **Documentation**: Update API documentation

## New API Endpoints

### User GitHub Token Management

#### Set Global GitHub Token
```http
PUT /users/{user_id}/github-key
Content-Type: application/json

{
  "github_token": "ghp_xxxxxxxxxxxxxxxxxxxx"
}

Response: 200 OK
{
  "message": "Global GitHub token set successfully"
}
```

#### Get Global GitHub Token Status
```http
GET /users/{user_id}/github-key

Response: 200 OK
{
  "has_global_token": true,
  "created_at": "2023-12-07T10:30:00Z",
  "updated_at": "2023-12-07T10:30:00Z"
}
```

#### Remove Global GitHub Token
```http
DELETE /users/{user_id}/github-key

Response: 200 OK
{
  "message": "Global GitHub token removed successfully"
}
```

### Updated Project Endpoints

#### Create Project with Token Inheritance
```http
POST /users/{user_id}/projects
Content-Type: application/json

{
  "name": "my-project",
  "github_token_source": "global" | "project" | "none",
  "github_token": "ghp_xxx" // only if source is "project"
}

Response: 201 Created
{
  "message": "Project created successfully",
  "project_id": "64a7b5c8e4b0a1b2c3d4e5f6",
  "github_token_source": "global"
}
```

#### Update Project GitHub Token with Global Option
```http
PUT /users/{user_id}/projects/{project_id}/github-key
Content-Type: application/json

{
  "github_token_source": "global" | "project" | "none",
  "github_token": "ghp_xxx" // only if source is "project"
}

Response: 200 OK
{
  "message": "Project GitHub token updated successfully",
  "github_token_source": "global"
}
```

## Security Considerations

### Token Storage Security
1. **Encryption**: All tokens encrypted before K8s secret storage
2. **Access Control**: Only project deployments can access relevant tokens
3. **Audit Trail**: Log token usage and updates
4. **Scope Limitation**: Encourage minimal required GitHub token scopes

### Token Resolution Priority
```python
def get_effective_github_token(user_id: str, project_id: str) -> Optional[str]:
    """
    Token priority: Project-specific > Global > None
    """
    # 1. Check for project-specific token
    project_token = get_project_github_token(project_id)
    if project_token:
        return project_token
        
    # 2. Fall back to global user token
    global_token = get_user_global_github_token(user_id)
    if global_token:
        return global_token
        
    # 3. No token available
    return None
```

## Migration Strategy

### Existing User Migration
1. **Create User Records**: Generate user records for existing users
2. **Preserve Project Tokens**: Existing project tokens remain unchanged  
3. **Gradual Migration**: Users can optionally set global tokens
4. **No Breaking Changes**: Existing functionality remains identical

### Database Migration Script
```python
async def migrate_existing_users():
    """
    Create user records for existing project owners
    """
    projects = mongodb_service.list_all_projects()
    users = set(project["user_id"] for project in projects)
    
    for user_id in users:
        if not mongodb_service.user_exists(user_id):
            mongodb_service.create_user_record({
                "user_id": user_id,
                "name": f"User {user_id}",  # Can be updated later
                "github_token_set": False,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            })
```

## Success Criteria

### Functional Requirements
- ✅ Users can set global GitHub tokens
- ✅ New projects automatically inherit global tokens
- ✅ Project-specific tokens override global tokens
- ✅ Clear UI indication of token source
- ✅ Existing projects continue working unchanged

### Technical Requirements  
- ✅ Secure token storage and encryption
- ✅ Proper token resolution hierarchy
- ✅ Database migration preserves existing data
- ✅ API endpoints follow existing patterns
- ✅ Comprehensive error handling

### User Experience Requirements
- ✅ Simplified project creation workflow
- ✅ Clear token management interface
- ✅ Intuitive token source indicators
- ✅ Backward compatibility for existing users

## Estimated Effort

- **Database & Service Layer**: 1-2 days
- **Kubernetes Integration**: 1 day  
- **Frontend Implementation**: 1-2 days
- **Testing & Migration**: 1 day
- **Total**: 4-6 days

## Risk Assessment

- **Risk Level**: Medium
- **Key Risks**: 
  - Token storage security
  - Migration complexity
  - UI/UX confusion
- **Mitigation**: 
  - Comprehensive testing
  - Gradual rollout
  - Clear documentation
  - User education

## Future Enhancements

1. **Multiple Global Tokens**: Support for multiple GitHub organizations
2. **Token Validation**: Real-time GitHub token validation
3. **Permission Scopes**: UI for managing GitHub token permissions
4. **Token Rotation**: Automated token rotation capabilities
5. **Audit Logging**: Comprehensive token usage auditing