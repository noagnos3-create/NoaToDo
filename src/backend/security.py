# NoaToDo, a local encrypted to-do app for Windows.
# Copyright (C) 2026 Noa Gnos
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Sicherheits-Kern der Phase 8 (Bauplan B.7/B.8, Gates G6-G9, G14-G18, G25, G28, G31-G33, G35).

Enthaelt:
- Schluesselableitung (G15/G18): Pepper-Bindung per HKDF-Extract (V2a), Argon2id
  mit den festen N11.4.3-Parametern, HKDF-SHA256 mit den U18-Labels.
- Das ``tasks.db.enc``-Dateiformat samt atomarem Schreiben (G16/V1: Header als
  AEAD-``associated_data``, Probe-Entschluesselung vor der ``.bak``-Rotation,
  Plattenplatz-Pruefung, frische Nonce).
- Den DPAPI-Pepper im Windows Credential Manager (G18, via ``keyring``).
- RAM-Schluessel-Hygiene (G25) + ``VirtualLock`` (G31, Best-Effort).
- Die Tresor-Sitzung (:class:`Vault`): Unlock/Wrap/Write-back nach N11.9
  (Arbeitskopie ist IMMER eine SQLCipher-verschluesselte Datei, nie Klartext;
  Spike-Ergebnis N11.18: sqlcipher3 hat kein ``serialize``, der
  Arbeitsdatei-Fallback ist verbindlich; Schnappschuesse via ``VACUUM INTO``).
- Die Entsperr-Rate-Limit-Leiter samt Persistenz (B.8.4 / N11.4.1).
- Den G17-Write-back (debounced ~3 s, harte Kappe 30 s, U20).
- Den Auto-Sperr-Timer (B.8.3 / N11.4.2: monotone Uhr, eigener Thread,
  fail-safe, nur ``activity_ping`` zaehlt).
- Die EINE ``teardown(reason)``-Sequenz (B.8.5 / N11.11, Gate G35).

