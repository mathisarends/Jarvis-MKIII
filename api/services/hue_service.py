import asyncio
import json
import os
from typing import Dict, List, Optional

from fastapi import HTTPException
from hueify import GroupsManager, HueBridge

from plugins.alarm.daylight_alarm import AlarmSystem


class HueService:
    """Service for managing Hue scenes and lighting integration"""

    def __init__(self):
        self.bridge: Optional[HueBridge] = None
        self.groups_manager: Optional[GroupsManager] = None
        self.alarm_system: AlarmSystem = AlarmSystem.get_instance()
        self._initialize_bridge()

    def _initialize_bridge(self) -> None:
        """Initialize Hue Bridge connection"""
        try:
            self.bridge = HueBridge.connect_by_ip()
            self.groups_manager = GroupsManager(self.bridge)
        except Exception as e:
            print(f"Warning: Could not connect to Hue Bridge: {e}")
            self.bridge = None
            self.groups_manager = None

    async def get_available_scenes(self, room_name: str = "Zimmer 1") -> List[str]:
        """Get all available scenes for the configured room"""
        if not self.groups_manager:
            raise HTTPException(status_code=503, detail="Hue Bridge not available")

        try:
            room_controller = await self.groups_manager.get_controller(room_name)
            return (await room_controller.scene_controller.get_scene_names())[:8]

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to get scenes: {str(e)}"
            )

    async def temporarily_activate_scene(
        self, scene_name: str, duration: int = 8
    ) -> None:
        """Temporarily activate a scene for a specified duration"""
        if not self.groups_manager:
            raise HTTPException(status_code=503, detail="Hue Bridge not available")

        try:
            room_controller = await self.groups_manager.get_controller("Zimmer 1")
            saved_state = await room_controller.save_state("previous_scene")
            await room_controller.activate_scene(scene_name)

            await asyncio.sleep(duration)

            await room_controller.restore_state(saved_state)

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to activate scene: {str(e)}"
            )

    def get_current_wake_up_scene(self) -> Optional[str]:
        """Get the currently configured wake-up scene"""
        settings = self.alarm_system.get_global_settings()
        return settings.get("wake_up_scene_name")
