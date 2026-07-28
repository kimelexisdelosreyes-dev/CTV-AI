# Search Runtime Pipeline

Universal Search consumes a presentation adapter. The adapter calls `ISearchService`, which discovers providers through `SearchRegistry`, executes SDK-based providers in parallel, normalizes and ranks results, merges duplicates where stable keys permit, and returns diagnostics. Phase 4.1C registers the generic demo provider plus local files, knowledge, and projects providers.
