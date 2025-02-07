# ETL-DOCKER-AIRFLOW-AWS

Here's a **state-of-the-art README** for your project, explaining the tools, architecture, and advantages of your pipeline. I've also included a **segment-by-segment explanation** of your Airflow DAG.  

---

# **Weather ETL Pipeline with Apache Airflow, Docker, and PostgreSQL**  

## **Project Overview**  
This project builds an **ETL (Extract, Transform, Load) data pipeline** using **Apache Airflow** to fetch weather data from the **OpenWeatherMap API**, process it, and store it in a **PostgreSQL database running inside a Docker container**.  

## **Architecture**  
The pipeline follows a standard **ETL architecture**:  

1. **Extract**: Fetches real-time weather data for multiple cities from the OpenWeatherMap API.  
2. **Transform**: Cleans and structures the data, extracting key weather attributes.  
3. **Load**: Inserts the transformed data into a PostgreSQL database.  

### **Technology Stack**  
- **Apache Airflow** (for orchestrating the pipeline)  
- **Docker** (to containerize PostgreSQL)  
- **PostgreSQL** (to store weather data)  
- **OpenWeatherMap API** (to fetch real-time weather data)  
- **Python (Requests, psycopg2, Airflow Providers)**  

---

## **Installation & Setup**  

### **1. Clone the Repository**  
```sh
git clone https://github.com/stilinsk/weather-etl-pipeline.git
cd weather-etl-pipeline
```

### **2. Start PostgreSQL in Docker**  
```sh
docker-compose up -d
```
This will start a **PostgreSQL** instance inside a Docker container.

### **3. Set Up Apache Airflow**  
```sh
astro dev start
```
This will start **Apache Airflow** using **Astronomer CLI (Astro)**.

### **4. Set Up Airflow Connections**  
In **Airflow UI**:  
1. Navigate to **Admin → Connections**  
2. Create a new connection with the following details:  
   - **Connection ID**: `postgres_default`  
   - **Connection Type**: `Postgres`  
   - **Host**: `postgres`  
   - **Port**: `5432`  
   - **Database**: `weather_db`  
   - **Username**: `airflow`  
   - **Password**: `airflow`  

### **5. Trigger the DAG**  
Go to **Airflow UI** → Enable & Run **`weather_etl_pipeline`** DAG.

---

## **Code Breakdown**  

### **1. Import Required Libraries**  
```python
from airflow import DAG
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.decorators import task
from airflow.utils.dates import days_ago
from datetime import datetime, timedelta
import requests
```
- `DAG`: Defines the Airflow DAG (workflow).  
- `PostgresHook`: Connects Airflow to PostgreSQL.  
- `task`: Simplifies task creation using decorators.  
- `requests`: Fetches data from OpenWeatherMap API.  
- `datetime`, `timedelta`: Handles time-based operations.

---

### **2. Define Constants**  
```python
CITIES = ['London', 'New York', 'Tokyo', 'Paris', 'Sydney', 'Los Angeles']
POSTGRES_CONN_ID = 'postgres_default'
API_URL = 'https://api.openweathermap.org/data/2.5/weather?q='
API_KEY = 'your_api_key'  # Replace with a valid OpenWeatherMap API key
```
- List of **cities** whose weather data will be fetched.  
- **API details** for OpenWeatherMap.  
- **PostgreSQL connection ID** (configured in Airflow UI).

---

### **3. Define DAG Default Arguments**  
```python
default_args = {
    'owner': 'airflow',
    'start_date': days_ago(1),
    'retries': 3,
    'retry_delay': timedelta(minutes=5)
}
```
- The DAG is owned by **Airflow**.  
- It starts **one day ago**.  
- If a task fails, it will **retry 3 times**, with a **5-minute delay** between retries.

---

### **4. Define the DAG**  
```python
with DAG(dag_id='weather_etl_pipeline',
         default_args=default_args,
         schedule_interval='@daily',
         catchup=False) as dag:
```
- **`@daily` schedule**: Runs the DAG once per day.  
- **`catchup=False`**: Prevents running DAG for past dates.  

---

### **5. Extract Task - Fetch Data from API**  
```python
@task()
def extract_weather_data():
    weather_data = {}
    for city in CITIES:
        endpoint = f'{API_URL}{city}&appid={API_KEY}'
        response = requests.get(endpoint)

        if response.status_code == 200:
            weather_data[city] = response.json()
        elif response.status_code == 401:
            raise Exception(f"Unauthorized API key for {city}. Please check your API key.")
        else:
            raise Exception(f"Failed to fetch weather data for {city}: {response.status_code}")
    return weather_data
```
- Loops through **all cities** and fetches data from OpenWeatherMap API.  
- If the API key is **invalid (401 error)**, an exception is raised.  

---

### **6. Transform Task - Process Extracted Data**  
```python
@task()
def transform_weather_data(weather_data):
    transformed_data = {}
    for city, data in weather_data.items():
        current_weather = data['main']
        transformed_data[city] = {
            'city': city,
            'temperature': current_weather['temp'],
            'windspeed': data['wind']['speed'],
            'winddirection': data['wind']['deg'],
            'weathercode': data['weather'][0]['id'],
            'request_timestamp': datetime.now()
        }
    return transformed_data
```
- Extracts **temperature, wind speed, wind direction, and weather code**.  
- Adds a **timestamp** for when the data was fetched.  

---

### **7. Load Task - Store Data in PostgreSQL**  
```python
@task()
def load_weather_data(transformed_data):
    pg_hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    conn = pg_hook.get_conn()
    cursor = conn.cursor()

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
```
- Creates **weather_data table** if it does not exist.  
- Inserts transformed data into PostgreSQL.  

---

### **8. DAG Execution - ETL Flow**  
```python
weather_data = extract_weather_data()
transformed_data = transform_weather_data(weather_data)
load_weather_data(transformed_data)
```
- Executes the **Extract → Transform → Load** sequence.

---

## **Advantages of This Pipeline**  
✅ **Automation**: Apache Airflow schedules and manages ETL workflows efficiently.  
✅ **Scalability**: Easily add new cities or integrate additional transformations.  
✅ **Containerization**: PostgreSQL runs in Docker, ensuring consistency.  
✅ **Error Handling**: Retries failed tasks automatically.  
✅ **Centralized Storage**: PostgreSQL stores structured weather data for analysis.  

---

## **Future Enhancements**  
🚀 **Integrate Data Visualization** using **Tableau / Power BI / Grafana**.  
🚀 **Extend Data Model** with **historical weather data & forecasting**.  
🚀 **Deploy to AWS** using **S3, RDS, and Lambda**.  

---

This **README** provides a **comprehensive guide** to your project. Let me know if you'd like any modifications! 🚀🔥
