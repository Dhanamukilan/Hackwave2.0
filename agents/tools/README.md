# tools
Explicit, allowlisted tool functions the agents may call: get_test_history, get_failure_history, search_similar_failures, get_commit_diff, get_recent_commits, get_changed_files, get_component_owner, get_environment_history, get_deployment_history, calculate_flakiness, get_runtime_evidence. Each tool queries real Postgres/Qdrant data — agents cannot invent evidence.