Sicherheitsregeln: Schluessel und Pepper leben nur als ``bytearray`` im RAM und
werden vor dem Verwerfen genullt (G25); nichts davon erreicht je Logs,
Exceptions oder das Frontend (G29).
"""
from __future__ import annotations

import ctypes
import hashlib
import hmac
import os
import secrets
import shutil
import struct
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from . import config as config_module

# ---------------------------------------------------------------------------
# Konstanten des .enc-Formats (G16) und der KDF (N11.4.3, U17/U18)
# ---------------------------------------------------------------------------
MAGIC = b"NOA1"
FORMAT_VERSION = 1
KDF_TYPE_ARGON2ID = 2          # argon2.low_level.Type.ID hat den Wert 2
ARGON2_VERSION = 0x13

# Fest verdrahtete Soll-Parameter (N11.4.3, die einzige Wahrheit; G8 konkret).
ARGON2_MEMORY_COST = 262144    # KiB = 256 MiB
ARGON2_TIME_COST = 3
ARGON2_PARALLELISM = 4
ARGON2_HASH_LEN = 32
SALT_LEN = 16
NONCE_LEN = 12

# Akzeptanzbereich gegen einen aufgeblaehten Header (DoS-Schutz, N11.4.3):
# wird VOR jeder Allokation geprueft; ausserhalb -> Kopf gilt als unlesbar.
MEMORY_COST_MIN = 64 * 1024    # 64 MiB in KiB
MEMORY_COST_MAX = 512 * 1024   # 512 MiB in KiB
TIME_COST_MIN, TIME_COST_MAX = 1, 10
PARALLELISM_MIN, PARALLELISM_MAX = 1, 16

# HKDF-Labels (U18, fest und versioniert; Aenderung erhoeht die v-Nummer).
INFO_AES = b"noatodo/aes-key/v1"
INFO_CHACHA = b"noatodo/chacha-key/v1"

# Header-Layout (alles little-endian):
#   magic(4) fmt(1) kdf_type(1) kdf_version(1) memory_cost(u32) time_cost(u32)
#   parallelism(u32) hash_len(1) salt(16) nonce(12)  -> 48 Bytes
_HEADER_FMT = "<4sBBBIIIB16s12s"
HEADER_LEN = struct.calcsize(_HEADER_FMT)

# Reserve fuer die Plattenplatz-Pruefung vor dem Wrap (G16/V1 Punkt 3).
_FREE_SPACE_RESERVE = 16 * 1024 * 1024

# DPAPI-Pepper (G18): 32 Byte im Windows Credential Manager, nie in der DB.
KEYRING_SERVICE = "NoaToDo"
KEYRING_PEPPER_NAME = "pepper"

# Rate-Limit-Leiter (B.8.4): 3 freie Versuche, dann je 2 Versuche pro Stufe.
LADDER_FREE_TRIES = 3
LADDER_TRIES_PER_STAGE = 2
LADDER_DURATIONS = (10, 30, 60, 300, 900, 1800, 3600, 18000, 36000)
RETRY_PAUSE_SECONDS = 2        # Zwangspause nach JEDEM Fehlversuch

# G17-Write-back (U20): debounced ~3 s, harte Kappe 30 s.
WRITEBACK_DEBOUNCE_SECONDS = 3.0
WRITEBACK_HARD_CAP_SECONDS = 30.0


class VaultError(Exception):
    """Tresor fehlt/beschaedigt/unlesbar -> Katalog-Code ``vault`` (N6)."""


class WrongPassphrase(Exception):
    """AEAD-Tag schlaegt fehl -> Katalog-Code ``passphrase`` (N6 Fall 3)."""


class RateLimited(Exception):
    """Leiter laeuft -> Katalog-Code ``rate_limited`` (+ retry_in)."""

    def __init__(self, retry_in: int):
        super().__init__("rate limited")
        self.retry_in = retry_in


# ---------------------------------------------------------------------------
# RAM-Schluessel-Hygiene (G25) + VirtualLock (G31, Best-Effort)
# ---------------------------------------------------------------------------

def _virtual_lock(buf: bytearray, lock: bool) -> None:
    """Sperrt/entsperrt einen Puffer gegen das Auslagern (G31, Best-Effort).

    Dokumentierte Grenze (G31): haelt Schluessel NICHT aus ``hiberfil.sys``
    oder Crash-Dumps heraus; dagegen hilft nur BitLocker (B.10.4).
    """
    if not buf:
        return
    try:
        raw = (ctypes.c_char * len(buf)).from_buffer(buf)
        fn = ctypes.windll.kernel32.VirtualLock if lock else ctypes.windll.kernel32.VirtualUnlock
        fn(ctypes.addressof(raw), ctypes.c_size_t(len(buf)))
    except Exception:
        pass


def zeroize(buf: bytearray | None) -> None:
    """Puffer nullen und (falls gesperrt) wieder freigeben (G25/G31)."""
    if buf is None:
        return
    _virtual_lock(buf, False)
    for i in range(len(buf)):
        buf[i] = 0


def _locked_bytearray(data: bytes) -> bytearray:
    """Kopiert Schluesselmaterial in ein per VirtualLock gesperrtes bytearray."""
    buf = bytearray(data)
    _virtual_lock(buf, True)
    return buf


# ---------------------------------------------------------------------------
# DPAPI-Pepper (G18)
# ---------------------------------------------------------------------------

def get_pepper(create: bool = False) -> bytearray:
    """Liest (oder erzeugt) den 32-Byte-Pepper aus dem Credential Manager.

    Fehlender Pepper bei ``create=False`` ist ein ``vault``-Fall (die Datei
    ist ohne ihn nicht zu oeffnen, N6). Kein Recovery-Export (N11.3).
    """
    import keyring

    try:
        stored = keyring.get_password(KEYRING_SERVICE, KEYRING_PEPPER_NAME)
    except Exception:
        raise VaultError("credential manager unavailable")
    if stored:
        try:
            raw = bytes.fromhex(stored)
        except ValueError:
            raise VaultError("pepper damaged")
        if len(raw) != 32:
            raise VaultError("pepper damaged")
        return _locked_bytearray(raw)
    if not create:
        raise VaultError("pepper missing")
    raw = secrets.token_bytes(32)
    try:
        keyring.set_password(KEYRING_SERVICE, KEYRING_PEPPER_NAME, raw.hex())
    except Exception:
        raise VaultError("credential manager write failed")
    return _locked_bytearray(raw)


def pepper_exists() -> bool:
    """Nur fuers ehrliche Status-Modal (G22): liegt ein Pepper im Store?"""
    import keyring

    try:
        return bool(keyring.get_password(KEYRING_SERVICE, KEYRING_PEPPER_NAME))
    except Exception:
        return False


def delete_pepper() -> None:
    """Pepper entfernen (nur Killswitch/Reset, N11.11 Schritt 8)."""
    import keyring

    try:
        keyring.delete_password(KEYRING_SERVICE, KEYRING_PEPPER_NAME)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Header (G16) und Schluesselableitung (G15/G18)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class KdfParams:
    memory_cost: int = ARGON2_MEMORY_COST
    time_cost: int = ARGON2_TIME_COST
    parallelism: int = ARGON2_PARALLELISM
    hash_len: int = ARGON2_HASH_LEN


def pack_header(params: KdfParams, salt: bytes, nonce: bytes) -> bytes:
    return struct.pack(
        _HEADER_FMT, MAGIC, FORMAT_VERSION, KDF_TYPE_ARGON2ID, ARGON2_VERSION,
        params.memory_cost, params.time_cost, params.parallelism,
        params.hash_len, salt, nonce,
    )


def parse_header(blob: bytes) -> tuple[KdfParams, bytes, bytes, bytes]:
    """Header parsen UND gegen den Akzeptanzbereich pruefen (N11.4.3).

    Laeuft ohne Passphrase und ohne Argon2 (N6 Schritt 2). Jede Abweichung
    (Magic, Version, Typ, Bereich) macht den Kopf "unlesbar" -> VaultError,
    KEIN Argon2-Lauf (DoS-Schutz gegen aufgeblaehte Parameter).
    Rueckgabe: (params, salt, nonce, header_bytes fuer die AEAD-AAD).
    """
    if len(blob) < HEADER_LEN:
        raise VaultError("header truncated")
    header = blob[:HEADER_LEN]
    magic, fmt, kdf_type, kdf_ver, mem, t, par, hlen, salt, nonce = struct.unpack(
        _HEADER_FMT, header
    )
    if magic != MAGIC or fmt != FORMAT_VERSION:
        raise VaultError("bad magic/version")
    if kdf_type != KDF_TYPE_ARGON2ID or kdf_ver != ARGON2_VERSION:
        raise VaultError("bad kdf type/version")
    if not (MEMORY_COST_MIN <= mem <= MEMORY_COST_MAX):
        raise VaultError("memory_cost out of range")
    if not (TIME_COST_MIN <= t <= TIME_COST_MAX):
        raise VaultError("time_cost out of range")
    if not (PARALLELISM_MIN <= par <= PARALLELISM_MAX):
        raise VaultError("parallelism out of range")
    if hlen != ARGON2_HASH_LEN:
        raise VaultError("hash_len invalid")
    return KdfParams(mem, t, par, hlen), salt, nonce, header


def derive_keys(passphrase: str, pepper: bytearray | bytes, salt: bytes,
                params: KdfParams) -> tuple[bytearray, bytearray]:
    """Passphrase -> (aes_key, chacha_key) nach G15/G18 (V2a, U18).

    Konstruktion: ``ikm = HKDF-Extract(salt=pepper, ikm=passphrase_utf8)``
    (per Definition HMAC-SHA256(key=pepper, msg=passphrase)), dann
    Argon2id(ikm, salt) -> ein 32-Byte-Master-Secret, daraus zweimal
    HKDF-SHA256 (salt=None bewusst, U18; feste info-Labels v1). Alle
    Zwischenwerte werden sofort genullt; ein Allokationsfehler wird als
    ``MemoryError`` weitergereicht (N11.4.3: eigener Code ``memory``, nie
    "falsche Passphrase", treibt die Leiter nicht voran).
    """
    from argon2.low_level import Type, hash_secret_raw
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF

    ikm = bytearray(hmac.new(bytes(pepper), passphrase.encode("utf-8"),
                             hashlib.sha256).digest())
    _virtual_lock(ikm, True)
    master: bytearray | None = None
    try:
        try:
            master = _locked_bytearray(hash_secret_raw(
                secret=bytes(ikm), salt=salt,
                time_cost=params.time_cost, memory_cost=params.memory_cost,
                parallelism=params.parallelism, hash_len=params.hash_len,
                type=Type.ID, version=ARGON2_VERSION,
            ))
        except MemoryError:
            raise
        except Exception as exc:
            # argon2-cffi meldet Allokationsfehler als HashingError o.ae.;
            # alles, was nach Speicher aussieht, ist der memory-Fall.
            if "alloc" in str(exc).lower() or "memory" in str(exc).lower():
                raise MemoryError(str(exc)) from exc
            raise
        aes = _locked_bytearray(HKDF(
            algorithm=hashes.SHA256(), length=32, salt=None, info=INFO_AES,
        ).derive(bytes(master)))
        chacha = _locked_bytearray(HKDF(
            algorithm=hashes.SHA256(), length=32, salt=None, info=INFO_CHACHA,
        ).derive(bytes(master)))
        return aes, chacha
    finally:
        zeroize(ikm)
        zeroize(master)


# ---------------------------------------------------------------------------
# Container lesen / atomar schreiben (G16, V1)
# ---------------------------------------------------------------------------

def read_container(enc_path: str) -> tuple[KdfParams, bytes, bytes, bytes, bytes]:
    """Datei lesen und Kopf pruefen (N6 Schritte 1/2, ohne Passphrase).

    Rueckgabe: (params, salt, nonce, header_bytes, ciphertext).
    """
    if not os.path.exists(enc_path):
        raise VaultError("vault file missing")
    try:
        with open(enc_path, "rb") as fh:
            blob = fh.read()
    except OSError:
        raise VaultError("vault file unreadable")
    params, salt, nonce, header = parse_header(blob)
    ciphertext = blob[HEADER_LEN:]
    if not ciphertext:
        raise VaultError("vault body missing")
    return params, salt, nonce, header, ciphertext


def unwrap(chacha_key: bytearray, header: bytes, nonce: bytes,
           ciphertext: bytes) -> bytes:
    """AEAD-Entschluesselung mit dem Header als associated_data (V1).

    Ein Tag-Fehler ist die implizite Passphrase-Pruefung (G15):
    -> :class:`WrongPassphrase`. Es gibt keinen gespeicherten Hash.
    """
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

    try:
        return ChaCha20Poly1305(bytes(chacha_key)).decrypt(nonce, ciphertext, header)
    except InvalidTag:
        raise WrongPassphrase()


def wrap_to_file(enc_path: str, chacha_key: bytearray, params: KdfParams,
                 salt: bytes, inner_image: bytes) -> None:
    """Inneres (SQLCipher-)Image atomar als ``tasks.db.enc`` schreiben (G16/V1).

    Reihenfolge: Plattenplatz pruefen -> frische Nonce -> verschluesseln
    (Header als AAD) -> ``.tmp`` schreiben + fsync -> ``.tmp`` PROBEWEISE
    entschluesseln -> bestehende Datei nach ``.bak`` rotieren (genau eine
    Generation) -> ``os.replace``. Scheitert irgendwas davor, bleibt der alte
    Stand unangetastet (VaultError -> Code ``vault``).
    """
    from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

    directory = os.path.dirname(os.path.abspath(enc_path))
    os.makedirs(directory, exist_ok=True)
    try:
        free = shutil.disk_usage(directory).free
    except OSError:
        free = None
    if free is not None and free < len(inner_image) + _FREE_SPACE_RESERVE:
        raise VaultError("not enough disk space")

    nonce = os.urandom(NONCE_LEN)
    header = pack_header(params, salt, nonce)
    ciphertext = ChaCha20Poly1305(bytes(chacha_key)).encrypt(nonce, inner_image, header)

    tmp = enc_path + ".tmp"
    with open(tmp, "wb") as fh:
        fh.write(header)
        fh.write(ciphertext)
        fh.flush()
        os.fsync(fh.fileno())

    # Probe-Entschluesselung des frischen .tmp VOR der .bak-Rotation (V1):
    # zwei fehlerhafte Schreibzyklen duerfen nie beide Generationen zerstoeren.
    try:
        with open(tmp, "rb") as fh:
            blob = fh.read()
        _p2, _s2, n2, h2 = parse_header(blob)
        ChaCha20Poly1305(bytes(chacha_key)).decrypt(n2, blob[HEADER_LEN:], h2)
    except Exception:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise VaultError("verify of fresh container failed")

    bak = enc_path + ".bak"
    if os.path.exists(enc_path):
        try:
            if os.path.exists(bak):
                os.remove(bak)
            os.replace(enc_path, bak)
        except OSError:
            # Rotation gescheitert: lieber ohne frisches .bak weiterschreiben
            # als den Write-back zu verlieren (Best-Effort, G16-Geist).
            pass
    os.replace(tmp, enc_path)


def secure_delete(path: str) -> None:
    """Datei bestmoeglich ueberschreiben, dann entlinken (G33-Pfad).

    Ehrliche Grenze (B.10/G33): auf SSDs mit Wear-Leveling ist das
    Ueberschreiben nicht garantiert; die letzte Deckung bleibt BitLocker
    bzw. beim Tresor der DPAPI-Pepper. Nie ein blankes ``os.remove`` fuer
    Tresor-/Altdaten-Bestaende verwenden.
    """
    try:
        if not os.path.exists(path):
            return
        size = os.path.getsize(path)
        with open(path, "r+b") as fh:
            step = 1024 * 1024
            written = 0
            while written < size:
                chunk = min(step, size - written)
                fh.write(b"\x00" * chunk)
                written += chunk
            fh.flush()
            os.fsync(fh.fileno())
        os.remove(path)
    except OSError:
        try:
            os.remove(path)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Rate-Limit-Leiter (B.8.4 / N11.4.1)
# ---------------------------------------------------------------------------

def ladder_stage(fails: int) -> tuple[int, int]:
    """DIE eine deterministische Stufenfunktion (N11.4.1).

    Aus ``fails`` allein folgen (stage, duration): die ersten 3 Fehlversuche
    sind frei (nur die 2-s-Pause), ab dem 4. greift die Leiter, je 2 weitere
    Fehlversuche schalten eine Stufe hoch (4-5 -> 10 s, 6-7 -> 30 s, ...,
    Deckel 10 h).
    """
    if fails <= LADDER_FREE_TRIES:
        return 0, 0
    idx = (fails - LADDER_FREE_TRIES - 1) // LADDER_TRIES_PER_STAGE
    idx = min(idx, len(LADDER_DURATIONS) - 1)
    return idx + 1, LADDER_DURATIONS[idx]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _td(seconds: float):
    from datetime import timedelta

    return timedelta(seconds=seconds)


def _parse_ts(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


class RateLimiter:
    """Persistierte Entsperr-Leiter (N11.4.1): zwei Uhren, persist-before-verify.

    - Innerhalb der Sitzung zaehlt ``time.monotonic()`` (immun gegen
      Uhr-Verstellen); ueber Neustarts die Wanduhr (UTC-Zeitstempel in
      ``config.json``). Die Restzeit ist immer ``max(monoton, wanduhr)``.
    - Rueckwaerts-Sprung (jetzt < locked_at) oder widerspruechliche Werte:
      die laufende Sperrzeit startet KOMPLETT neu, nie verkuerzt.
    - ``register_fail()`` schreibt synchron und atomar, BEVOR Argon2/AEAD
      laufen (persist-before-verify); nur ``reset()`` (Erfolg) raeumt auf.
    """

    def __init__(self, get_config: Callable[[], dict],
                 save_config: Callable[[dict], None]):
        self._get_config = get_config
        self._save_config = save_config
        self._mono_until: float | None = None   # monotone Sperr-Deadline
        self._boot_check_done = False

    def _rl(self) -> dict:
        cfg = self._get_config()
        rl = cfg.get("unlock_ratelimit")
        if not isinstance(rl, dict):
            rl = {"fails": 0, "stage": 0, "next_try_at": None,
                  "locked_at": None, "duration": 0}
            cfg["unlock_ratelimit"] = rl
        return rl

    def _persist(self) -> None:
        self._save_config(self._get_config())

    def _boot_reconcile(self, rl: dict) -> None:
        """Beim ersten Blick nach dem Start: Wanduhr-Zustand pruefen (N11.4.1).

        Rueckwaerts-Sprung oder widerspruechliche Werte -> Sperrzeit komplett
        neu starten. ``stage`` ist nur Spiegel von ``fails``; widersprechen
        sie sich, gilt der hoehere Wert (zugunsten der Sperre).
        """
        if self._boot_check_done:
            return
        self._boot_check_done = True
        fails = max(int(rl.get("fails") or 0), 0)
        stage_from_fails, duration = ladder_stage(fails)
        stored_stage = int(rl.get("stage") or 0)
        if stored_stage > stage_from_fails:
            # Hoeherer gespeicherter Stand gewinnt (zugunsten der Sperre):
            # fails passend anheben, bis die Stufenfunktion ihn erreicht.
            while ladder_stage(fails)[0] < stored_stage and fails < 10_000:
                fails += 1
            stage_from_fails, duration = ladder_stage(fails)
        rl["fails"] = fails
        rl["stage"] = stage_from_fails
        rl["duration"] = duration
        now = _utcnow()
        locked_at = _parse_ts(rl.get("locked_at"))
        next_try = _parse_ts(rl.get("next_try_at"))
        if duration <= 0:
            rl["next_try_at"] = None
            rl["locked_at"] = None
            self._persist()
            return
        if locked_at is None or next_try is None or now < locked_at:
            # Fehlende/widerspruechliche Werte oder Uhr zurueckgestellt:
            # Sperre in voller Laenge neu starten, nie verkuerzen.
            rl["locked_at"] = now.isoformat()
            rl["next_try_at"] = (now + _td(duration)).isoformat()
            self._mono_until = time.monotonic() + duration
            self._persist()
            return
        remaining = (next_try - now).total_seconds()
        if remaining > 0:
            self._mono_until = time.monotonic() + remaining
        self._persist()

    def remaining(self) -> int:
        """Verbleibende Sperrzeit in Sekunden (0 = Versuch erlaubt)."""
        rl = self._rl()
        self._boot_reconcile(rl)
        wall = 0.0
        next_try = _parse_ts(rl.get("next_try_at"))
        if next_try is not None:
            wall = (next_try - _utcnow()).total_seconds()
        mono = 0.0
        if self._mono_until is not None:
            mono = self._mono_until - time.monotonic()
        return max(0, int(max(wall, mono) + 0.999))

    def register_fail(self) -> int:
        """Fehlversuch zaehlen und SOFORT persistieren (vor der Pruefung!).

        Liefert die ab jetzt geltende Wartezeit in Sekunden (mindestens die
        2-s-Zwangspause). Wird VOR Argon2id/AEAD gerufen und vor jeder
        Antwort ans Frontend (persist-before-verify, N11.4.1).
        """
        rl = self._rl()
        self._boot_reconcile(rl)
        rl["fails"] = int(rl.get("fails") or 0) + 1
        stage, duration = ladder_stage(rl["fails"])
        rl["stage"] = stage
        rl["duration"] = duration
        wait = max(duration, RETRY_PAUSE_SECONDS)
        now = _utcnow()
        rl["locked_at"] = now.isoformat()
        rl["next_try_at"] = (now + _td(wait)).isoformat()
        self._mono_until = time.monotonic() + wait
        self._persist()
        return wait

    def undo_last_fail(self) -> None:
        """Einen gezaehlten Fehlversuch zuruecknehmen (kein Rateversuch, N6).

        Fuer die Faelle, die NICHT die Leiter vorantreiben (``memory``,
        ``vault``/fehlender Pepper): weil persist-before-verify den Versuch
        schon gezaehlt hat, wird er hier wieder abgezogen, sobald feststeht,
        dass es kein Passphrase-Rateversuch war.
        """
        rl = self._rl()
        rl["fails"] = max(0, int(rl.get("fails") or 0) - 1)
        stage, duration = ladder_stage(rl["fails"])
        rl["stage"] = stage
        rl["duration"] = duration
        if duration <= 0:
            rl["next_try_at"] = None
            rl["locked_at"] = None
            self._mono_until = None
        self._persist()

    def reset(self) -> None:
        """Nur der Erfolg raeumt auf (erfolgreiches unlock)."""
        rl = self._rl()
        rl["fails"] = 0
        rl["stage"] = 0
        rl["duration"] = 0
        rl["next_try_at"] = None
        rl["locked_at"] = None
        self._mono_until = None
        self._persist()

    def reset_memory(self) -> None:
        """Nur den fluechtigen Zustand zuruecksetzen, OHNE zu persistieren.

        Fuer ``reset_vault``: dort ist die ``config.json`` schon geloescht;
        ein persistierendes ``reset()`` wuerde ueber ``_load_config`` eine neue
        Konfig mit leerem ``vault_path`` zurueckschreiben und den naechsten Boot
        faelschlich in ``vault_error`` statt ins Onboarding schicken.
        """
        self._mono_until = None
        self._boot_check_done = False


# ---------------------------------------------------------------------------
# Tresor-Sitzung (N11.9-Fallback: verschluesselte Arbeitsdatei, VACUUM INTO)
# ---------------------------------------------------------------------------

def work_dir() -> str:
    """Benutzerprivater Arbeitsordner fuer die SQLCipher-Arbeitsdatei.

    Unter ``%LOCALAPPDATA%\\NoaToDo\\work``: benutzerprivat (Profil-ACL),
    lokal, vom Store-Python-Redirect transparent mitumgeleitet (V8). Die
    Dateien darin sind IMMER AES-Chiffretext (N11.9), nie Klartext.
    """
    local = os.environ.get("LOCALAPPDATA") or os.path.join(
        os.path.expanduser("~"), "AppData", "Local"
    )
    return os.path.join(local, "NoaToDo", "work")


def cleanup_work_dir() -> None:
    """Verwaiste Arbeitsdateien eines Absturzes kommentarlos entfernen (N11.9).

    KEINE Crash-Recovery aus der Arbeitsdatei: nach einem Absturz wird sie
    verworfen, nie gelesen; Wiederherstellungsstand ist ausschliesslich das
    zuletzt geschriebene ``tasks.db.enc`` (bzw. dessen ``.bak``, G16).
    """
    d = work_dir()
    if not os.path.isdir(d):
        return
    for name in os.listdir(d):
        secure_delete(os.path.join(d, name))


class Vault:
    """Die entsperrte Tresor-Sitzung: Schluessel, Arbeitsdatei, Write-back.

    Lebenszyklus: :meth:`Vault.unlock` bzw. :meth:`Vault.create` liefern eine
    offene Sitzung; :meth:`flush` schreibt den Stand als ``tasks.db.enc``
    (G16/G17); :meth:`close` schliesst die DB, entfernt die Arbeitsdatei und
    nullt die Schluessel (G25). Danach ist das Objekt tot.
    """

    def __init__(self, enc_path: str, aes_key: bytearray, chacha_key: bytearray,
                 params: KdfParams, salt: bytes):
        self.enc_path = enc_path
        self._aes_key = aes_key
        self._chacha_key = chacha_key
        self.params = params
        self.salt = salt
        self.work_path: str | None = None
        self.db = None          # backend.db.Database, gesetzt in _open_db
        self._closed = False

    # -- Aufbau ------------------------------------------------------------
    @classmethod
    def unlock(cls, enc_path: str, passphrase: str) -> "Vault":
        """Voller Entsperr-Vorgang (N6-Reihenfolge, Krypto-Teil).

        Kopf-Pruefungen (Datei fehlt / Kopf unlesbar -> VaultError) laufen
        VOR der teuren Ableitung; erst danach Argon2id + AEAD (Tag-Fehler ->
        WrongPassphrase). Die Rate-Limit-Buchfuehrung macht der Aufrufer
        (persist-before-verify, N11.4.1).
        """
        params, salt, nonce, header, ciphertext = read_container(enc_path)
        pepper = get_pepper(create=False)
        aes_key = chacha_key = None
        try:
            aes_key, chacha_key = derive_keys(passphrase, pepper, salt, params)
        finally:
            zeroize(pepper)
        try:
            inner = unwrap(chacha_key, header, nonce, ciphertext)
        except WrongPassphrase:
            zeroize(aes_key)
            zeroize(chacha_key)
            raise
        vault = cls(enc_path, aes_key, chacha_key, params, salt)
        vault._open_db(inner)
        return vault

    @classmethod
    def create(cls, enc_path: str, passphrase: str) -> "Vault":
        """Neuen, leeren Tresor anlegen (N11.13 / create_vault-Krypto).

        Frisches Salt, Soll-Parameter, Pepper wird bei Bedarf erzeugt (G18).
        Der Riegel gegen das Ueberschreiben eines bestehenden Tresors liegt
        beim Aufrufer (N11.15.6). Schreibt sofort ein gueltiges
        ``tasks.db.enc``.
        """
        params = KdfParams()
        salt = os.urandom(SALT_LEN)
        pepper = get_pepper(create=True)
        try:
            aes_key, chacha_key = derive_keys(passphrase, pepper, salt, params)
        finally:
            zeroize(pepper)
        vault = cls(enc_path, aes_key, chacha_key, params, salt)
        vault._open_db(None)
        vault.flush()
        return vault

    @classmethod
    def from_keys(cls, enc_path: str, aes_key: bytearray, chacha_key: bytearray,
                  params: KdfParams, salt: bytes, inner_image: bytes) -> "Vault":
        """Sitzung aus bereits abgeleiteten Schluesseln + entpacktem Image bauen.

        Fuer den rate-limit-bewussten Entsperr-Pfad in ``api.py``, der die
        Krypto-Schritte selbst interleavt (Header lesen -> Leiter zaehlen ->
        ableiten -> entpacken), damit ``vault``/``memory`` die Leiter nicht
        vorantreiben (N6/N11.4.1). ``aes_key``/``chacha_key`` gehen in den
        Besitz der Sitzung ueber.
        """
        vault = cls(enc_path, aes_key, chacha_key, params, salt)
        vault._open_db(inner_image)
        return vault

    def matches_aes(self, candidate: bytes) -> bool:
        """Konstante-Zeit-Vergleich gegen den aktuellen Schicht-1-Schluessel.

        Fuer ``change_passphrase``: die alte Passphrase gilt als korrekt, wenn
        die aus ihr (mit dem aktuellen Salt/Pepper) abgeleiteten AES-Bytes dem
        offenen Schluessel entsprechen. Kein gespeicherter Hash noetig.
        """
        return hmac.compare_digest(bytes(self._aes_key), bytes(candidate))

    def _open_db(self, inner_image: bytes | None) -> None:
        """Arbeitsdatei schreiben und SQLCipher-Verbindung oeffnen (N11.9/G7)."""
        from . import db as db_module

        d = work_dir()
        os.makedirs(d, exist_ok=True)
        self.work_path = os.path.join(d, f"work-{secrets.token_hex(8)}.db")
        if inner_image:
            with open(self.work_path, "wb") as fh:
                fh.write(inner_image)
                fh.flush()
                os.fsync(fh.fileno())
        self.db = db_module.Database(self.work_path, bytes(self._aes_key))
        self.db.seed_if_empty()

    # -- Write-back (G17) --------------------------------------------------
    def snapshot_inner(self) -> bytes:
        """Konsistenten AES-verschluesselten Schnappschuss der DB ziehen.

        ``VACUUM INTO`` schreibt eine mit demselben Schluessel verschluesselte,
        konsistente Kopie, ohne die Verbindung zu schliessen (Spike N11.18).
        Die Schnappschuss-Datei ist reiner Chiffretext und wird sofort wieder
        sicher entfernt.
        """
        if self.db is None or self.work_path is None:
            raise VaultError("vault not open")
        snap = self.work_path + ".snap"
        secure_delete(snap)
        self.db.conn.commit()
        # Pfad als Literal: VACUUM INTO bindet keine Parameter zuverlaessig;
        # der Pfad stammt von uns (token_hex), nie aus Nutzereingaben.
        self.db.conn.execute("VACUUM INTO '%s'" % snap.replace("'", "''"))
        try:
            with open(snap, "rb") as fh:
                return fh.read()
        finally:
            secure_delete(snap)

    def flush(self) -> None:
        """Aktuellen Stand atomar als ``tasks.db.enc`` persistieren (G16/G17)."""
        if self._closed:
            return
        inner = self.snapshot_inner()
        wrap_to_file(self.enc_path, self._chacha_key, self.params, self.salt, inner)

    def rewrap_with(self, aes_key: bytearray, chacha_key: bytearray,
                    params: KdfParams, salt: bytes) -> None:
        """Passphrase-Wechsel (N11.3 a-d): DB umschluesseln + neu wrappen.

        (a) frisches Salt kommt vom Aufrufer, die frische Nonce von
            ``wrap_to_file``;
        (b) der Pepper bleibt (macht der Aufrufer: er leitet mit dem
            BESTEHENDEN Pepper ab);
        (c) die ``.bak``-Generation wird sofort mit dem NEUEN Schluessel neu
            geschrieben; nichts bleibt mit der alten Passphrase lesbar, der
            alte Stand geht ueber den Secure-Delete-Pfad;
        (d) params sind die aktuellen Soll-Werte (KDF-Upgrade-Pfad).
        """
        if self.db is None:
            raise VaultError("vault not open")
        self.db.rekey(bytes(aes_key))
        old_aes, old_chacha = self._aes_key, self._chacha_key
        self._aes_key, self._chacha_key = aes_key, chacha_key
        self.params, self.salt = params, salt
        zeroize(old_aes)
        zeroize(old_chacha)
        inner = self.snapshot_inner()
        # Reihenfolge datensicher (kein Fenster ohne gueltige .enc): erst das
        # neue Primaer atomar schreiben (G16 rotiert dabei das ALTE, noch
        # alt-lesbare Primaer nach .bak); scheitert das (z.B. Platte voll),
        # bleibt der alte, intakte Stand als .enc/.bak stehen (VaultError ->
        # change_passphrase liefert vault, kein Datenverlust). Erst NACH dem
        # erfolgreichen Schreiben die alt-lesbare .bak sicher wegraeumen und
        # durch eine mit dem NEUEN Schluessel ersetzen (N11.3 c: nach dem
        # Wechsel ist nichts mehr mit der alten Passphrase entschluesselbar).
        wrap_to_file(self.enc_path, self._chacha_key, self.params, self.salt, inner)
        bak = self.enc_path + ".bak"
        secure_delete(bak)
        try:
            shutil.copyfile(self.enc_path, bak)
        except OSError:
            # Frische .bak konnte nicht angelegt werden: hinnehmbar (die
            # G16-Absturzsicherung fehlt dann bis zum naechsten Write-back),
            # aber NICHTS bleibt alt-lesbar (die alte .bak ist sicher geloescht).
            pass

    # -- Abbau -------------------------------------------------------------
    def close(self) -> None:
        """DB schliessen, Arbeitsdatei entfernen, Schluessel nullen (G25)."""
        if self._closed:
            return
        self._closed = True
        if self.db is not None:
            try:
                self.db.close()
            except Exception:
                pass
            self.db = None
        if self.work_path:
            secure_delete(self.work_path)
            secure_delete(self.work_path + ".snap")
            self.work_path = None
        zeroize(self._aes_key)
        zeroize(self._chacha_key)


# ---------------------------------------------------------------------------
# G17-Write-back: debounced ~3 s, harte Kappe 30 s (U20)
# ---------------------------------------------------------------------------

class WriteBack:
    """Debounced Write-back der Arbeits-DB nach ``tasks.db.enc``.

    ``notify_change()`` nach jeder Mutation; geschrieben wird ~3 s nach der
    letzten Aenderung, spaetestens aber 30 s nach der ERSTEN ungesicherten
    Aenderung, auch bei Dauereingabe (U20). ``flush_sync()`` schreibt sofort
    und synchron (teardown Schritt 4; Fehler propagieren dort hart).
    """

    def __init__(self, flush: Callable[[], None]):
        self._flush = flush
        self._lock = threading.Lock()
        self._timer: threading.Timer | None = None
        self._dirty_since: float | None = None
        self._stopped = False

    def notify_change(self) -> None:
        with self._lock:
            if self._stopped:
                return
            now = time.monotonic()
            if self._dirty_since is None:
                self._dirty_since = now
            if self._timer is not None:
                self._timer.cancel()
            elapsed = now - self._dirty_since
            delay = min(WRITEBACK_DEBOUNCE_SECONDS,
                        max(0.0, WRITEBACK_HARD_CAP_SECONDS - elapsed))
            self._timer = threading.Timer(delay, self._fire)
            self._timer.daemon = True
            self._timer.start()

    def _fire(self) -> None:
        with self._lock:
            if self._stopped:
                return
            self._timer = None
            self._dirty_since = None
        try:
            self._flush()
        except Exception:
            # Ein fehlgeschlagener Hintergrund-Write-back darf die App nicht
            # reissen; der naechste Versuch kommt mit der naechsten Mutation,
            # und der Teardown-Flush (Schritt 4) behandelt Fehler hart.
            pass

    def cancel(self) -> bool:
        """Timer abbrechen; True, wenn noch eine Aenderung aussteht."""
        with self._lock:
            pending = self._dirty_since is not None or self._timer is not None
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
            self._dirty_since = None
            return pending

    def flush_sync(self) -> None:
        """Sofort synchron schreiben (teardown Schritt 4; Fehler propagieren)."""
        self.cancel()
        self._flush()

    def stop(self) -> None:
        with self._lock:
            self._stopped = True
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
            self._dirty_since = None


# ---------------------------------------------------------------------------
# Auto-Sperre (B.8.3 / N11.4.2)
# ---------------------------------------------------------------------------

class AutoLock:
    """Fail-safe Auto-Sperr-Timer: monotone Uhr, eigener Thread.

    Der Backend-Timer ist die alleinige Autoritaet: ``ping()`` (nur
    ``activity_ping``, G13-gesperrt kein Ping) stempelt ``last_activity`` auf
    die Backend-Uhr, kann sie nie in die Zukunft setzen und den Timer nicht
    abschalten. Bleiben Pings aus (Frontend haengt/tot/XSS-stillgelegt),
    sperrt die App trotzdem. ``timeout_min`` kommt live aus den Settings
    (``autoLock``, 0 = nie); ein kleinerer Wert greift beim naechsten Tick.
    Der Timer laeuft unabhaengig von Fensterfokus und Windows-Sitzung
    (N11.8.4), also auch bei per Win+L gesperrtem PC.
    """

    def __init__(self, get_timeout_min: Callable[[], int],
                 on_timeout: Callable[[], None]):
        self._get_timeout_min = get_timeout_min
        self._on_timeout = on_timeout
        self._last_activity = time.monotonic()
        self._enabled = False
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, daemon=True,
                                        name="noatodo-autolock")
        self._thread.start()

    def ping(self) -> None:
        """Nur activity_ping ruft das; stempelt auf die MONOTONE Backend-Uhr."""
        self._last_activity = time.monotonic()

    def arm(self) -> None:
        """Beim Entsperren/Tresor-Oeffnen: jetzt als letzte Aktivitaet setzen."""
        self._last_activity = time.monotonic()
        self._enabled = True

    def disarm(self) -> None:
        """Beim Sperren/Beenden: Timer ruht (kein zweiter teardown-Ausloeser)."""
        self._enabled = False

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        while not self._stop.wait(1.0):
            if not self._enabled:
                continue
            try:
                timeout_min = int(self._get_timeout_min())
            except Exception:
                timeout_min = 0
            if timeout_min <= 0:
                continue
            if time.monotonic() - self._last_activity > timeout_min * 60:
                self._enabled = False
                try:
                    self._on_timeout()
                except Exception:
                    pass


# ---------------------------------------------------------------------------
# Die EINE teardown(reason)-Sequenz (B.8.5 / N11.11, Gate G35)
# ---------------------------------------------------------------------------

Reason = str  # "lock" | "autolock" | "quit" | "panic_finish" | "killswitch" | "reset" | "atexit"

# Prozessweite Idempotenz-Sperre (Schritt 1): hoechstens EIN Durchlauf
# gleichzeitig; ein begonnenes Beenden gewinnt immer gegen ein begonnenes
# Sperren (_teardown_terminal bleibt bei Beenden-Gruenden endgueltig gesetzt).
_teardown_lock = threading.Lock()
_teardown_terminal = False


class TeardownAbort(Exception):
    """Schritt 4 (Debounce-Flush) ist gescheitert: Sequenz abgebrochen,
    N6-Fehlerbildschirm statt Datenverlust (N11.11.2 Schritt 4). Es wird
    nicht weitergewischt und nicht beendet; die ``.bak``-Generation bleibt
    unangetastet."""


class Session:
    """Verdrahtungspunkt zwischen teardown, Api, Vault und main.py.

    main.py und api.py setzen die Felder; :func:`run_teardown` ruft nur die
    Methoden hier. So bleibt die Sequenz EINE Funktion (G35), und die
    nativen Schritte 9 bis 11 orchestriert main.py anhand von
    ``next_state``, ohne einen zweiten Ablauf zu bauen.
    """

    def __init__(self):
        self.vault: Vault | None = None
        self.writeback: WriteBack | None = None
        self.autolock: AutoLock | None = None
        self.api = None                 # backend.api.Api (von main.py gesetzt)
        self.next_state = "exit"        # von run_teardown gesetzt:
                                        # "locked" | "onboarding" | "exit"
        self.deferred_native = False    # autolock bei offenem Dialog (N11.11.5)

    # -- Schritt-Implementierungen (nur von run_teardown gerufen) ----------
    def resolve_dialogs(self, cancel: bool) -> None:
        if self.api is not None:
            try:
                self.deferred_native = self.api._resolve_native_dialog(cancel)
            except Exception:
                self.deferred_native = False

    def freeze(self) -> None:
        if self.api is not None:
            self.api.locked = True

    def autolock_disarm(self) -> None:
        if self.autolock is not None:
            self.autolock.disarm()

    def flush_sync(self) -> None:
        if self.writeback is not None:
            self.writeback.flush_sync()
        elif self.vault is not None:
            self.vault.flush()

    def clear_clipboard(self) -> None:
        if self.api is not None:
            self.api._clear_own_clipboard()

    def close_vault(self) -> None:
        if self.writeback is not None:
            self.writeback.stop()
            self.writeback = None
        if self.vault is not None:
            self.vault.close()
            self.vault = None
        if self.api is not None:
            self.api._detach_db()

    def drop_volatile(self) -> None:
        if self.api is not None:
            self.api._drop_volatile()

    def delete_vault_files(self) -> None:
        """Killswitch/Reset (B.8.7): reine Datei-Operation, keine Schluessel.

        Loescht ``tasks.db.enc`` + ``.bak`` + ``.tmp`` (Secure-Delete-Pfad),
        raeumt den Arbeitsordner, entfernt den DPAPI-Pepper und die Konfig
        (Vault-Eintrag + Rate-Limit, U6/U21). Es wird KEIN ``seeded``-Marker
        geschrieben; der naechste Start ist mangels Datei automatisch ein
        leerer Erststart. Dokumentierter Nebeneffekt (U21): mit dem Pepper
        sterben auch alle frueher kopierten ``.enc``-Staende endgueltig.
        """
        enc = self._enc_path()
        if enc:
            for suffix in ("", ".bak", ".tmp", ".oldkey"):
                secure_delete(enc + suffix)
        cleanup_work_dir()
        delete_pepper()
        config_module.delete_config()

    def _enc_path(self) -> str | None:
        if self.vault is not None:
            return self.vault.enc_path
        try:
            cfg = config_module.load_config()
        except config_module.ConfigDamaged:
            return None
        return cfg.get("vault_path") if cfg else None


def run_teardown(reason: Reason, session: Session) -> bool:
    """Die verbindliche Soll-Sequenz aus N11.11.2, Schritte 1 bis 8.

    Die nativen Schritte 9 bis 11 (Ansicht abbauen, ``PROFILE_DIR`` wischen,
    Funk wiederherstellen, Prozess-Ende) fuehrt ``main.py`` NACH diesem
    Aufruf anhand von ``session.next_state`` aus; sie gehoeren zur selben
    Sequenz (main baut keinen eigenen Ablauf, G35). Rueckgabe True =
    Sequenz gelaufen, False = verworfen (Idempotenz, Schritt 1).

    Wirft :class:`TeardownAbort`, wenn der synchrone G17-Flush scheitert
    (einzige nicht-Best-Effort-Stelle, Schritt 4).
    """
    global _teardown_terminal
    terminal = reason in ("quit", "panic_finish", "killswitch", "atexit")
    if not _teardown_lock.acquire(blocking=False):
        return False
    try:
        if _teardown_terminal:
            return False        # Beenden laeuft schon; alles Weitere verworfen
        if terminal:
            _teardown_terminal = True

        # Schritt 2: offene native Dialoge aufloesen (U5/N11.11.5). Jeder
        # Grund ausser autolock bricht den Dialog sofort ab; autolock laeuft
        # bis Schritt 7 durch und parkt nur die nativen Schritte 9 bis 11
        # (session.deferred_native; main.py wartet auf die Dialog-Rueckkehr).
        session.resolve_dialogs(cancel=(reason != "autolock"))

        # Schritt 3: Eingaben einfrieren (G13): ab jetzt liefert jede
        # Bridge-Methode ausserhalb der Allowlist {"error": "locked"}.
        session.freeze()

        # Schritt 4: Timer stoppen, ausstehende Aenderungen SYNCHRON
        # persistieren (G17/G16). Entfaellt ersatzlos fuer killswitch/reset
        # (die Datei stirbt gleich). Scheitert das Schreiben, bricht die
        # Sequenz ab (kein Datenverlust; .bak bleibt unangetastet).
        session.autolock_disarm()
        if reason not in ("killswitch", "reset"):
            try:
                session.flush_sync()
            except Exception as exc:
                if terminal:
                    _teardown_terminal = False
                raise TeardownAbort(str(exc)) from exc

        # Ab hier best effort (N11.11.2 Fehlerregel): kein gescheiterter
        # Schritt darf die folgenden verhindern.

        # Schritt 5: Clipboard leeren, wenn es noch App-Inhalt traegt (V7/G23).
        try:
            session.clear_clipboard()
        except Exception:
            pass

        # Schritt 6: DB schliessen, Arbeitsdatei sicher entfernen.
        # Schritt 7: Schluessel nullen (G25) + fluechtige RAM-Puffer
        # verwerfen (Undo-Puffer N11.2.1, Fehler-Ringpuffer G29).
        try:
            session.close_vault()
        except Exception:
            pass
        try:
            session.drop_volatile()
        except Exception:
            pass

        # Schritt 8: nur killswitch/reset loeschen Dateien + Pepper (U21),
        # erst NACH 6/7 (keine offenen Handles, Prozess ist schluessellos).
        if reason in ("killswitch", "reset"):
            try:
                session.delete_vault_files()
            except Exception:
                pass

        session.next_state = {
            "lock": "locked", "autolock": "locked",
            "reset": "onboarding",
        }.get(reason, "exit")
        return True
    finally:
        _teardown_lock.release()
