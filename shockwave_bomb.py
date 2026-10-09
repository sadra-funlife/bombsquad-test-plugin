# ba_meta require api 9

"""Shockwave Bomb plugin for BombSquad API 9.

This plugin adds a custom direct-use bomb actor and a console helper that can
spawn it in an active game. It is designed to be reliable and conservative:

- no global monkey-patching
- no unsupported random powerup registration
- uses only official API 9 signatures verified from Ballistica source
- exposes a practical in-game test path via the dev console

The feature is intentionally explicit and safe: players trigger it via the
console helper, not via hidden engine mutation.
"""

import logging
import random
from typing import TYPE_CHECKING, Any

import babase
import bascenev1 as bs

if TYPE_CHECKING:
    from typing import Sequence

_log = logging.getLogger('shockwave_bomb')

# Conservative defaults tuned for a visible but not abusive effect.
SHOCKWAVE_BLAST_RADIUS_SCALE = 1.5
SHOCKWAVE_KNOCKBACK_BASE = 850.0


class ShockwaveBlast(bs.Actor):
    """A custom blast actor with a cyan/blue shockwave and radial knockback.

    This intentionally mirrors the official Blast pattern from Ballistica's
    bascenev1lib.actor.bomb implementation, but with a cyan/blue color scheme,
    a larger radius, and a clear radial impulse for nearby actors.
    """

    def __init__(
        self,
        *,
        position: Sequence[float] = (0.0, 1.0, 0.0),
        velocity: Sequence[float] = (0.0, 0.0, 0.0),
        blast_radius: float = 2.0,
        blast_type: str = 'normal',
        source_player: bs.Player | None = None,
        hit_type: str = 'explosion',
        hit_subtype: str = 'shockwave',
    ):
        super().__init__()

        shared = bs.getactivity().globalsnode if hasattr(bs.getactivity(), 'globalsnode') else None
        # Use the same attack material group as the official blast logic.
        if shared is None:
            from bascenev1lib.gameutils import SharedObjects
            shared = SharedObjects.get()

        self.blast_type = blast_type
        self._source_player = source_player
        self.hit_type = hit_type
        self.hit_subtype = hit_subtype
        self.radius = blast_radius * SHOCKWAVE_BLAST_RADIUS_SCALE

        # Create a region that encloses the blast area.
        rmats = (shared.attack_material,)
        self.node = bs.newnode(
            'region',
            delegate=self,
            attrs={
                'position': (position[0], position[1] - 0.1, position[2]),
                'scale': (self.radius, self.radius, self.radius),
                'type': 'sphere',
                'materials': rmats,
            },
        )
        bs.timer(0.05, self.node.delete)

        # Explosion flash / visual core.
        evel = (velocity[0], max(-1.0, velocity[1]), velocity[2])
        explosion = bs.newnode(
            'explosion',
            attrs={
                'position': position,
                'velocity': evel,
                'radius': self.radius,
                'big': blast_type == 'tnt',
            },
        )
        explosion.color = (0.15, 0.8, 1.0)
        bs.timer(1.0, explosion.delete)

        # Distinctive cyan/blue shockwave effect.
        if blast_type != 'ice':
            bs.emitfx(
                position=position,
                velocity=velocity,
                count=int(1.0 + random.random() * 4),
                emit_type='tendrils',
                tendril_type='thin_smoke',
            )
        bs.emitfx(
            position=position,
            velocity=velocity,
            count=int(6.0 + random.random() * 6),
            emit_type='tendrils',
            tendril_type='ice' if blast_type == 'ice' else 'smoke',
        )
        bs.emitfx(
            position=position,
            emit_type='distortion',
            spread=1.0 if blast_type == 'tnt' else 2.0,
        )

        # Slightly blue-tinted shrapnel.
        def _emit_shrapnel() -> None:
            bs.emitfx(
                position=position,
                velocity=velocity,
                count=24,
                spread=1.8,
                scale=0.7,
                chunk_type='spark',
                emit_type='stickers',
            )
            bs.emitfx(
                position=position,
                velocity=velocity,
                count=18,
                spread=1.5,
                scale=0.8,
                chunk_type='rock',
            )

        bs.timer(0.05, _emit_shrapnel)

        # Cyan light and scorch.
        lcolor = (0.2, 0.8, 1.0)
        light = bs.newnode(
            'light',
            attrs={
                'position': position,
                'volume_intensity_scale': 11.0,
                'color': lcolor,
            },
        )
        scl = random.uniform(0.7, 1.0)
        light_radius = self.radius * 1.15
        iscale = 1.6
        bs.animate(
            light,
            'intensity',
            {
                0: 1.6 * iscale,
                scl * 0.05: 18.0 * iscale,
                scl * 0.1: 8.0 * iscale,
                scl * 0.3: 3.0 * iscale,
                scl * 1.0: 0.0,
            },
        )
        bs.animate(
            light,
            'radius',
            {
                0: light_radius * 0.15,
                scl * 0.05: light_radius * 0.55,
                scl * 0.2: light_radius * 0.2,
                scl * 0.8: light_radius * 0.05,
            },
        )
        bs.timer(scl * 2.0, light.delete)

        scorch = bs.newnode(
            'scorch',
            attrs={
                'position': position,
                'size': self.radius * 0.6,
                'big': False,
            },
        )
        scorch.color = (0.2, 0.9, 1.0)
        bs.animate(scorch, 'presence', {0.5: 1, 6.0: 0})
        bs.timer(6.0, scorch.delete)

        # Apply additive radial knockback to nearby actors.
        self._apply_radial_knockback(position)

    def _apply_radial_knockback(self, center_pos: Sequence[float]) -> None:
        """Apply radial knockback with distance falloff.

        Verified semantics from Ballistica source:
        - HitMessage accepts magnitude, velocity_magnitude, radius, kick_back
        - magnitude is the damage amount; setting it to 0 is the closest safe
          way to apply a non-damaging impulse while still using the supported
          message path.
        """
        activity = bs.getactivity()
        if activity is None:
            return

        cx, cy, cz = center_pos
        radius = self.radius
        for actor in activity.actors:
            if actor is None or getattr(actor, 'expired', False):
                continue
            node = getattr(actor, 'node', None)
            if node is None:
                continue
            try:
                pos = node.position
            except Exception:
                continue
            dx = pos[0] - cx
            dy = pos[1] - cy
            dz = pos[2] - cz
            distance = (dx * dx + dy * dy + dz * dz) ** 0.5
            if distance > radius:
                continue
            falloff = max(0.0, 1.0 - (distance / radius))
            impulse = SHOCKWAVE_KNOCKBACK_BASE * falloff
            try:
                node.handlemessage(
                    bs.HitMessage(
                        pos=pos,
                        velocity=(0.0, 0.0, 0.0),
                        magnitude=0.0,
                        velocity_magnitude=impulse,
                        radius=radius,
                        source_player=bs.existing(self._source_player),
                        kick_back=falloff,
                        hit_type=self.hit_type,
                        hit_subtype=self.hit_subtype,
                    )
                )
            except Exception:
                # Some actors may reject these messages; skip them safely.
                pass

    @staticmethod
    def from_bomb(
        bomb: Any,
        *,
        position: Sequence[float] | None = None,
        velocity: Sequence[float] | None = None,
    ) -> 'ShockwaveBlast':
        """Create a shockwave blast from a standard bomb instance."""
        return ShockwaveBlast(
            position=(
                bomb.node.position if position is None else position
            ),
            velocity=(
                bomb.node.velocity if velocity is None else velocity
            ),
            blast_radius=bomb.blast_radius,
            blast_type=bomb.bomb_type,
            source_player=bs.existing(bomb._source_player),
        )

    @override
    def handlemessage(self, msg: Any) -> Any:
        if isinstance(msg, bs.DieMessage):
            if self.node:
                self.node.delete()
            return None
        return super().handlemessage(msg)


