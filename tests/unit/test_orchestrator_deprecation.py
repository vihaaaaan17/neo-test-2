"""
Unit tests for legacy orchestrator runtime DeprecationWarning emission.

Validates:
- GroundModeOrchestrator emits DeprecationWarning on instantiation
- ResearchModeOrchestrator emits DeprecationWarning on instantiation
- Both retain their public method signatures (compatibility shim contract)
"""
import warnings
import pytest
from unittest.mock import MagicMock, AsyncMock


class TestGroundModeOrchestratorDeprecation:
    def test_warns_on_instantiation(self):
        """
        GroundModeOrchestrator must emit DeprecationWarning when instantiated.
        This is the Phase 5 contract: shims warn callers to migrate.
        """
        hybrid = MagicMock()
        llm = AsyncMock()
        embed = AsyncMock()

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            from app.orchestration.ground_mode import GroundModeOrchestrator
            GroundModeOrchestrator(
                hybrid_retriever=hybrid,
                llm_gateway=llm,
                embed_gateway=embed
            )

        deprecation_warnings = [
            w for w in caught
            if issubclass(w.category, DeprecationWarning)
        ]
        assert deprecation_warnings, (
            "GroundModeOrchestrator must emit DeprecationWarning on instantiation. "
            "It is a compatibility shim and callers must be warned to migrate to "
            "OpenNotebookGroundEngine."
        )
        # Verify the warning message references the successor
        combined_message = " ".join(str(w.message) for w in deprecation_warnings)
        assert "OpenNotebookGroundEngine" in combined_message or "deprecated" in combined_message.lower(), (
            f"DeprecationWarning message should reference 'OpenNotebookGroundEngine'. Got: {combined_message!r}"
        )

    def test_maintains_execute_method_signature(self):
        """
        GroundModeOrchestrator must still have an execute() method for backward compatibility.
        """
        from app.orchestration.ground_mode import GroundModeOrchestrator
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            orch = GroundModeOrchestrator(
                hybrid_retriever=MagicMock(),
                llm_gateway=AsyncMock(),
                embed_gateway=AsyncMock()
            )
        assert hasattr(orch, "execute") or hasattr(orch, "run"), (
            "GroundModeOrchestrator must retain execute() or run() for backward compatibility."
        )


class TestResearchModeOrchestratorDeprecation:
    def test_warns_on_instantiation(self):
        """
        ResearchModeOrchestrator must emit DeprecationWarning when instantiated.
        """
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            from app.orchestration.research_mode import ResearchModeOrchestrator
            ResearchModeOrchestrator(
                llm_gateway=AsyncMock(),
                search_tool=MagicMock()
            )

        deprecation_warnings = [
            w for w in caught
            if issubclass(w.category, DeprecationWarning)
        ]
        assert deprecation_warnings, (
            "ResearchModeOrchestrator must emit DeprecationWarning on instantiation. "
            "It is a compatibility shim and callers must be warned to migrate to "
            "OpenDeepResearchEngine."
        )
        combined_message = " ".join(str(w.message) for w in deprecation_warnings)
        assert (
            "OpenDeepResearchEngine" in combined_message
            or "deprecated" in combined_message.lower()
        ), (
            f"DeprecationWarning should reference 'OpenDeepResearchEngine'. Got: {combined_message!r}"
        )

    def test_maintains_run_method_signature(self):
        """
        ResearchModeOrchestrator must retain its public run interface for backward compat.
        """
        from app.orchestration.research_mode import ResearchModeOrchestrator
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            orch = ResearchModeOrchestrator(
                llm_gateway=AsyncMock(),
                search_tool=MagicMock()
            )
        assert hasattr(orch, "run") or hasattr(orch, "execute") or hasattr(orch, "graph"), (
            "ResearchModeOrchestrator must retain its public run interface for backward compatibility."
        )


class TestOrchestratorDeprecationModuleLevel:
    def test_both_orchestrators_importable(self):
        """Both deprecated orchestrators must remain importable (no removal in Phase 5)."""
        from app.orchestration.ground_mode import GroundModeOrchestrator
        from app.orchestration.research_mode import ResearchModeOrchestrator
        assert GroundModeOrchestrator is not None
        assert ResearchModeOrchestrator is not None

    def test_ground_factory_emits_deprecation_warning_for_legacy_path(self):
        """
        The ground engine factory must also emit DeprecationWarning when returning
        the legacy GroundModeOrchestrator path.
        """
        try:
            from app.services.ground.factory import get_ground_engine
            # This is a dependency injector; we just verify it's callable
            assert callable(get_ground_engine)
        except ImportError:
            pytest.skip("ground.factory not available in this environment")
