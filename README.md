# FinSim API

![GitHub top language](https://img.shields.io/github/languages/top/Jalpan04/FinSim-API) ![GitHub repo size](https://img.shields.io/github/repo-size/Jalpan04/FinSim-API) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

FinSim API is a FastAPI-based backend service for the **Financial Life Event Simulator (FinSim)**. It allows users to simulate their long-term financial projection (typically 30 years) by adding real-world investments and life events, tracking how their net worth accumulates over time. It also acts as a secure API gateway/proxy for real-time stock and commodity prices.

## Features

- **Long-term Financial Projection**: Calculates year-by-year cash flow, asset valuations, and total net worth over a custom timeframe (default: 30 years).
- **Life Events Simulation**: Incorporates critical life milestones (e.g. Marriage, Education, Retirement) and recurring overhead costs (e.g. Loans, Personal Expenses, Bills) that drain savings.
- **Diversified Portfolio Management**: Model investment growth rates across various asset classes:
  - **Properties** (Default growth: 6% annually)
  - **Mutual Funds** (Default growth: 12% annually)
  - **Stocks, FDs, Gold, and Silver**
- **Real-time API Proxies**:
  - Fetch real-time stock prices securely via the **Twelve Data API**.
  - Query real-time Gold and Silver prices in INR (per gram) via **API Ninjas**, with a reliable fallback price structure.
- **Local Persistence**: Stores simulation settings locally in a lightweight JSON database schema (`db.json`) utilizing FastAPI's lifespan framework.

## Tech Stack

- **Core Framework**: FastAPI (Python 3.8+)
- **Validation**: Pydantic v2
- **HTTP Client**: `httpx` (for asynchronous API calls)
- **Database**: Local JSON-based store (`db.json`)

## File Structure

```
├── main.py              # Application logic, schemas, and endpoint controllers
├── requirements.txt     # Python dependency configuration
├── db.json              # Local persistent JSON database (auto-generated)
├── .gitignore           # Git ignore patterns
└── LICENSE              # MIT License
```

## API Endpoint Reference

### Simulations

- `POST /simulations?initial_salary={value}`: Initialize a new financial simulation.
- `GET /simulations/{sim_id}`: Retrieve current state of the simulation.
- `GET /simulations/{sim_id}/projection?years={value}`: Generate the year-by-year net worth projection list.

### Investments & Life Events

- `POST /simulations/{sim_id}/investments`: Append an investment to the simulation.
- `DELETE /simulations/{sim_id}/investments/{item_id}`: Remove a specific investment item.
- `POST /simulations/{sim_id}/events`: Append a life event to the simulation.
- `DELETE /simulations/{sim_id}/events/{item_id}`: Remove a specific life event.

### Real-Time Markets

- `GET /stock/{symbol}`: Secure proxy fetching current price of a ticker.
- `GET /commodities/gold`: Proxy fetching current Gold price per gram in INR.
- `GET /commodities/silver`: Proxy fetching current Silver price per gram in INR.

## Setup & Local Server

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Jalpan04/FinSim-API.git
   ```
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` configuration file in the project root:
   ```env
   TWELVE_DATA_API_KEY="your_twelve_data_api_key"
   API_NINJAS_KEY="your_api_ninjas_key"
   ```

### Running Locally
To launch the FastAPI development server with hot-reloading:
```bash
uvicorn main:app --reload --port 8000
```
Open `http://localhost:8000/docs` in your browser to view the interactive Swagger API documentation.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
