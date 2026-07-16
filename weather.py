import requests
import time
from flask import Flask

# define default API endpoints (keyless)
DEBUG = True
WEATHER_URL = "https://api.weather.gov"
API_RATE = 250_000

def get_coords() -> None | tuple[float,float]:
    api = API_Handler()
    r = api.raw_call("http://ip-api.com/json/?fields=lat,lon")
    if r:
        return(r.json()["lat"], r.json()["lon"])
    else:
        return(None)

def current_time():
    return round(time.time() * 1_000_000)
 
_API_delay = current_time()

# Class to handle api calls
class API_Handler:
    api_url = None

    def __init__(self, url: str = ""):
        self.api_url = url

    # Call a raw url 
    def raw_call(self, url: str) -> None | requests.models.Response:
        # Rate limit the api call
        global _API_delay
        if current_time() - _API_delay < API_RATE:
            time.sleep(API_RATE / 1_000_000)

        # Debug message
        if DEBUG: print("Calling endpoint: " + url)


        # Make the call and verify
        try:
            _API_delay = current_time()
            response = requests.get(url)
            if response.status_code == 200:
                return response
            else: 
                print(f"CALL FAILED: {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            print(e)
            return None

    
    # formatted method for calling API endpoint (This only does a get request as I only ever need it to do that)
    def call(self, endpoint: list[str]) -> None | requests.models.Response:
        # Check the api url
        if self.api_url == "" or self.api_url == None:
            print("Cannot perform formatted api call :: api url is not configured or is blank")
            return None

        # Format endpoint
        full_endpoint = self.api_url + '/' + '/'.join(endpoint)

        # Make call 
        return(self.raw_call(full_endpoint))

# NOAA api interface class
class NOAA:
    handler = None

    # Constructor, defining handler
    def __init__(self):
        self.handler = API_Handler(WEATHER_URL)

    # Get NOAA data from coords
    # Point parameter is optional, if omitted one will be found using the IP address. (This is not reliable for cellular devices)
    # Returns: Points object
    # optional 'radio' parameter if true returns radio broadcast for the coordinates. TODO: radio breaks requests.json() call
    def get_point(self, point: None | tuple[float, float] = None, radio: bool = False) -> None | dict: 
        # Pull lat and lon from point if available, otherwise use IP address
        lat, lon = point if point else get_coords()

        # Call api handler
        r = self.handler.call(["points", f"{lat},{lon}", "radio" if radio else ""])
        return(r.json() if r else None)
    
    
    # Get NOAA forecast for given coords.  
    # Point parameter is optional, if omitted one will be found using the IP address. (This is not reliable for cellular devices)
    def point_forecast(self, point: None | tuple[float, float] = None) -> None | dict:
        # get JSON point data
        r = self.get_point(point, False)
        r = self.handler.raw_call(r["properties"]["forecast"])
        return r.json() if r else None
    
    # Get NOAA hourly forecast for given coords.  
    # Point parameter is optional, if omitted one will be found using the IP address. (This is not reliable for cellular devices)
    def point_forecast_hourly(self, point: None | tuple[float, float] = None) -> None | dict:
        # get JSON point data
        r = self.get_point(point, False)
        r = self.handler.raw_call(r["properties"]["forecastHourly"])
        return r.json() if r else None


app = Flask(__name__)

@app.route("/")
def root():
    return(
        '<h1>Weather</h1>'
        '<a href="/forecast"><button>Daily Forecast</button></a><a href="/hourly-forecast"><button>Hourly Forecast</button></a>'
        )

@app.route("/forecast")
def forecast():
    noaa = NOAA()
    r = noaa.point_forecast()
    periods = r["properties"]["periods"]

    items = []
    for p in periods:
        pop = p["probabilityOfPrecipitation"]["value"]
        pop = pop if pop is not None else 0
        items.append(
            f'<li><p>{p["name"]}</p><p>{p["temperature"]}{p["temperatureUnit"]} -- {pop}%</p></li>'
        )
    return(
        '<h1>Daily Forecast</h1>'
        '<a href="/"><button>back</button></a>'
        f"<ul>{"".join(items)}</ul>"
    )   

@app.route("/hourly-forecast")
def hourly_forecast():
    noaa = NOAA()
    r = noaa.point_forecast_hourly()
    periods = r["properties"]["periods"]

    items = []
    for p in periods:
        pop = p["probabilityOfPrecipitation"]["value"]
        pop = pop if pop is not None else 0
        items.append(
            f'<li><p>{p["startTime"]}</p><p>{p["temperature"]}{p["temperatureUnit"]} -- {pop}%</p></li>'
        )
    return(
        '<h1>Hourly Forecast</h1>'
        '<a href="/"><button>back</button></a>'
        f"<ul>{"".join(items)}</ul>"
    )

# Main execution
if __name__ == "__main__":
    noaa = NOAA()
    r = noaa.point_forecast()
    print(r if r else "Response failed")



