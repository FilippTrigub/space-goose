# Dynamic Volume Mounting for Sessions - Research Findings

## Executive Summary

**Bottom Line:** Adding volumes to running pods without restart is **not possible** in Kubernetes. However, there are several viable alternative approaches for implementing persistent storage per session.

## Key Research Findings

### 1. Kubernetes Volume Limitations

**Critical Finding:** Volumes cannot be added to running pods without pod restart.

- Changing volume mounts requires pod spec modification, which forces pod recreation
- This is a fundamental Kubernetes architecture limitation, not a bug
- Even privileged pods cannot dynamically mount volumes through normal K8s APIs

**Source:** Multiple Stack Overflow discussions confirm this limitation

### 2. Alternative Implementation Strategies

#### Option A: Pod Restart Approach (Simplest)
- **How it works:** When session created, restart pod with additional volume
- **Pros:** Simple implementation, uses standard K8s features
- **Cons:** Brief downtime during restart, existing sessions temporarily disrupted
- **Implementation:** Modify deployment spec to add new PVC, K8s handles pod recreation

#### Option B: StatefulSet with Volume Templates (Recommended)
- **How it works:** Convert deployments to StatefulSets, each session gets own pod+volume
- **Pros:** Each session isolated, no restarts needed, true persistent storage
- **Cons:** More complex pod management, one pod per session
- **Implementation:** Use volumeClaimTemplates for dynamic provisioning

#### Option C: Shared Volume with Session Directories
- **How it works:** Mount single large volume, create subdirectories per session
- **Pros:** No pod restarts, simple volume management
- **Cons:** Sessions share same volume (potential conflicts), manual directory management
- **Implementation:** Create emptyDir or PV, manage session dirs in application code

#### Option D: External Storage Service
- **How it works:** Session data stored in external service (database, object storage)
- **Pros:** No K8s volume complexity, highly scalable
- **Cons:** Network dependency, additional service complexity
- **Implementation:** Integrate with existing MongoDB or add S3-compatible storage

## Implementation Plan

### Recommended Approach: Option B (StatefulSets)

**Phase 1: Core Infrastructure**
1. Create StatefulSet template replacing current Deployment
2. Add volumeClaimTemplate for session storage
3. Modify k8s_service.py to create StatefulSet instead of Deployment

**Phase 2: Session Management**
1. Modify session creation to scale StatefulSet
2. Each session gets dedicated pod (proj-{project_id}-session-{index})
3. Automatic PVC creation per session pod

**Phase 3: Session Lifecycle**
1. Implement session deletion (scale down StatefulSet)
2. Handle PVC cleanup policies
3. Add session data migration/backup capabilities

### Alternative: Option A (Pod Restart) for MVP

**Simpler approach for immediate implementation:**
1. When session created, add PVC to deployment spec
2. Let K8s restart pod with new volume
3. Sessions resume after brief interruption

## Code Changes Required

### For StatefulSet Approach

```python
# In k8s_service.py - Replace apply_project_resources()
def create_project_statefulset(user_id: str, project_id: str, github_key: str = None):
    """Create StatefulSet instead of Deployment for dynamic session volumes"""
    # StatefulSet with volumeClaimTemplates
    pass

def create_session_pod(user_id: str, project_id: str, session_id: str):
    """Scale StatefulSet to create new pod for session"""
    # Scale up StatefulSet replicas
    pass
```

### For Pod Restart Approach

```python
# In k8s_service.py
def add_session_volume(user_id: str, project_id: str, session_id: str):
    """Add volume to existing deployment (causes restart)"""
    deployment = get_deployment(...)
    # Add new volumeMount and PVC
    # Update deployment (triggers restart)
    pass
```

## Storage Considerations

- **Volume Type:** Use dynamic provisioning with StorageClass
- **Size:** Start with small volumes (1-5GB per session)
- **Access Mode:** ReadWriteOnce (single pod access)
- **Reclaim Policy:** Delete (auto-cleanup when session deleted)

## Cost/Performance Impact

- **StatefulSet:** More pods = higher resource usage but better isolation
- **Pod Restart:** Minimal additional resources, brief service interruption
- **Storage Costs:** Depends on session count and data size

## Conclusion

While dynamic volume mounting without restart is impossible, the StatefulSet approach provides the best balance of functionality and Kubernetes best practices. For immediate needs, the pod restart approach offers a simpler path to persistent session storage.