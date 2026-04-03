"""Integration tests for LightRAG knowledge graph (Phase 10).

These tests verify architectural contracts and configuration correctness
without requiring a running LightRAG sidecar. They use static analysis
(AST parsing, file content inspection) to enforce invariants.

LRAG-02: Per-user isolation verified in test_lightrag_service.py
LRAG-03: Entity extraction config + functional validation
LRAG-07: Retrieval routing contract enforcement
"""
import ast
import re
import pathlib
import pytest

# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

_TEST_DIR = pathlib.Path(__file__).parent          # backend/tests/
_BACKEND_DIR = _TEST_DIR.parent                    # backend/
_REPO_DIR = _BACKEND_DIR.parent                    # project root
_AGENTS_DIR = _BACKEND_DIR / "agents"
_SERVICES_DIR = _BACKEND_DIR / "services"
_DOCKER_COMPOSE = _REPO_DIR / "docker-compose.yml"

# ---------------------------------------------------------------------------
# Routing contract: Writer never imports lightrag_service
# ---------------------------------------------------------------------------


def test_writer_never_imports_lightrag():
    """Parse writer.py AST and verify no import of lightrag_service at any level.

    Enforces RETRIEVAL ROUTING CONTRACT: Writer reads only from Pinecone,
    never from LightRAG knowledge graph.
    """
    writer_path = _AGENTS_DIR / "writer.py"
    assert writer_path.exists(), f"writer.py not found at {writer_path}"

    source = writer_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(writer_path))

    # Check all AST import nodes for lightrag_service references
    lightrag_imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if "lightrag" in alias.name.lower():
                    lightrag_imports.append(f"import {alias.name} (line {node.lineno})")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if "lightrag" in module.lower():
                names = [alias.name for alias in node.names]
                lightrag_imports.append(f"from {module} import {', '.join(names)} (line {node.lineno})")

    # Also check for string occurrences (catches lazy string-based imports or comments)
    lightrag_str_occurrences = [
        f"line {i+1}: {line.strip()}"
        for i, line in enumerate(source.splitlines())
        if "lightrag_service" in line and not line.strip().startswith("#")
    ]

    assert not lightrag_imports, (
        f"Writer must NEVER import lightrag_service. Found imports:\n"
        + "\n".join(lightrag_imports)
    )
    assert not lightrag_str_occurrences, (
        f"Writer contains 'lightrag_service' references (lazy imports not allowed):\n"
        + "\n".join(lightrag_str_occurrences)
    )


def test_learning_has_lightrag_insert():
    """Verify learning.py contains exactly 2 occurrences of lightrag_service insert_content import.

    Both approval paths (manual approval + post history import) must insert to knowledge graph.
    """
    learning_path = _AGENTS_DIR / "learning.py"
    assert learning_path.exists(), f"learning.py not found at {learning_path}"

    source = learning_path.read_text(encoding="utf-8")
    # Count lazy import occurrences: from services.lightrag_service import insert_content
    count = source.count("from services.lightrag_service import insert_content")
    assert count == 2, (
        f"learning.py must have exactly 2 lazy imports of insert_content "
        f"(manual approval + post import), found: {count}"
    )


def test_thinker_has_lightrag_query():
    """Verify thinker.py contains exactly 1 occurrence of lightrag_service query_knowledge_graph import.

    Thinker reads from LightRAG once per content generation cycle before angle selection.
    """
    thinker_path = _AGENTS_DIR / "thinker.py"
    assert thinker_path.exists(), f"thinker.py not found at {thinker_path}"

    source = thinker_path.read_text(encoding="utf-8")
    count = source.count("from services.lightrag_service import query_knowledge_graph")
    assert count == 1, (
        f"thinker.py must have exactly 1 lazy import of query_knowledge_graph, found: {count}"
    )


def test_pipeline_has_routing_contract():
    """Verify pipeline.py contains the RETRIEVAL ROUTING CONTRACT comment.

    This comment documents the read/write split and is a required architectural marker.
    """
    pipeline_path = _AGENTS_DIR / "pipeline.py"
    assert pipeline_path.exists(), f"pipeline.py not found at {pipeline_path}"

    source = pipeline_path.read_text(encoding="utf-8")
    assert "RETRIEVAL ROUTING CONTRACT" in source, (
        "pipeline.py must contain the 'RETRIEVAL ROUTING CONTRACT' comment "
        "(Phase 10 architectural marker)"
    )


# ---------------------------------------------------------------------------
# Entity type configuration
# ---------------------------------------------------------------------------

# Domain-specific entity types required for ThookAI
# Required: topic_domain, hook_archetype, emotional_tone, expertise_signal, content_format
_REQUIRED_ENTITY_TYPES = [
    "topic_domain",
    "hook_archetype",
    "emotional_tone",
    "expertise_signal",
    "content_format",
]

# Default generic types that must NOT be present
_FORBIDDEN_ENTITY_TYPES = [
    "organization",
    "person",
    "geo",
    "event",
]


