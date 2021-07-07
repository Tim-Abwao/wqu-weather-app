from io import StringIO

import pandas as pd
import plotly.express as px
import requests
import requests_cache

# requests_cache configuration
FLUSH_PERIOD = 10 * 60  # 10 minutes in seconds
requests_cache.install_cache(expire_after=FLUSH_PERIOD)


def process_weather_forecast(ip_address):
    """Create a message with weather and location-related information.

    Parameters
    ----------
    ip_address : str
        A single IPv4/IPv6 address, or a domain name.

    Returns
    -------
    dict
        A dictionary of weather and location information.
    """
    location = get_location(ip_address)
    weather_info = get_weather_info(
        location["lat"], location["lon"], location["timezone"]
    )
    temp_C = float(
        weather_info["current_weather"]["Air temperature"].rstrip("°C")
    )
    temp_F = convert_to_fahr(temp_C)

    return dict(
        graphs=plot_forecast(weather_info["temp_time_series"]),
        headline=(
            f"It's {temp_C :.0f}°C ({temp_F :.0f}°F) in {location['city']},"
            f" {location['country']} right now."
        ),
        ip_address=ip_address,
        data=weather_info,
    )


def get_location(ip_address):
    """Get city, country, latitude, longitude and timezone information for a
    location given an IP address.

    Parameters
    ----------
    ip_address : str
        A single IPv4/IPv6 address, or a domain name.

    Returns
    -------
    dict
        A dictionary of location details.
    """
    location_info = requests.get(
        f"http://ip-api.com/json/{ip_address}",
        headers={"User-Agent": "wqu_weather_app"},
    ).json()

    return {
        key: location_info[key]
        for key in ("city", "country", "lat", "lon", "timezone")
    }


def get_weather_info(lat, lon, timezone):
    """Get weather forecast data for a given location.

    Parameters
    ----------
    lat, lon : int, float
        Latitude and longitude values, respectively.
    timezone : str
        Time zone information e.g. 'GMT'.

    Returns
    -------
    dict
        A dictionary of various weather metrics, including icons.
    """
    raw_data = requests.get(
        "https://api.met.no/weatherapi/locationforecast/2.0/compact",
        params={"lat": lat, "lon": lon},
        headers={"User-Agent": "wqu_weather_app"},
    ).json()["properties"]["timeseries"]

    return dict(
        current_weather=get_current_weather(
            raw_data[0]["data"]["instant"]["details"]
        ),
        weather_icons=get_weather_icons(raw_data[0]["data"]),
        temp_time_series=get_temperature_time_series(raw_data, timezone),
    )


def get_current_weather(current_weather):
    """Get the current values for air, cloud and wind metrics.

    Parameters
    ----------
    current_weather : dict
        Weather information for the current hour.

    Returns
    -------
    dict
        Parsed weather information for the current hour.
    """
    return {
        "Air pressure": f"{current_weather['air_pressure_at_sea_level']}hPa",
        "Air temperature": f"{current_weather['air_temperature']}°C",
        "Cloud area fraction": f"{current_weather['cloud_area_fraction']}%",
        "Relative humidity": f"{current_weather['relative_humidity']}%",
        "Wind direction (from)": f"{current_weather['wind_from_direction']}°",
        "Wind speed": f"{current_weather['wind_speed']}m/s",
    }


def get_weather_icons(icon_info):
    """Fetch the appropriate icons to illustrate the weather for the next
    few hours.

    Parameters
    ----------
    icon_info : dict
        Weather information for the current hour.

    Returns
    -------
    dict
        Weather forecast icons for the next 1, 6 and 12 hours.
    """
    return {
        f"{time}h": icon_info[f"next_{time}_hours"]["summary"]["symbol_code"]
        for time in [1, 6, 12]
    }


def get_temperature_time_series(weather_info, timezone):
    """Get air temperature forecasts as a time-zone-aware pandas Series.

    Parameters
    ----------
    weather_info : list of dicts
        Time series data with hourly weather forecasts.
    timezone : str
        Time zone information e.g. 'GMT'.

    Returns
    -------
    pandas.Series
        A pandas series of air temperature forecasts.
    """
    time_info = [entry["time"] for entry in weather_info]
    temp_info = [
        entry["data"]["instant"]["details"]["air_temperature"]
        for entry in weather_info
    ]
    temp_data = pd.Series(temp_info, index=time_info)

    # Make the index time-zone aware
    temp_data.index = pd.to_datetime(temp_data.index).tz_convert(timezone)

    return temp_data


def plot_forecast(temp_data):
    """Get graphs of air temperature forecasts.

    Parameters
    ----------
    temp_data: pandas.Series
        Air temperature time series data.

    Returns
    -------
    24h_forecast_graph : io.StringIO
        A line graph of the 24hr air temperature forecast.
    10d_forecast_graph : io.StringIO
        A bar graph of the 10-day max & min temperature forecast.
    """
    temp24H = temp_data[:24]
    fig = px.line(
        y=temp24H, x=temp24H.index.astype(str), title="24 Hour Forecast"
    )
    # Rename axes labels and disable zoom
    fig.update_xaxes(title_text="Time", fixedrange=True)
    fig.update_yaxes(title_text="Air temperature in °C", fixedrange=True)

    fig.update_layout(paper_bgcolor="azure", plot_bgcolor="azure")
    fig.update_traces(
        hovertemplate="<b>Time</b>: %{x}<br><b>Temp</b>: %{y}°C<br>"
    )
    # Write graph to text buffer
    temp24H_graph = StringIO()
    fig.write_html(
        temp24H_graph,
        full_html=False,
        include_plotlyjs="https://cdn.plot.ly/plotly-basic-1.58.2.min.js",
    )

    temp10D = temp_data.resample("1D").agg(["max", "min"])
    fig2 = px.bar(
        temp10D,
        color_discrete_sequence=["orangered", "cyan"],
        barmode="group",
        title="10 Day Forecast",
    )
    # Rename axes labels and disable zoom
    fig2.update_xaxes(title_text="Day", fixedrange=True)
    fig2.update_yaxes(title_text="Air temperature in °C", fixedrange=True)

    fig2.update_layout(paper_bgcolor="azure", plot_bgcolor="azure")
    fig2.update_traces(
        hovertemplate="<b>Date</b>: %{x}<br><b>Temp</b>: %{y}°C<br>"
    )
    # Write graph to text buffer
    temp10D_graph = StringIO()
    fig2.write_html(
        temp10D_graph,
        full_html=False,
        include_plotlyjs="https://cdn.plot.ly/plotly-basic-1.58.2.min.js",
    )
    return temp24H_graph, temp10D_graph


def convert_to_fahr(temp_C):
    """Convert temperature from degrees Celsius to Fahrenheit.

    Parameters
    ----------
    temp_C : int, float
        The temperature value in degrees Celcius/centigrade.

    Returns
    -------
    int, float
        The temperature in degrees Fahrenheit.
    """
    return 9 / 5 * temp_C + 32


def get_external_IP_address():
    """Get the client's IP address via a GET request to an API service.

    Returns
    -------
    str
        An IPv4 or IPv6 address.
    """
    return requests.get(
        "https://ident.me/", headers={"User-Agent": "wqu_weather_app"}
    ).text


if __name__ == "__main__":
    import sys

    [
        print(f"{key} --> {value}")
        for key, value in process_weather_forecast(sys.argv[1]).items()
    ]  # e.g. python utils.py 8.8.8.8
