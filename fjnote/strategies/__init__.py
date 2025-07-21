"""
Strategies package
"""

from .note_strategies import INoteStrategy, FlashNoteStrategy, TodoNoteStrategy

__all__ = ['INoteStrategy', 'FlashNoteStrategy', 'TodoNoteStrategy']