For the sake of clarity, this is a summary my current approach:

Stage 1:
Re-user CLI across isolated containers tied to user id and project id
1. web app with multi-user support (no auth, just switching users), UI and backend facilitating the environment orchestration
2. each user has a set of projects and can perform CRUD on them
3. each project id will have an associated container with the existing goose cli api (and ultimately gh repo) controlled via kubernetes / podman
4. user can send messages to the ai in that container to interact with the repo and build code

Drawbacks:
- containers are not meant to be persistent (high cost), but the user might forget to push changes to the repo
- custom goose cli image creates management overhead for container nodes in kubernetes cluster

Stage 2:
More advanced plan: Use goose cli with container-use MCP and dagger runners deployed across kubernetes / podman
1. same as stage 1: web ui with multi-user support (no auth, just switching users), UI and backend facilitating the environment orchestration
2. same as stage 1: each user has a set of projects and can perform CRUD on them
3. similar to stage 1: each user can access an isolated goose cli environments (similar to the first plan, but only 1 persistent environment) 
4. new: each goose cli uses container-use mcp to execute build instructions for a given project via dagger
5. new: container-use & dagger enable goose to clone the repo and work on the code inside a container orchestrated on kubernetes / podman

Why stage 2:
- dagger is purpose built for agentic coding in isolated envs (integrates git repos and facilitates lifecycle) and integrates well with kubernetes
- container-use can be direclty integrated into the existing goose api server via MCP