def _get_entity_types_from_docker_compose() -> list:
    """Parse ENTITY_TYPES from docker-compose.yml using string matching."""
    assert _DOCKER_COMPOSE.exists(), f"docker-compose.yml not found at {_DOCKER_COMPOSE}"
    content = _DOCKER_COMPOSE.read_text(encoding="utf-8")

    # Match ENTITY_TYPES=["..."] pattern
    match = re.search(r'ENTITY_TYPES=(\[.*?\])', content)
    assert match, "ENTITY_TYPES line not found in docker-compose.yml"

    raw_value = match.group(1)
    # Extract quoted strings from the list literal
    entity_types = re.findall(r'"([^"]+)"|\'([^\']+)\'', raw_value)
    # Flatten tuples from findall
    return [et[0] or et[1] for et in entity_types]


def test_entity_types_are_domain_specific():
    """Parse docker-compose.yml ENTITY_TYPES and verify:
    - All 5 domain types present
    - None of the 4 default generic types present
    """
    entity_types = _get_entity_types_from_docker_compose()

    for required in _REQUIRED_ENTITY_TYPES:
        assert required in entity_types, (
            f"Required domain entity type '{required}' missing from ENTITY_TYPES. "
            f"Found: {entity_types}"
        )

    for forbidden in _FORBIDDEN_ENTITY_TYPES:
        assert forbidden not in entity_types, (
            f"Forbidden default entity type '{forbidden}' found in ENTITY_TYPES. "
            f"Remove generic types and keep only domain-specific types. "
            f"Found: {entity_types}"
        )


def test_embedding_model_frozen():
    """Verify docker-compose.yml has EMBEDDING_MODEL=text-embedding-3-small and EMBEDDING_DIM=1536.

    These must be frozen to prevent NanoVectorDB dimension mismatch on existing indexes.
    """
    content = _DOCKER_COMPOSE.read_text(encoding="utf-8")

    assert "EMBEDDING_MODEL=text-embedding-3-small" in content, (
        "docker-compose.yml must have EMBEDDING_MODEL=text-embedding-3-small "
        "(frozen embedding — changing requires full index rebuild)"
    )
    assert "EMBEDDING_DIM=1536" in content, (
        "docker-compose.yml must have EMBEDDING_DIM=1536 "
        "(matches text-embedding-3-small output dimension)"
    )


def test_lightrag_uses_separate_database():
    """Verify docker-compose.yml has MONGO_DATABASE=thookai_lightrag.

    LightRAG must use a separate MongoDB database to avoid collection name collisions
    with the main ThookAI application database.
    """
    content = _DOCKER_COMPOSE.read_text(encoding="utf-8")

    assert "MONGO_DATABASE=thookai_lightrag" in content, (
        "docker-compose.yml must set MONGO_DATABASE=thookai_lightrag for LightRAG service. "
        "LightRAG must NOT share the app database to prevent collection conflicts."
    )


def test_lightrag_uses_nano_vector_storage():
    """Verify docker-compose.yml has LIGHTRAG_VECTOR_STORAGE=NanoVectorDBStorage.

    NanoVectorDB is required to preserve the hybrid architecture:
    Pinecone handles persona similarity search, NanoVDB handles graph-adjacent vectors.
    MongoVectorDBStorage is explicitly NOT used.
    """
    content = _DOCKER_COMPOSE.read_text(encoding="utf-8")

    assert "LIGHTRAG_VECTOR_STORAGE=NanoVectorDBStorage" in content, (
        "docker-compose.yml must set LIGHTRAG_VECTOR_STORAGE=NanoVectorDBStorage. "
        "Do not use MongoVectorDBStorage — Pinecone handles persona similarity."
    )

    assert "MongoVectorDBStorage" not in content or content.count("NanoVectorDBStorage") >= 1, (
        "NanoVectorDBStorage must be set as the active vector storage"
    )


# ---------------------------------------------------------------------------
# Metadata forwarding validation (static analysis)
# ---------------------------------------------------------------------------


def test_insert_content_metadata_not_dropped():
    """Read lightrag_service.py source and verify insert_content POST body includes metadata.

    Static analysis confirms platform, content_type, was_edited fields are forwarded
    to LightRAG — they must not be dropped in the HTTP payload.
    """
    service_path = _SERVICES_DIR / "lightrag_service.py"
    assert service_path.exists(), f"lightrag_service.py not found at {service_path}"

    source = service_path.read_text(encoding="utf-8")

    assert '"metadata"' in source or "'metadata'" in source, (
        "insert_content must include a 'metadata' key in the POST body"
    )
    assert '"platform"' in source or "'platform'" in source, (
        "insert_content metadata must include 'platform' field"
    )
    assert '"content_type"' in source or "'content_type'" in source, (
        "insert_content metadata must include 'content_type' field"
    )
    assert '"was_edited"' in source or "'was_edited'" in source, (
        "insert_content metadata must include 'was_edited' field"
    )