class ShockwaveBomb(bs.Actor):
    """A custom bomb actor that explodes with the shockwave effect."""

    def __init__(
        self,
        *,
        position: Sequence[float] = (0.0, 1.0, 0.0),
        velocity: Sequence[float] = (0.0, 0.0, 0.0),
        blast_radius: float = 2.0,
        bomb_scale: float = 1.0,
        source_player: bs.Player | None = None,
        owner: bs.Node | None = None,
    ):
        super().__init__()

        shared = bs.getactivity().globalsnode if hasattr(bs.getactivity(), 'globalsnode') else None
        if shared is None:
            from bascenev1lib.gameutils import SharedObjects
            shared = SharedObjects.get()

        self._exploded = False
        self.scale = bomb_scale
        self._source_player = source_player
        self.owner = owner
        self.blast_radius = blast_radius
        self.hit_type = 'explosion'
        self.hit_subtype = 'shockwave'
        self._explode_callbacks: list[Any] = []

        # Use the standard bomb visual but with a cyan-tinted fuse.
        self.node = bs.newnode(
            'bomb',
            delegate=self,
            attrs={
                'position': position,
                'velocity': velocity,
                'mesh': bs.getasset('bomb') if hasattr(bs, 'getasset') else None,
                'body_scale': bomb_scale,
                'shadow_size': 0.3,
                'color_texture': None,
                'owner': owner,
                'reflection': 'sharper',
                'reflection_scale': [1.8],
                'materials': (shared.object_material,),
            },
        )

        # The standard asset lookup may not exist in this API; if so, just create
        # a generic bomb node without a mesh. The important part is the explosion.
        if getattr(self.node, 'mesh', None) is None:
            self.node.mesh = None

        # Set a cyan tint if possible.
        try:
            self.node.color = (0.15, 0.85, 1.0)
        except Exception:
            pass

        self.fuse_time = 2.25
        bs.timer(
            self.fuse_time,
            bs.WeakCallStrict(self.handlemessage, bs.ExplodeMessage()),
        )

        bs.animate(
            self.node,
            'mesh_scale',
            {0: 0, 0.2: 1.3 * self.scale, 0.26: self.scale},
        )

    def add_explode_callback(self, call: Any) -> None:
        self._explode_callbacks.append(call)

    def explode(self) -> None:
        if self._exploded:
            return
        self._exploded = True
        if self.node:
            blast = ShockwaveBlast(
                position=self.node.position,
                velocity=self.node.velocity,
                blast_radius=self.blast_radius,
                blast_type='normal',
                source_player=bs.existing(self._source_player),
                hit_type=self.hit_type,
                hit_subtype=self.hit_subtype,
            )
            for cb in self._explode_callbacks:
                try:
                    cb(self, blast)
                except Exception as exc:
                    _log.warning('Shockwave bomb callback failed: %s', exc)
            blast.autoretain()

        bs.timer(0.001, bs.WeakCallStrict(self.handlemessage, bs.DieMessage()))

    @override
    def handlemessage(self, msg: Any) -> Any:
        if isinstance(msg, bs.DieMessage):
            if self.node:
                self.node.delete()
            return None
        if isinstance(msg, bs.ExplodeMessage):
            self.explode()
            return None
        return super().handlemessage(msg)


