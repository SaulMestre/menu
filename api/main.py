from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import sqlite3, os, json, pathlib

DB_PATH = os.getenv("DB_PATH", "meals.db")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*")

app = FastAPI(title="Meals API")

# Permitir peticiones desde cualquier origen (para el front)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in ALLOWED_ORIGINS.split(",")] if ALLOWED_ORIGINS != "*" else ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_conn():
    """Crea la conexión SQLite y la tabla si no existe."""
    pathlib.Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    need_init = not pathlib.Path(DB_PATH).exists()
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    if need_init:
        con.execute("""
        CREATE TABLE IF NOT EXISTS meals(
          date TEXT PRIMARY KEY,
          lunch_json TEXT NOT NULL,
          dinner_json TEXT NOT NULL
        )
        """)
        con.commit()
    return con

# ---- Modelos de datos ----
class MealPart(BaseModel):
    dish: Optional[str] = None
    frozen: bool = False

class MealDay(BaseModel):
    date: str
    lunch: MealPart = MealPart()
    dinner: MealPart = MealPart()

# ---- Endpoints ----
@app.post("/meals")
def upsert_meal(day: MealDay):
    """Crea o actualiza una comida por fecha."""
    con = get_conn()
    con.execute(
        "REPLACE INTO meals(date, lunch_json, dinner_json) VALUES (?,?,?)",
        (day.date, json.dumps(day.lunch.model_dump()), json.dumps(day.dinner.model_dump()))
    )
    con.commit()
    con.close()
    return {"ok": True, "message": f"Comidas del {day.date} guardadas."}

@app.get("/meals/{date}")
def get_meal(date: str):
    """Obtiene una comida guardada por fecha."""
    con = get_conn()
    cur = con.execute("SELECT lunch_json, dinner_json FROM meals WHERE date=?", (date,))
    row = cur.fetchone()
    con.close()
    if not row:
        raise HTTPException(status_code=404, detail=f"No hay comidas guardadas para {date}.")
    return {
        "date": date,
        "lunch": json.loads(row[0]),
        "dinner": json.loads(row[1])
    }

@app.get("/ping")
def ping():
    """Ping de prueba"""
    return {"ok": True, "message": "API funcionando correctamente."}
