# Infrastructure Provider Boundaries

Phase 4.1D models indexed local-demo infrastructure metadata from the existing enterprise map. The infrastructure, storage, workstation, and compute providers are SDK-based and registered only by the search composition root.

They never connect to NAS SMB, cloud storage, Docker, Ollama, Windows APIs, networks, or remote command channels. Their health reflects indexed metadata only, not active monitoring. Missing capacity, utilization, GPU, CPU, RAM, and model inventory are explicitly not represented rather than inferred.
