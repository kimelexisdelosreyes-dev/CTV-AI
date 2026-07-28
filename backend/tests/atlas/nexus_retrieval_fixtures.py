from app.atlas.providers.nexus import NexusEntity, NexusGraphBuilder, NexusGraphSnapshot, NexusRelationship


def retrieval_snapshot() -> NexusGraphSnapshot:
    entities = (
        NexusEntity(entity_id="doc_a", entity_type="knowledge_document", label="Doc A", source_reference="nexus:doc_a", confidence=100),
        NexusEntity(entity_id="policy_a", entity_type="policy", label="Policy A", source_reference="nexus:policy_a", confidence=100),
        NexusEntity(entity_id="project_a", entity_type="project", label="Project A", source_reference="nexus:project_a", confidence=90),
        NexusEntity(entity_id="asset_a", entity_type="media_asset", label="Asset A", source_reference="nexus:asset_a", confidence=80),
        NexusEntity(entity_id="event_a", entity_type="event", label="Event A", source_reference="nexus:event_a", confidence=70),
    )
    relationships = (
        NexusRelationship(relationship_id="rel_doc_policy", source_entity_id="doc_a", target_entity_id="policy_a", relationship_type="direct_reference", source_reference="nexus:rel_doc_policy", confidence=100),
        NexusRelationship(relationship_id="rel_doc_project", source_entity_id="doc_a", target_entity_id="project_a", relationship_type="document_relates_to_project", source_reference="nexus:rel_doc_project", confidence=90),
        NexusRelationship(relationship_id="rel_project_asset", source_entity_id="project_a", target_entity_id="asset_a", relationship_type="asset_related_to", source_reference="nexus:rel_project_asset", confidence=80),
        NexusRelationship(relationship_id="rel_asset_event", source_entity_id="asset_a", target_entity_id="event_a", relationship_type="media_relation", source_reference="nexus:rel_asset_event", confidence=70),
        NexusRelationship(relationship_id="rel_event_doc", source_entity_id="event_a", target_entity_id="doc_a", relationship_type="project_association", source_reference="nexus:rel_event_doc", confidence=60),
    )
    return NexusGraphBuilder.from_graph(entities, relationships)

