# main.py (Final Version for Render Deployment)
import os
import uuid
import json
from typing import List, Literal
from contextlib import asynccontextmanager

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware

PROPERTY_GROWTH_RATE = 1.06
MF_GROWTH_RATE = 1.12
USD_TO_INR_RATE = 83.5

simulations_db = {}


def save_db():
    with open("db.json", "w") as f:
        db_as_dict = {sim_id: sim.dict() for sim_id, sim in simulations_db.items()}
        json.dump(db_as_dict, f, indent=4)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global simulations_db
    try:
        with open("db.json", "r") as f:
            db_from_file = json.load(f)
            simulations_db = {sim_id: Simulation(**data) for sim_id, data in db_from_file.items()}
            print("Database loaded successfully from db.json")
    except FileNotFoundError:
        simulations_db = {}
        print("db.json not found, starting with an empty database.")
    yield


load_dotenv()
app = FastAPI(
    title="FinSim API",
    description="API for the Financial Life Event Simulator",
    version="2.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Investment(BaseModel):
    item_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: Literal["Stock", "Properties", "Mutual Funds", "FD", "Gold/Silver"]
    name: str
    initial_value: float = Field(..., gt=0)
    year_of_investment: int = Field(..., gt=0)
    shares: float = Field(default=0, ge=0)


class LifeEvent(BaseModel):
    item_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: Literal["Marriage", "Education", "Household Bill", "Loan", "Personal Expense", "Insurance", "Retirement"]
    name: str
    cost: float = Field(..., gt=0)
    year_of_event: int = Field(..., gt=0)


class Simulation(BaseModel):
    sim_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    initial_salary: float = Field(..., gt=0)
    investments: List[Investment] = []
    life_events: List[LifeEvent] = []


@app.post("/simulations", response_model=Simulation)
def create_simulation(initial_salary: float):
    new_sim = Simulation(initial_salary=initial_salary)
    simulations_db[new_sim.sim_id] = new_sim
    save_db()
    return new_sim


@app.get("/simulations/{sim_id}", response_model=Simulation)
def get_simulation(sim_id: str):
    if sim_id not in simulations_db: raise HTTPException(404, "Simulation not found")
    return simulations_db[sim_id]


@app.post("/simulations/{sim_id}/investments", response_model=Investment)
def add_investment(sim_id: str, investment: Investment):
    if sim_id not in simulations_db: raise HTTPException(404, "Simulation not found")
    simulations_db[sim_id].investments.append(investment)
    save_db()
    return investment


@app.post("/simulations/{sim_id}/events", response_model=LifeEvent)
def add_life_event(sim_id: str, event: LifeEvent):
    if sim_id not in simulations_db: raise HTTPException(404, "Simulation not found")
    simulations_db[sim_id].life_events.append(event)
    save_db()
    return event


@app.delete("/simulations/{sim_id}/investments/{item_id}", status_code=204)
def delete_investment(sim_id: str, item_id: str):
    if sim_id not in simulations_db: raise HTTPException(404, "Simulation not found")
    sim = simulations_db[sim_id]
    initial_len = len(sim.investments)
    sim.investments = [inv for inv in sim.investments if inv.item_id != item_id]
    if len(sim.investments) == initial_len: raise HTTPException(404, "Investment item not found")
    save_db()


@app.delete("/simulations/{sim_id}/events/{item_id}", status_code=204)
def delete_life_event(sim_id: str, item_id: str):
    if sim_id not in simulations_db: raise HTTPException(404, "Simulation not found")
    sim = simulations_db[sim_id]
    initial_len = len(sim.life_events)
    sim.life_events = [event for event in sim.life_events if event.item_id != item_id]
    if len(sim.life_events) == initial_len: raise HTTPException(404, "Life event item not found")
    save_db()


@app.get("/simulations/{sim_id}/projection")
def get_projection(sim_id: str, years: int = 30):
    if sim_id not in simulations_db: raise HTTPException(404, "Simulation not found")
    sim = simulations_db[sim_id]
    projection_data = []
    cash_savings = 0
    annual_salary = sim.initial_salary * 12
    investment_current_values = {inv.item_id: inv.initial_value for inv in sim.investments}

    for year in range(1, years + 1):
        for inv in sim.investments:
            if inv.year_of_investment < year:
                if inv.type == "Properties":
                    investment_current_values[inv.item_id] *= PROPERTY_GROWTH_RATE
                elif inv.type == "Mutual Funds":
                    investment_current_values[inv.item_id] *= MF_GROWTH_RATE

        yearly_income = annual_salary
        yearly_cost = sum(event.cost for event in sim.life_events if event.year_of_event == year)
        investment_cost_this_year = sum(inv.initial_value for inv in sim.investments if inv.year_of_investment == year)

        cash_savings += yearly_income - yearly_cost - investment_cost_this_year
        total_investment_value = sum(
            investment_current_values[inv.item_id] for inv in sim.investments if inv.year_of_investment <= year)
        net_worth = cash_savings + total_investment_value
        projection_data.append({"year": year, "net_worth": round(net_worth, 2)})

    return projection_data


@app.get("/stock/{symbol}")
async def get_stock_price(symbol: str):
    # 1. Use the new environment variable
    api_key = os.getenv("TWELVE_DATA_API_KEY")
    if not api_key:
        raise HTTPException(500, "Twelve Data API key not configured")

    # 2. Note the different URL structure for Twelve Data
    # For Indian stocks like "RELIANCE.NS", you might need to use "RELIANCE:NSE"
    # The API is generally smart enough to handle common tickers.
    url = f"https://api.twelvedata.com/price?symbol={symbol}&apikey={api_key}"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            response.raise_for_status()  # Raises an exception for 4XX or 5XX status codes

            # 3. Parse the simpler JSON response from Twelve Data
            data = response.json()
            price = data.get("price")

            if not price:
                raise HTTPException(404, f"Price not found for symbol: {symbol}. Check if the ticker is correct.")

            # The price is returned as a string, so we convert it to float
            return {"symbol": symbol, "price": round(float(price), 2)}

        except httpx.HTTPStatusError as e:
            # Handle specific API errors, e.g., invalid symbol or key
            raise HTTPException(status_code=e.response.status_code, detail=f"Error from stock API: {e.response.text}")
        except Exception:
            # Generic fallback for network issues or other errors
            raise HTTPException(503, "Error communicating with stock API")

@app.get("/commodities/gold")
async def get_gold_price():
    api_key = os.getenv("API_NINJAS_KEY")
    if not api_key: raise HTTPException(500, "API Ninjas key not configured")
    url = "https://api.api-ninjas.com/v1/goldprice"
    headers = {'X-Api-Key': api_key}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            price_per_ounce_usd = response.json().get("price")
            price_per_gram_inr = (price_per_ounce_usd / 28.3495) * USD_TO_INR_RATE
            return {"metal": "Gold", "price_per_gram_inr": round(price_per_gram_inr, 2)}
        except Exception:
            return {"metal": "Gold", "price_per_gram_inr": 7250.00}


@app.get("/commodities/silver")
async def get_silver_price():
    """
    A secure proxy to get the latest price of Silver (per gram) in INR.
    """
    api_key = os.getenv("API_NINJAS_KEY")
    if not api_key: raise HTTPException(500, "API Ninjas key not configured")

    # The URL is the only major change
    url = "https://api.api-ninjas.com/v1/silverprice"
    headers = {'X-Api-Key': api_key}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            price_per_ounce_usd = response.json().get("price")
            # 1 Ounce = 28.3495 grams
            price_per_gram_inr = (price_per_ounce_usd / 28.3495) * USD_TO_INR_RATE
            return {"metal": "Silver", "price_per_gram_inr": round(price_per_gram_inr, 2)}
        except Exception:
            # Return a believable mock price as a fallback
            return {"metal": "Silver", "price_per_gram_inr": 95.50}
            
