"""Discovery of the rooms from the areas."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smart_comfort.const import DOMAIN
from custom_components.smart_comfort.discovery import discover_rooms, merge


class House:
    """Areas, devices and entities of a test house."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self.entry = MockConfigEntry(domain="test")
        self.entry.add_to_hass(hass)
        self.areas = ar.async_get(hass)
        self.devices = dr.async_get(hass)
        self.entities = er.async_get(hass)

    def area(self, name: str) -> str:
        return self.areas.async_get_or_create(name).id

    def device(self, name: str, area: str, model: str | None = None) -> str:
        device = self.devices.async_get_or_create(
            config_entry_id=self.entry.entry_id, identifiers={("test", name)}, name=name, model=model
        )
        self.devices.async_update_device(device.id, area_id=area)
        return device.id

    def entity(
        self,
        domain: str,
        object_id: str,
        state: str,
        device: str | None = None,
        area: str | None = None,
        platform: str = "test",
        **attrs,
    ):
        entry = self.entities.async_get_or_create(
            domain, platform, object_id, suggested_object_id=object_id, device_id=device, config_entry=self.entry
        )
        if area:
            self.entities.async_update_entity(entry.entity_id, area_id=area)
        self.hass.states.async_set(entry.entity_id, state, attrs)
        return entry.entity_id


def build(hass: HomeAssistant) -> House:
    h = House(hass)
    living, bedroom, garden, hall = h.area("Living room"), h.area("Bedroom"), h.area("Garden"), h.area("Hall")
    station = h.device("Weather station", living)
    h.entity("sensor", "living_temperature", "21", station, device_class="temperature", state_class="measurement")
    h.entity("sensor", "living_humidity", "50", station, device_class="humidity")
    h.entity("sensor", "living_co2", "800", station, device_class="carbon_dioxide")
    h.entity("sensor", "living_noise", "40", station, device_class="sound_pressure")
    # An air quality sensor measuring the temperature only: the station wins.
    h.entity("sensor", "aq_temperature", "22", h.device("Air sensor", living), device_class="temperature")
    h.entity("binary_sensor", "living_window", "off", area=living, device_class="window")
    ac = h.device("Air conditioner", living)
    h.entity("climate", "living_ac", "off", ac, hvac_modes=["off", "cool", "heat"], fan_modes=["auto", "low", "silent"])
    h.entity("sensor", "ac_outdoor_temperature", "10", ac, device_class="temperature")
    h.entity("fan", "ac_fan", "off", ac)
    fan = h.device("Tower fan", living)
    h.entity("fan", "living_fan", "off", fan, preset_modes=["Natural Wind", "Straight Wind", "Smart"])
    h.entity("sensor", "fan_temperature", "23", fan, device_class="temperature")
    purifier = h.device("Air Purifier 4", living, model="zhimi.purifier")
    h.entity("fan", "living_purifier", "on", purifier, preset_modes=["auto"])
    h.entity("select", "living_purifier_mode", "automatic", purifier, options=["automatic", "manual"])
    h.entity("select", "living_purifier_brightness", "bright", purifier, options=["bright", "dim", "off"])
    h.entity("sensor", "purifier_pm25", "4", purifier, device_class="pm25")
    # Bedroom: a heating thermostat (no cooling) and a plain sensor.
    trv = h.device("Thermostat", bedroom)
    h.entity("climate", "bedroom_trv", "heat", trv, hvac_modes=["off", "heat"])
    h.entity("sensor", "trv_temperature", "17", trv, device_class="temperature")
    h.entity("sensor", "bedroom_temperature", "19", area=bedroom, device_class="temperature")
    h.entity("binary_sensor", "bedroom_door", "off", area=bedroom, device_class="door")
    h.entity("binary_sensor", "bedroom_motion", "off", area=bedroom, device_class="motion")
    h.entity(
        "fan",
        "bedroom_purifier",
        "on",
        h.device("Purificateur chambre", bedroom),
        preset_modes=["Auto", "Sleep", "Favorite"],
    )
    # Garden: outdoor. Hall: a door, no comfort sensor.
    h.entity("sensor", "garden_temperature", "9", area=garden, device_class="temperature")
    h.entity("sensor", "garden_noise", "50", area=garden, device_class="sound_pressure")
    h.entity("sensor", "garden_aqi", "42", area=garden, device_class="aqi")
    h.entity("binary_sensor", "hall_door", "off", area=hall, device_class="door")
    return h