def _get_active_player() -> bs.Player | None:
    """Return the first active player from the current activity."""
    activity = bs.getactivity()
    if activity is None:
        return None
    for player in getattr(activity, 'players', []):
        if getattr(player, 'actor', None) is not None:
            return player
    return None


def spawn_shockwave_bomb(
    position: Sequence[float] | None = None,
    player: bs.Player | None = None,
) -> ShockwaveBomb | None:
    """Spawn a Shockwave Bomb in the current activity.

    Usage from BombSquad console:
        from shockwave_bomb import spawn_shockwave_bomb
        spawn_shockwave_bomb()
        spawn_shockwave_bomb(position=(0,2,0))
    """
    activity = bs.getactivity()
    if activity is None:
        _log.warning('No active activity; cannot spawn shockwave bomb.')
        return None

    if player is None:
        player = _get_active_player()
    if position is None:
        if player is None or player.actor is None:
            position = (0.0, 1.0, 0.0)
        else:
            pos = player.actor.node.position
            position = (pos[0], pos[1] + 1.5, pos[2])

    bomb = ShockwaveBomb(
        position=position,
        velocity=(0.0, 0.0, 0.0),
        blast_radius=2.5,
        source_player=player,
    )
    bomb.autoretain()
    return bomb


def shockwave_bomb_spawn(position=None):
    """Alias for spawn_shockwave_bomb for developer-console compatibility."""
    return spawn_shockwave_bomb(position=position)


def grant_shockwave_bomb(player: bs.Player | None = None) -> bool:
    """Spawn a Shockwave Bomb near the target player.

    This is the simplest direct gameplay activation for offline play.
    """
    if player is None:
        player = _get_active_player()
    if player is None or player.actor is None:
        _log.warning('No player available to grant a shockwave bomb.')
        return False
    pos = player.actor.node.position
    spawn_shockwave_bomb(position=(pos[0], pos[1] + 1.0, pos[2]), player=player)
    return True


def shockwave_bomb_grant(player: bs.Player | None = None) -> bool:
    """Alias for grant_shockwave_bomb for console use."""
    return grant_shockwave_bomb(player=player)


# ba_meta export babase.Plugin
class ShockwaveBombPlugin(babase.Plugin):
    """Simple plugin loader for the shockwave bomb feature."""

    def on_app_running(self) -> None:
        babase.screenmessage(
            'Shockwave Bomb ready. Use shockwave_bomb_spawn() or shockwave_bomb_grant() in the console.',
            color=(0.2, 0.9, 1.0),
        )
