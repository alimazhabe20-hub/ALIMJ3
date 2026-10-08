"""Registry for public APIs that do not require an API key.

URLs are kept here instead of in handlers, making providers easy to replace
without changing the rest of the bot.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class APIProvider:
    name: str
    category: str
    base_url: str
    method: str = "GET"
    timeout: float = 10.0
    cache_ttl: float = 30.0
    params: dict[str, Any] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)
    description: str = ""

    @property
    def auth(self) -> str:
        """Compatibility marker: every registered provider is keyless."""
        return "No"


PROVIDERS: dict[str, APIProvider] = {
    "open_meteo_forecast": APIProvider(
        "open_meteo_forecast", "weather", "https://api.open-meteo.com/v1/forecast",
        cache_ttl=120, description="Current weather and forecast; no key required.",
    ),
    "open_meteo_geocoding": APIProvider(
        "open_meteo_geocoding", "geocoding", "https://geocoding-api.open-meteo.com/v1/search",
        cache_ttl=3600, description="City name to coordinates; no key required.",
    ),
    "frankfurter": APIProvider(
        "frankfurter", "currency", "https://api.frankfurter.app/latest",
        cache_ttl=60, description="Reference exchange rates; no key required.",
    ),
    "rest_countries": APIProvider(
        "rest_countries", "world", "https://restcountries.com/v3.1/name/{name}",
        cache_ttl=86400, description="Country information; no key required.",
    ),
    "rest_countries_all": APIProvider(
        "rest_countries_all", "world", "https://restcountries.com/v3.1/all",
        cache_ttl=86400, description="Country catalog; no key required.",
    ),
    "jokeapi": APIProvider(
        "jokeapi", "entertainment", "https://v2.jokeapi.dev/joke/Any",
        cache_ttl=30, description="Random jokes; no key required.",
    ),
    "quotable": APIProvider(
        "quotable", "quotes", "https://api.quotable.io/random",
        cache_ttl=30, description="Random quotes; no key required.",
    ),
    "open_library_search": APIProvider(
        "open_library_search", "books", "https://openlibrary.org/search.json",
        cache_ttl=300, description="Book search; no key required.",
    ),
    "gutendex": APIProvider(
        "gutendex", "books", "https://gutendex.com/books",
        cache_ttl=300, description="Public-domain books; no key required.",
    ),
    "musicbrainz": APIProvider(
        "musicbrainz", "music", "https://musicbrainz.org/ws/2/recording",
        cache_ttl=300, headers={"Accept": "application/json"},
        description="Music metadata search; no key required.",
    ),
    "itunes_search": APIProvider(
        "itunes_search", "music", "https://itunes.apple.com/search",
        cache_ttl=300, description="Music and media search; no key required.",
    ),
    "tvmaze_search": APIProvider(
        "tvmaze_search", "video", "https://api.tvmaze.com/search/shows",
        cache_ttl=300, description="TV show search; no key required.",
    ),
    "tvmaze_schedule": APIProvider(
        "tvmaze_schedule", "video", "https://api.tvmaze.com/schedule",
        cache_ttl=120, description="TV episode schedule by country/date; no key required.",
    ),
    "tvmaze_web_schedule": APIProvider(
        "tvmaze_web_schedule", "video", "https://api.tvmaze.com/schedule/web",
        cache_ttl=120, description="Streaming/web TV schedule by date; no key required.",
    ),
    "cinemeta_catalog_movies": APIProvider(
        "cinemeta_catalog_movies", "video", "https://cinemeta-catalogs.strem.io/top/catalog/movie/top.json",
        timeout=15, cache_ttl=600, description="Keyless movie catalog with IMDb IDs and ratings via Cinemeta.",
    ),
    "cinemeta_catalog_series": APIProvider(
        "cinemeta_catalog_series", "video", "https://cinemeta-catalogs.strem.io/top/catalog/series/top.json",
        timeout=15, cache_ttl=600, description="Keyless series catalog with IMDb IDs and ratings via Cinemeta.",
    ),
    "nager_date": APIProvider(
        "nager_date", "calendar", "https://date.nager.at/api/v3/PublicHolidays/{year}/{country_code}",
        cache_ttl=86400, description="Public holidays; no key required.",
    ),
    "onefindme_search": APIProvider(
        "onefindme_search", "shopping", "https://onefindme.com/api/search",
        timeout=12, cache_ttl=60,
        description="Keyless AliExpress product search with price, rating and orders.",
    ),
    "nominatim_search": APIProvider(
        "nominatim_search", "geocoding", "https://nominatim.openstreetmap.org/search",
        timeout=12, cache_ttl=3600,
        headers={"Accept": "application/json", "User-Agent": "ALIMJBot/3.0 (+public-api-hub; contact=admin)"},
        description="Worldwide forward geocoding; no API key required.",
    ),
    "nominatim_reverse": APIProvider(
        "nominatim_reverse", "geocoding", "https://nominatim.openstreetmap.org/reverse",
        timeout=12, cache_ttl=3600,
        headers={"Accept": "application/json", "User-Agent": "ALIMJBot/3.0 (+public-api-hub; contact=admin)"},
        description="Worldwide reverse geocoding; no API key required.",
    ),
    "coin_gecko_simple": APIProvider(
        "coin_gecko_simple", "crypto", "https://api.coingecko.com/api/v3/simple/price",
        cache_ttl=20, description="Crypto prices; no key required for public endpoint.",
    ),
    "ipma_weather": APIProvider(
        "ipma_weather", "weather", "https://api.ipma.pt/open-data/forecast/meteorology/cities/daily/{city_id}.json",
        cache_ttl=120, description="Portuguese weather data; no key required.",
    ),
}


# Additional keyless providers consolidated from the project's public-API catalog.
_EXTRA = [
    APIProvider("imdb_suggestion", "video", "https://v3.sg.media-imdb.com/suggestion/x/{query}.json", timeout=12, cache_ttl=300, description="Unofficial public IMDb suggestion endpoint; not an official IMDb API."),
    APIProvider("jikan_anime", "anime", "https://api.jikan.moe/v4/anime", timeout=15, cache_ttl=300),
    APIProvider("freetogame_games", "games", "https://www.freetogame.com/api/games", timeout=15, cache_ttl=300),
    APIProvider("spaceflight_news", "news", "https://api.spaceflightnewsapi.net/v4/articles/", timeout=15, cache_ttl=120),
    APIProvider("europe_pmc", "science", "https://www.ebi.ac.uk/europepmc/webservices/rest/search", timeout=15, cache_ttl=300, params={"format": "json"}),
    APIProvider("gbif", "science", "https://api.gbif.org/v1/species/match", timeout=12, cache_ttl=3600),
    APIProvider("clinical_trials", "health", "https://clinicaltrials.gov/api/v2/studies", timeout=15, cache_ttl=300),
    APIProvider("nvd_cves", "security", "https://services.nvd.nist.gov/rest/json/cves/2.0", timeout=15, cache_ttl=300),
    APIProvider("urlhaus", "security", "https://urlhaus-api.abuse.ch/v1/urls/recent/limit/10/", timeout=15, cache_ttl=120),
    APIProvider("data_usa", "open_data", "https://api.datausa.io/tesseract/data.jsonrecords", timeout=15, cache_ttl=600),
    APIProvider("fruityvice", "food", "https://www.fruityvice.com/api/fruit/all", timeout=12, cache_ttl=3600),
    APIProvider("cat_facts", "animals", "https://catfact.ninja/fact", timeout=10, cache_ttl=60),
    APIProvider("dog_facts", "animals", "https://dogapi.dog/api/v2/facts", timeout=10, cache_ttl=60),
    APIProvider("wiktionary", "dictionary", "https://en.wiktionary.org/w/api.php", timeout=12, cache_ttl=300, params={"action": "query", "format": "json", "prop": "extracts", "explaintext": 1}),
    APIProvider("datamuse", "text", "https://api.datamuse.com/words", timeout=10, cache_ttl=300),
    APIProvider("arbeitnow_jobs", "jobs", "https://www.arbeitnow.com/api/job-board-api", timeout=15, cache_ttl=300),
    APIProvider("packagist", "development", "https://packagist.org/search.json", timeout=12, cache_ttl=300),
    APIProvider("universities", "education", "http://universities.hipolabs.com/search", timeout=12, cache_ttl=3600),
    APIProvider("nhtsa_vpic", "vehicle", "https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValuesExtended/{vin}?format=json", timeout=15, cache_ttl=3600),
    APIProvider("nhtsa_models", "vehicle", "https://vpic.nhtsa.dot.gov/api/vehicles/GetModelsForMake/{make}?format=json", timeout=15, cache_ttl=3600),
    APIProvider("transitland", "transportation", "https://transit.land/api/v2/rest/stops", timeout=15, cache_ttl=300),
    APIProvider("hackernews", "social", "https://hacker-news.firebaseio.com/v0/topstories.json", timeout=10, cache_ttl=60),
]
for _provider in _EXTRA:
    PROVIDERS.setdefault(_provider.name, _provider)


# Stable aliases kept for older integrations/tests.
PROVIDER_ALIASES = {
    "open_meteo": "open_meteo_forecast",
}


def get_provider(name: str) -> APIProvider | None:
    name = str(name).strip().lower()
    name = PROVIDER_ALIASES.get(name, name)
    return PROVIDERS.get(str(name).strip().lower())


def list_providers(category: str | None = None) -> list[APIProvider]:
    values = list(PROVIDERS.values())
    if category:
        wanted = category.strip().lower()
        values = [item for item in values if item.category.lower() == wanted]
    return values