async def test_discover_rooms(hass: HomeAssistant) -> None:
    build(hass)
    found = discover_rooms(hass)
    rooms = found.rooms
    # The garden: an outdoor place, with its sensors.
    assert found.outdoors == [
        {
            "name": "Garden",
            "area": "garden",
            "temperature": ["sensor.garden_temperature"],
            "air_quality": ["sensor.garden_aqi"],
            "noise": ["sensor.garden_noise"],
        }
    ]
    assert found.outdoor == found.outdoor_noise == found.outdoor_air == []
    by_name = {r["name"]: r for r in rooms}
    # Every area but the outdoor ones, even without a comfort sensor (the hall has a door only).
    assert sorted(by_name) == ["Bedroom", "Hall", "Living room"]
    assert by_name["Hall"] == {"name": "Hall", "area": "hall", "openings": ["binary_sensor.hall_door"]}
    living = by_name["Living room"]
    assert living["area"] == "living_room"
    assert living["temperature"] == "sensor.living_temperature"
    assert living["humidity"] == "sensor.living_humidity"
    assert living["co2"] == "sensor.living_co2"
    assert living["noise"] == "sensor.living_noise"
    assert living["openings"] == ["binary_sensor.living_window"]
    # The quietest fan mode for the night.
    assert living["climate"] == {"entity_id": "climate.living_ac", "night_fan_mode": "silent"}
    assert living["fans"] == [
        {
            "entity_id": "fan.living_fan",
            "preset": "Natural Wind",
            "off_preset": "Natural Wind",
            "open_preset": "Straight Wind",
        }
    ]
    assert living["purifiers"] == [
        {
            "entity_id": "fan.living_purifier",
            "mode_select": "select.living_purifier_mode",
            "open_mode": "manual",
            "closed_mode": "automatic",
        }
    ]
    bedroom = by_name["Bedroom"]
    assert bedroom["temperature"] == "sensor.bedroom_temperature"
    assert "climate" not in bedroom
    assert bedroom["openings"] == ["binary_sensor.bedroom_door"]
    assert bedroom["purifiers"] == [
        {
            "entity_id": "fan.bedroom_purifier",
            "open_preset": "Favorite",
            "closed_preset": "Auto",
            "night_preset": "Sleep",
        }
    ]


async def test_merge_keeps_what_is_set(hass: HomeAssistant) -> None:
    build(hass)
    found = discover_rooms(hass)
    options = {
        "outdoor_temperature": ["sensor.other", "sensor.garden_temperature"],
        "rooms": [
            {
                "name": "Living Room",
                "temperature": "sensor.aq_temperature",
                "fans": [{"entity_id": "fan.living_fan", "preset": "Smart"}],
            },
            {"name": "Office", "temperature": "sensor.office"},
        ],
    }
    merged, report = merge(options, found)
    assert report.added == ["Bedroom", "Hall"]
    assert report.updated == ["Living Room"]
    # The garden added as an outdoor place: its sensor leaves the top-level list, the other one stays.
    assert report.outdoors_added == ["Garden"]
    assert report.outdoor == []
    assert merged["outdoor_temperature"] == ["sensor.other"]
    assert merged["outdoors"][0]["temperature"] == ["sensor.garden_temperature"]
    living = merged["rooms"][0]
    assert living["temperature"] == "sensor.aq_temperature"  # kept
    assert living["co2"] == "sensor.living_co2"  # filled in
    # Device already there: its own setting kept, the missing ones filled in.
    assert living["fans"] == [
        {"entity_id": "fan.living_fan", "preset": "Smart", "off_preset": "Natural Wind", "open_preset": "Straight Wind"}
    ]
    assert "outdoor_noise" not in merged
    assert living["area"] == "living_room"
    assert merged["rooms"][1] == {"name": "Office", "temperature": "sensor.office"}
    assert merged["rooms"][2]["name"] == "Bedroom"
    # Discovering again changes nothing.
    again, report = merge(merged, found)
    assert again == merged
    assert report.added == report.updated == report.outdoors_added == report.outdoors_updated == []
    # The input isn't modified.
    assert options["rooms"][0] == {
        "name": "Living Room",
        "temperature": "sensor.aq_temperature",
        "fans": [{"entity_id": "fan.living_fan", "preset": "Smart"}],
    }