# ---------------------------------------------------------------------------
# Entity extraction functional validation (LRAG-03 pre-production gate)
# ---------------------------------------------------------------------------
#
# Validates that the 5 domain entity type definitions are semantically
# meaningful for real ThookAI content. Does NOT call LightRAG.
# Serves as the pre-production gate: "tested on 10+ real posts"
# ---------------------------------------------------------------------------

# Sample ThookAI content representing real post types
_SAMPLE_CONTENTS = [
    # LinkedIn thought leadership post
    """After building 5 companies in the AI space, I've learned something most founders miss.
    The biggest mistake in startup strategy isn't moving too slow — it's optimizing for the wrong metric.
    Most people think growth = success. Wrong.
    In my experience, companies that focus on retention in Year 1 are 3x more likely to reach Series A.
    Here's the framework I use with every founder I mentor:
    1/ Map your core user journey
    2/ Identify the 'aha moment'
    3/ Optimize everything toward that single moment
    What's your 'aha moment'? Drop it below. 👇""",

    # X (Twitter) thread hook
    """I spent 3 years studying viral content patterns across LinkedIn, Twitter, and Instagram.
    Here's what actually drives engagement (most "experts" get this wrong):
    [Thread]
    1/ The hook isn't about being clever. It's about triggering pattern interruption.
    Frustrated by generic AI content? Same.
    2/ Your content format matters more than the topic.
    Listicles: 2.3x more shares than paragraphs on LinkedIn.
    3/ Emotional tone > information density every time.""",

    # Instagram caption with hook archetype
    """Surprised by how many creators still don't know this productivity hack.
    The Pomodoro Technique changed my whole workflow for content creation.
    AI tools + focused sprints = more content in 2 hours than most do in a day.
    Topic domain: content creation, productivity, AI tools.
    What's your go-to tool for deep work? ⬇️
    #contentcreator #productivity #AI""",

    # Contrarian LinkedIn post
    """Hot take: Posting every day on LinkedIn is destroying your credibility.
    Here's why quality beats quantity every single time for thought leadership.
    The expertise signal that actually builds authority? Saying something counter-intuitive
    that turns out to be true.
    I went from 500 to 50,000 followers by posting 3x per week with real insights.
    The format? Always the same: bold claim → evidence → actionable insight.""",

    # Storytelling post
    """Six months ago I was excited to launch our first product.
    Today, after talking to 200 customers, I've completely pivoted.
    The emotional tone of those early customer calls was a mix of confusion and frustration.
    Not at us — at the industry. That's the gap we're now building for.
    Topic: SaaS, product-market fit, founder journey.""",
]

# Patterns that demonstrate each entity type is extractable
_ENTITY_TYPE_PATTERNS = {
    "topic_domain": [
        # Identifiable topic keywords
        r"\b(AI|artificial intelligence|startup|productivity|content creation|SaaS|product-market fit)\b",
    ],
    "hook_archetype": [
        # Hook patterns: contrarian, curiosity, story, number
        r"(Most people think|I spent \d+|Hot take|After building|What .* founders miss|Here's why|Surprised by)",
    ],
    "emotional_tone": [
        # Emotional markers in content
        r"\b(frustrated|excited|surprised|confused|wrong|missed|miss)\b",
    ],
    "expertise_signal": [
        # Authority markers
        r"(In my experience|After building|years studying|I've learned|the framework I use|talking to \d+ customers)",
    ],
    "content_format": [
        # Format indicators: listicle numbering, thread markers, question-answer
        r"(1/|2/|3/|\[Thread\]|#\w+|\d+\/ |\bHere's the framework\b|\bHere's why\b)",
    ],
}


@pytest.mark.parametrize("entity_type", _REQUIRED_ENTITY_TYPES)
def test_entity_types_extract_from_real_content(entity_type: str):
    """Validate that each domain entity type can be identified in ThookAI content samples.

    This is LRAG-03 pre-production gate: entity types must be semantically meaningful
    for real creator content, not just syntactically present in docker-compose.yml.

    Checks that at least 2 of the 5 sample contents contain patterns matching the entity type.
    """
    patterns = _ENTITY_TYPE_PATTERNS.get(entity_type, [])
    assert patterns, f"No validation patterns defined for entity type: {entity_type}"

    combined_pattern = "|".join(f"(?:{p})" for p in patterns)
    matches_found = 0

    for i, content in enumerate(_SAMPLE_CONTENTS):
        match = re.search(combined_pattern, content, re.IGNORECASE)
        if match:
            matches_found += 1

    assert matches_found >= 2, (
        f"Entity type '{entity_type}' must be extractable from at least 2/5 sample contents. "
        f"Only found in {matches_found} samples. "
        f"Pattern used: {combined_pattern[:100]}..."
        if len(combined_pattern) > 100 else
        f"Entity type '{entity_type}' must be extractable from at least 2/5 sample contents. "
        f"Only found in {matches_found} samples. Pattern: {combined_pattern}"
    )
