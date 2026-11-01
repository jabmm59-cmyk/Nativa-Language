"""
NAgame Backend - Implementação Pygame para NAgame
"""

from .window import NAgameWindow
from .graphics import NAgameGraphics
from .audio import NAgameAudio
from .physics import NAgamePhysics
from .input import NAgameInput
from .animation import NAgameAnimation
from .particles import NAgameParticles
from .camera import NAgameCamera
from .interface import NAgameInterface

__all__ = [
    'NAgameWindow',
    'NAgameGraphics',
    'NAgameAudio',
    'NAgamePhysics',
    'NAgameInput',
    'NAgameAnimation',
    'NAgameParticles',
    'NAgameCamera',
    'NAgameInterface',
]