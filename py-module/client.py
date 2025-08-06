from __future__ import annotations
from typing import Optional, Dict, Set, List, Collection

import aiohttp
import logging

from .httpclient import HTTPClient
from .school import School
from .user import ClientUser, User
from .errors import Forbidden, NotFound, BadRequest, HTTPException, NotSupported, MissingPermissions

__all__ = ["Client"]


class Client:
    """HSS API Client"""

    def __init__(self) -> None:
        self.is_ready: bool = False
        self._http: Optional[HTTPClient] = None
        self._schools: Dict[int, School] = {}
        self._users: Dict[int, User] = {}
        self._user_id_cache: Set[int] = set()
        self.user: Optional[ClientUser] = None

    async def setup(
        self,
        token: str,
        *,
        session: Optional[aiohttp.ClientSession] = None,
        fetch_all_schools: bool = True
    ) -> None:
        """
        Initialize the client by fetching user and (optionally) school data.

        Args:
            token: Your application's HSS API token.
            session: Optional aiohttp session. If None, a new session is created.
            fetch_all_schools: Whether to immediately load all accessible schools.

        Raises:
            Forbidden: If the provided token is invalid.
            ValueError: If the aiohttp session is already closed.
        """
        self._http = HTTPClient(token, session=session)
        self._schools.clear()
        self._users.clear()
        self._user_id_cache.clear()

        try:
            cu_data = await self._http.get_client_user()
        except Exception as e:
            logging.error(f"Failed to fetch client user info: {e}")
            raise

        self.user = ClientUser(
            self,
            int(cu_data["hid"]),
            cu_data["description"],
            cu_data["username"],
            int(cu_data["ownerId"])
        )
        self._users[self.user.id] = self.user
        self._user_id_cache.add(self.user.id)

        if fetch_all_schools:
            try:
                school_ids = await self._http.get_all_schools()
                for school_id in school_ids:
                    try:
                        raw_data = await self._http.get_school(int(school_id))
                        school = School.from_raw_data(self, raw_data)
                        self._schools[int(school_id)] = school
                    except Exception as e:
                        logging.warning(f"Failed to fetch school ID {school_id}: {e}")
            except Exception as e:
                logging.error(f"Failed to fetch school list: {e}")
                raise

        self.is_ready = True

    async def reload(self) -> None:
        """Re-initialize the client using the stored token and session."""
        if not self._http:
            raise RuntimeError("Client has not been initialized yet.")
        await self.setup(self._http.get_token(), session=self._http.session)

    @property
    def schools(self) -> Collection[School]:
        """Returns the cached schools."""
        return self._schools.values()

    def get_school(self, id: int) -> Optional[School]:
        """Returns a School by its ID, or None if not found."""
        return self._schools.get(id)

    @property
    def users(self) -> Collection[User]:
        """Returns the cached users (may not include all users)."""
        return self._users.values()

    def get_user(self, id: int) -> Optional[User]:
        """Returns a User by its ID, or None if not found."""
        return self._users.get(id)

    async def fetch_schools_from_discord(self, discord_id: int) -> List[School]:
        """
        Fetch schools associated with a Discord user ID.

        Args:
            discord_id: The Discord user's ID.

        Returns:
            A list of School objects.
        """
        try:
            data = await self._http.get_schools_from_discord_user(discord_id)
        except Exception as e:
            logging.error(f"Failed to fetch schools for Discord ID {discord_id}: {e}")
            return []

        schools: List[School] = []
        for school_id in data.get("registeredSchools", []):
            school = self.get_school(int(school_id))
            if school:
                schools.append(school)
        return schools

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._http and self._http.session:
            await self._http.session.close()