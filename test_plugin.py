# ba_meta require api 9

import babase


# ba_meta export babase.Plugin
class TestPlugin(babase.Plugin):
    """Minimal BombSquad API 9 plugin."""

    def on_app_running(self) -> None:
        babase.screenmessage(
            "Test Plugin Loaded",
            color=(0.3, 1.0, 0.4),
        )
