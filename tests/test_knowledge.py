import pytest
from uuid import uuid4
from pydantic import ValidationError
from app.schemas.knowledge import KnowledgeMemoryCreate, Provenance

def test_knowledge_memory_provenance_validation():
    # Valid
    prov = Provenance(source_refs=[uuid4()], source_mode="ground")
    assert prov.source_mode == "ground"
    
    # Invalid missing mode
    with pytest.raises(ValidationError):
        Provenance(source_refs=[uuid4()])

def test_knowledge_memory_create_schema():
    prov = Provenance(source_refs=[uuid4()], source_mode="ground")
    
    # Valid
    mem = KnowledgeMemoryCreate(
        knowledge_type="finding",
        content="The sky is blue",
        status="verified",
        provenance=prov
    )
    assert mem.content == "The sky is blue"
    assert mem.provenance.source_mode == "ground"
    
    # Invalid missing required provenance
    with pytest.raises(ValidationError):
        KnowledgeMemoryCreate(
            knowledge_type="finding",
            content="The sky is blue",
            status="verified"
        )
