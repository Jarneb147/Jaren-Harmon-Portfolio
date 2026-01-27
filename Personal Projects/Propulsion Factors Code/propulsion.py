import math
import requests # This library allows Python to browse the web

class LiveEnvironmentalData:
    def __init__(self, location, api_key, dist_to_coast_km):
        self.location = location
        self.api_key = api_key
        # Note: Free weather APIs don't tell you distance to ocean, 
        # so we keep this as a manual input for now.
        self.dist_to_coast_km = dist_to_coast_km 
        self.lat = 0
        self.lon = 0

    def get_live_data(self):
        print(f"\n--- Connecting to Satellite for {self.location}... ---")
        
        # 1. Fetch Basic Weather (Temperature, Pressure, Humidity, Wind)
        base_url = "http://api.openweathermap.org/data/2.5/weather"
        params = {
            'q': self.location,
            'appid': self.api_key,
            'units': 'metric' # Returns Temp in Celsius
        }
        
        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status() # Check for connection errors
            w_data = response.json()
            
            # Save Lat/Lon for the Pollution Call
            self.lat = w_data['coord']['lat']
            self.lon = w_data['coord']['lon']
            
            # Extract Wind Direction (Degrees)
            # We convert degrees to rough cardinal direction for our logic
            deg = w_data['wind']['deg']
            wind_dir = "Offshore" # Default assumption
            # Simplified logic: If wind is roughly East (blowing inland on US East coast)
            # In a real app, you'd calculate this based on specific geography
            if 45 <= deg <= 135: wind_dir = "Onshore" 

        except Exception as e:
            print(f"Error fetching weather: {e}")
            return None

        # 2. Fetch Pollution Data (PM2.5)
        # This requires a separate call using the Lat/Lon we just found
        poll_url = "http://api.openweathermap.org/data/2.5/air_pollution"
        poll_params = {'lat': self.lat, 'lon': self.lon, 'appid': self.api_key}
        
        pm2_5 = 0
        try:
            p_response = requests.get(poll_url, params=poll_params)
            p_data = p_response.json()
            # OpenWeatherMap gives PM2.5 in μg/m3
            pm2_5 = p_data['list'][0]['components']['pm2_5']
        except Exception as e:
            print(f"Error fetching pollution: {e}")

        # 3. Package the data for our Engine Calculator
        return {
            "temp_c": w_data['main']['temp'],
            "pressure_hpa": w_data['main']['pressure'],
            "humidity": w_data['main']['humidity'],
            "wind_speed_mph": w_data['wind']['speed'] * 2.237, # Convert m/s to mph
            "wind_direction": wind_dir,
            "dist_to_coast_km": self.dist_to_coast_km,
            "pm2_5": pm2_5
        }

class PropulsionCalculator:
    def __init__(self, data):
        self.data = data
        
    def calculate_vapor_pressure(self):
        temp_c = self.data['temp_c']
        es = 6.112 * math.exp((17.67 * temp_c) / (temp_c + 243.5))
        vapor_pressure = es * (self.data['humidity'] / 100.0)
        return vapor_pressure

    def calculate_air_density(self):
        temp_k = self.data['temp_c'] + 273.15
        pressure_pa = self.data['pressure_hpa'] * 100
        vapor_pressure_pa = self.calculate_vapor_pressure() * 100
        dry_pressure = pressure_pa - vapor_pressure_pa
        R_dry = 287.05
        R_vapor = 461.495
        rho = (dry_pressure / (R_dry * temp_k)) + (vapor_pressure_pa / (R_vapor * temp_k))
        return rho

    def analyze_salt_risk(self):
        dist = self.data['dist_to_coast_km']
        wind_dir = self.data['wind_direction']
        speed = self.data['wind_speed_mph']
        
        risk_score = 0
        if dist < 10: risk_score += 2 
        if wind_dir == "Onshore": risk_score += 2 
        if speed > 15: risk_score += 1 
        
        if risk_score >= 4: return "HIGH (Active Corrosion Risk)"
        elif risk_score >= 2: return "MODERATE"
        else: return "LOW"

    def analyze_pollution_impact(self):
        pm = self.data['pm2_5']
        if pm > 150: return 0.95, f"CRITICAL (PM2.5: {pm})"
        elif pm > 50: return 0.98, f"MODERATE (PM2.5: {pm})"
        return 1.0, f"CLEAN (PM2.5: {pm})"

    def run_simulation(self, rated_hp):
        if not self.data:
            print("No data available.")
            return

        current_rho = self.calculate_air_density()
        std_rho = 1.225 
        sigma = current_rho / std_rho
        
        pollution_factor, pollution_status = self.analyze_pollution_impact()
        salt_status = self.analyze_salt_risk()
        
        actual_hp = rated_hp * sigma * pollution_factor
        
        print("-" * 50)
        print(f"LIVE PROPULSION REPORT: {self.data['temp_c']}°C | {self.data['humidity']}% Hum")
        print("-" * 50)
        print(f"Location Pressure: {self.data['pressure_hpa']} hPa")
        print(f"Air Density:       {current_rho:.3f} kg/m^3 ({(sigma*100):.1f}% of Std)")
        print(f"Salt Risk:         {salt_status}")
        print(f"Pollution Status:  {pollution_status}")
        print("-" * 50)
        print(f"RATED POWER:   {rated_hp} HP")
        print(f"ACTUAL POWER:  {actual_hp:.1f} HP")
        print(f"TOTAL LOSS:    {rated_hp - actual_hp:.1f} HP")
        print("-" * 50)

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    
    # --- CONFIGURATION ---
    # PASTE YOUR API KEY BELOW
    USER_API_KEY = '3882ecf49e38a2e0bcbdc96252d94685'
    
    city = input("Enter City Name (e.g. London, Tokyo): ")
    # We still ask for distance to coast because calculating that 
    # automatically requires a massive complex GIS database.
    dist = float(input("Distance to nearest ocean (km): "))
    
    # 1. Get Live Environment
    env = LiveEnvironmentalData(city, USER_API_KEY, dist)
    conditions = env.get_live_data()
    
    # 2. Run Calc
    if conditions:
        engine_sim = PropulsionCalculator(conditions)
        engine_sim.run_simulation(rated_hp=300)