"""Get data from the SickGear Instance API."""
from aiohttp import ClientError, ClientSession, ClientTimeout
import asyncio


class SickApi:
    """Core SickGear API Object."""

    # Shamelessly ripped from the pysabnzbd module

    def __init__(
        self, base_url, api_key, web_root=None, session=None, timeout=5
    ) -> None:
        """Initialize the connection to the SickGear Server."""
        if web_root is not None:
            web_root = "{}/".format(web_root.strip("/"))
        else:
            web_root = ""

        self.sickgear_url = base_url
        self.scheduler = {}
        self.shows_stats = {}
        self.shows_upcoming = {}
        self.shows_upcoming["shows_today"] = {}
        self.shows_upcoming["shows_soon"] = {}
        self.shows_upcoming["shows_later"] = {}
        self.shows_upcoming["shows_missed"] = {}
        self._api_url = "{}/{}/{}".format(base_url.rstrip("/"), "api", api_key)
        self._timeout = timeout

        if session is None:
            self._session = ClientSession()
            self._cleanup_session = True
        else:
            self._session = session
            self._cleanup_session = False

    def __del__(self):
        """Cleanup the session if it was created here."""
        if self._cleanup_session:
            self._session.loop.run_until_complete(self._session.close())

    async def _call(self, params):
        """Call the SickGear API."""
        if self._session.closed:
            raise SickApiException("Session already closed")
        parameters = {**params}
        try:
            resp = await self._session.get(
                self._api_url,
                params=parameters,
                timeout=ClientTimeout(self._timeout),
            )
            data = await resp.json()
            if data.get("status", True) is False:
                self._handle_error(data, params)
            else:
                return data
        except ClientError as exc:
            raise SickApiException("Unable to communicate with SickGear API") from exc
        except asyncio.TimeoutError as exc:
            raise SickApiException("SickGear API request timed out") from exc

    async def refresh_data(self):
        """Refresh the cached SickGear data."""
        scheduler = await self.get_scheduler()
        shows_stats = await self.get_shows_stats()
        upcoming = await self.get_upcoming_shows()
        self.scheduler = scheduler
        self.shows_stats = shows_stats
        self.shows_upcoming["shows_today"] = upcoming["today"]
        self.shows_upcoming["shows_later"] = upcoming["later"]
        self.shows_upcoming["shows_missed"] = upcoming["missed"]
        self.shows_upcoming["shows_soon"] = upcoming["soon"]

    async def check_available(self):
        """Test the connection to the SickGear Server."""
        params = {"cmd": "sg"}
        await self._call(params)
        return True

    async def get_scheduler(self):
        """Fetch the SickGear Scheduler Config."""
        params = {"cmd": "sg.checkscheduler"}
        scheduler = await self._call(params)
        return scheduler.get("data")

    async def get_shows_stats(self):
        """Fetch the SickGear Shows Stats."""
        params = {"cmd": "sg.shows.stats"}
        stats = await self._call(params)
        return stats.get("data")

    async def get_upcoming_shows(self):
        """Fetch the SickGear Upcoming Shows."""
        params = {"cmd": "sg.future", "sort": "date"}
        stats = await self._call(params)
        return stats.get("data")

    def _handle_error(self, data, params):
        """Handle an error response from the SickGear API."""
        error = data.get("error", "API call failed")
        mode = params.get("mode")
        raise SickApiException(error, mode=mode)


class SickApiException(Exception):
    """Base exception class for all SABnzbd API errors."""

    def __init__(self, message, mode=None) -> None:
        """Initiate Exception."""
        self.message = message
        self.mode = mode

    def __str__(self):
        """Set Exception Value."""
        if self.mode is not None:
            msg_format = "{}: calling api endpoint '{}'"
        else:
            msg_format = "{}"
        return msg_format.format(
            self.message, self.mode if self.mode is not None else ""
        )
