# RexLapisLib/__init__.py

# From client.py
from .core.client import Client

# From manager.py
from .core.manager import TradeManager, PositionExecutor

# From data_processor.py
from .core.data_processor import DataProcessor

# From engine.py
from .core.engine import TechnicalEngine

# From backtester.py
from .core.backtester import BacktestEngine

# From strategy.py
from .core.strategy import Strategy

# From context.py
from .core.context import LiveContext, BacktestContext, IContext

# From visualizer.py
from .core.visualizer import show_dashboard

# From states.py
from .models.states import ExecutorState

# Define the public API of the package
__all__ = [
    "Client",
    "TradeManager",
    "PositionExecutor",
    "DataProcessor",
    "TechnicalEngine",
    "BacktestEngine",
    "Strategy",
    "LiveContext",
    "BacktestContext",
    "IContext",
    "show_dashboard",
    "ExecutorState"
]