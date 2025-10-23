from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os, json, pathlib, sqlite3

# Postgres opcional
import psycopg
from psycopg.rows import tuple_row

APP_TITLE = "Meals API"
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*")
DATABASE_URL = os.getenv("DATABASE_URL")  # si existe: Postgres; si no: SQLite
SQLITE_PATH = os.getenv("DB_PATH", "meals.db")

app = FastAPI(title=APP_TITLE)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in ALLOWED_ORIGINS.split(",")] if ALLOWED_ORIGINS != "*" else ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class MealPart(BaseModel):
    dish: Optional[str] = None
    frozen: bool = False

class MealDay(BaseModel):
    date: str              # YYYY-MM-DD
    lunch: MealPart = MealPart()
    dinner: MealPart = MealPart()

# --------- Storage layer (PG o SQLite) ----------

def is_pg() -> bool:
    return bool(DATABASE_URL)

def init_db():
    if is_pg():
        with psycopg.connect(DATABASE_URL, row_factory=tuple_row) as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS meals (
                    date date PRIMARY KEY,
                    lunch_json jsonb NOT NULL,
                    dinner_json jsonb NOT NULL
                );
            """)
            con.commit()
    else:
        pathlib.Path(SQLITE_PATH).parent.mkdir(parents=True, exist_ok=True)
        need_init = not pathlib.Path(SQLITE_PATH).exists()
        with sqlite3.connect(SQLITE_PATH) as con:
            if need_init:
                con.execute("""
                    CREATE TABLE IF NOT EXISTS meals (
                        date TEXT PRIMARY KEY,
                        lunch_json TEXT NOT NULL,
                        dinner_json TEXT NOT NULL
                    );
                """)
                con.commit()

def upsert_meal_db(day: MealDay):
    if is_pg():
        with psycopg.connect(DATABASE_URL) as con:
            con.execute("""
                INSERT INTO meals(date, lunch_json, dinner_json)
                VALUES (%s, %s, %s)
                ON CONFLICT (date) DO UPDATE
                SET lunch_json = EXCLUDED.lunch_json,
                    dinner_json = EXCLUDED.dinner_json;
            """, (day.date, json.dumps(day.lunch.model_dump()), json.dumps(day.dinner.model_dump())))
            con.commit()
    else:
        with sqlite3.connect(SQLITE_PATH) as con:
            con.execute(
                "REPLACE INTO meals(date, lunch_json, dinner_json) VALUES (?,?,?)",
                (day.date, json.dumps(day.lunch.model_dump()), json.dumps(day.dinner.model_dump()))
            )
            con.commit()

def get_meal_db(date: str):
    if is_pg():
        with psycopg.connect(DATABASE_URL, row_factory=tuple_row) as con:
            row = con.execute("SELECT lunch_json, dinner_json FROM meals WHERE date = %s", (date,)).fetchone()
            return row
    else:
        with sqlite3.connect(SQLITE_PATH) as con:
            cur = con.execute("SELECT lunch_json, dinner_json FROM meals WHERE date=?", (date,))
            return cur.fetchone()

# --------- Endpoints ----------

@app.on_event("startup")
def _startup():
    init_db()

@app.get("/ping")
def ping():
    return {"ok": True, "driver": "postgres" if is_pg() else "sqlite"}

@app.post("/meals")
def upsert_meal(day: MealDay):
    upsert_meal_db(day)
    return {"ok": True, "message": f"Comidas del {day.date} guardadas."}

@app.get("/meals/{date}")
def get_meal(date: str):
    row = get_meal_db(date)
    if not row:
        raise HTTPException(status_code=404, detail=f"No hay comidas guardadas para {date}.")
    lunch_json, dinner_json = row
    # Si es PG vienen como dict; si es SQLite, strings
    lunch = lunch_json if isinstance(lunch_json, dict) else json.loads(lunch_json)
    dinner = dinner_json if isinstance(dinner_json, dict) else json.loads(dinner_json)
    return {"date": date, "lunch": lunch, "dinner": dinner}