async def test_discover_command(hass: HomeAssistant, hass_ws_client) -> None:
    build(hass)
    entry = MockConfigEntry(domain=DOMAIN, title="Smart Comfort", data={}, options={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": f"{DOMAIN}/discover", "options": {}})
    msg = await client.receive_json()
    assert msg["success"], msg
    result = msg["result"]
    assert result["report"] == {
        "added": ["Bedroom", "Hall", "Living room"],
        "updated": [],
        "outdoors_added": ["Garden"],
        "outdoors_updated": [],
        "outdoor": [],
        "outdoor_noise": [],
        "outdoor_air": [],
    }
    assert result["options"]["outdoors"][0]["name"] == "Garden"
    # Not saved: the options are only saved by smart_comfort/config/save, which accepts them.
    assert entry.options == {}
    await client.send_json_auto_id({"type": f"{DOMAIN}/config/save", "options": result["options"]})
    msg = await client.receive_json()
    assert msg["success"], msg
    await hass.async_block_till_done()
    settings = entry.runtime_data.settings
    assert [r.name for r in settings.rooms] == ["Bedroom", "Hall", "Living room"]
    assert settings.outdoor == ("sensor.garden_temperature",)
    assert settings.outdoor_air == ("sensor.garden_aqi",)
    assert settings.outdoor_noise == ("sensor.garden_noise",)


async def test_outdoor_places(hass: HomeAssistant) -> None:
    """Outdoor modules of an indoor station (the terrace by their device), a city air quality index."""
    h = House(hass)
    living, terrace = h.area("Séjour"), h.area("Terrasse")
    h.entity("sensor", "station_temperature", "20", h.device("Station", living), device_class="temperature")
    for n in (1, 2):
        module = h.device(f"Station Météo Extérieur {n}", terrace, model="Smart Outdoor Module")
        h.entity("sensor", f"exterieur_{n}_temperature", "9", module, device_class="temperature")
        h.entity("sensor", f"exterieur_{n}_humidity", "81", module, device_class="humidity")
    # In no area: a module named outdoor, the city index (not its forecast nor pollen), other things.
    h.entity("sensor", "balcon_temperature", "8", device_class="temperature")
    atmo = h.device("Atmo France", None)
    h.entity("sensor", "atmo_qualite_globale_rennes", "3", atmo, platform="atmofrance")
    h.entity("sensor", "atmo_qualite_globale_rennes_j_1", "2", atmo, platform="atmofrance")
    h.entity("sensor", "atmo_qualite_globale_pollen_rennes", "1", atmo, platform="atmofrance")
    h.entity("sensor", "air_quality", "0", platform="spook")
    h.entity("sensor", "nas_temperature", "50", device_class="temperature")
    # The outdoor unit of an air conditioner: inside the house, not the outdoor temperature.
    ac = h.device("Climatiseur", living)
    h.entity("climate", "climatiseur", "off", ac, hvac_modes=["off", "cool"])
    h.entity("sensor", "climatiseur_outdoor_temperature", "10", ac, device_class="temperature")
    hass.states.async_set("weather.home", "sunny", {"temperature": 8})
    found = discover_rooms(hass)
    assert [r["name"] for r in found.rooms] == ["Séjour"]
    assert found.outdoors == [
        {
            "name": "Terrasse",
            "area": "terrasse",
            "temperature": ["sensor.exterieur_1_temperature", "sensor.exterieur_2_temperature"],
        }
    ]
    assert found.outdoor == ["sensor.balcon_temperature"]
    assert found.outdoor_air == ["sensor.atmo_qualite_globale_rennes"]
    # Set before: the terrace sensor moves to its place, the weather entity stays, the place is completed.
    options = {
        "outdoor_temperature": ["weather.home", "sensor.exterieur_1_temperature"],
        "outdoors": [{"name": "Terrasse", "temperature": ["sensor.exterieur_1_temperature"]}],
    }
    merged, report = merge(options, found)
    assert merged["outdoor_temperature"] == ["weather.home", "sensor.balcon_temperature"]
    assert merged["outdoors"] == [
        {
            "name": "Terrasse",
            "area": "terrasse",
            "temperature": ["sensor.exterieur_1_temperature", "sensor.exterieur_2_temperature"],
        }
    ]
    assert merged["outdoor_air_quality"] == ["sensor.atmo_qualite_globale_rennes"]
    assert report.outdoors_updated == ["Terrasse"]
    assert report.outdoor == ["sensor.balcon_temperature"]
    assert report.outdoor_air == ["sensor.atmo_qualite_globale_rennes"]


async def test_outdoor_weather(hass: HomeAssistant) -> None:
    """Without an outdoor temperature sensor, the weather entity: only when nothing is set."""
    h = House(hass)
    h.entity("sensor", "living_temperature", "20", area=h.area("Living room"), device_class="temperature")
    hass.states.async_set("weather.home", "sunny", {"temperature": 8})
    found = discover_rooms(hass)
    assert found.outdoor == ["weather.home"]
    merged, report = merge({}, found)
    assert merged["outdoor_temperature"] == ["weather.home"]
    assert report.outdoor == ["weather.home"]
    for options in (
        {"outdoor_temperature": ["sensor.mine"]},
        {"outdoors": [{"name": "Garden", "temperature": ["sensor.garden"]}]},
    ):
        merged, report = merge(options, found)
        assert "weather.home" not in merged.get("outdoor_temperature", [])
        assert report.outdoor == []
