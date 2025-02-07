from airflow import DAG
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.decorators import task
from airflow.utils.dates import days_ago
from datetime import datetime, timedelta
import requests

# List of cities for weather data
CITIES = [
    'London',
    'New York',
    'Tokyo',
    'Paris',
    'Sydney',
    'Los Angeles',
    # Add more cities as needed
]

POSTGRES_CONN_ID = 'postgres_default'
API_URL = 'https://api.openweathermap.org/data/2.5/weather?q='
API_KEY = '18890a1d8cfd1b3130af9ac578d2c1a5'  # Ensure this is a valid API key

default_args = {
    'owner': 'airflow',
    'start_date': days_ago(1),
    'retries': 3,  # Retry 3 times on failure
    'retry_delay': timedelta(minutes=5)  # Delay of 5 minutes between retries
}

# DAG
with DAG(dag_id='weather_etl_pipeline',
         default_args=default_args,
         schedule_interval='@daily',
         catchup=False) as dag:

    @task()
    def extract_weather_data():
        """Extract weather data for all cities at once."""
        weather_data = {}
        for city in CITIES:
            # Construct the API request URL for current weather data (using city name and API key)
            endpoint = f'{API_URL}{city}&appid={API_KEY}'
            response = requests.get(endpoint)

            if response.status_code == 200:
                weather_data[city] = response.json()
            elif response.status_code == 401:
                raise Exception(f"Unauthorized API key for {city}. Please check your API key.")
            else:
                raise Exception(f"Failed to fetch weather data for {city}: {response.status_code}")
        return weather_data
    
    @task()
    def transform_weather_data(weather_data):
        """Transform the extracted weather data for all cities."""
        transformed_data = {}
        for city, data in weather_data.items():
            current_weather = data['main']
            transformed_data[city] = {
                'city': city,
                'temperature': current_weather['temp'],
                'windspeed': data['wind']['speed'],
                'winddirection': data['wind']['deg'],
                'weathercode': data['weather'][0]['id'],
                'request_timestamp': datetime.now()  # Store request timestamp
            }
        return transformed_data
    
    @task()
    def load_weather_data(transformed_data):
        """Load transformed data into PostgreSQL."""
        pg_hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
        conn = pg_hook.get_conn()
        cursor = conn.cursor()

        # Create table if it doesn't exist
        cursor.execute(""" 
        CREATE TABLE IF NOT EXISTS weather_data (
            city VARCHAR(255),
            temperature FLOAT,
            windspeed FLOAT,
            winddirection FLOAT,
            weathercode INT,
            request_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Insert transformed data into the table
        for city, data in transformed_data.items():
            cursor.execute(""" 
            INSERT INTO weather_data (city, temperature, windspeed, winddirection, weathercode, request_timestamp)
            VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                data['city'],
                data['temperature'],
                data['windspeed'],
                data['winddirection'],
                data['weathercode'],
                data['request_timestamp']
            ))

        conn.commit()
        cursor.close()
        conn.close()

    # Sequential ETL process for all cities
    weather_data = extract_weather_data()
    transformed_data = transform_weather_data(weather_data)
    load_weather_data(transformed_data)
