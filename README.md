🌦️ Weather App

A simple and interactive Weather App built with Streamlit and the OpenWeatherMap API.
This app allows users to check real-time weather information for any city in the world — including temperature, humidity, wind speed, and weather conditions.

🚀 Features

🌍 Search weather by city name

🌡️ Displays temperature, humidity, pressure, and wind speed

🧭 Shows weather description (e.g., clear sky, rain)

🕒 Real-time data updates

🎨 Simple and modern Streamlit UI

🧰 Tech Stack

Python 3.9+

Streamlit — for the web interface

Requests — for API communication

OpenWeatherMap API — for weather data

⚙️ Installation

Clone this repository

git clone https://github.com/your-username/weather-app.git
cd weather-app


Create a virtual environment (optional but recommended)

python -m venv venv
source venv/bin/activate  # on macOS/Linux
venv\Scripts\activate     # on Windows


Install dependencies

pip install -r requirements.txt


Add your API key

Create a .env file in the project root and add:

OPENWEATHER_API_KEY=your_api_key_here


You can get your free API key at OpenWeatherMap
.

▶️ Run the App

Start the Streamlit app using:

streamlit run app.py


Then open your browser at:

http://localhost:8501

🧩 Project Structure
weather-app/
│
├── app.py                  # Main Streamlit application
├── requirements.txt        # Project dependencies
├── .env                    # API key (not shared)
└── README.md               # Project documentation

📸 Preview

(Add a screenshot or GIF here once your app is running)

💡 Example

Enter a city name like Paris or Tokyo, and instantly get:

Temperature: 21°C
Condition: Clear sky ☀️
Humidity: 48%
Wind Speed: 3.5 m/s

🧑‍💻 Author

Your Name
📧 your.email@example.com

🌐 GitHub Profile
