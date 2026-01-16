"""Base agent interface for all PharmHunter agents."""

from abc import ABC, abstractmethod
from typing import Any, Callable, Optional


class BaseAgent(ABC):
    """Abstract base class for all agents in the PharmHunter pipeline."""
    
    def __init__(self, on_progress: Optional[Callable[[str], None]] = None):
        """
        Initialize the agent.
        
        Args:
            on_progress: Optional callback for progress updates
        """
        self.on_progress = on_progress
    
    def report_progress(self, message: str) -> None:
        """Report progress to the UI if callback is set."""
        if self.on_progress:
            self.on_progress(message)
    
    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """
        Execute the agent's main task.
        
        Args:
            **kwargs: Agent-specific parameters
            
        Returns:
            Agent-specific result type
        """
        pass
