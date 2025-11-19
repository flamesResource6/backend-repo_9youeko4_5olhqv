import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Any, Dict

from schemas import Capability, Inquiry, Product, User

app = FastAPI(title="Manufacturing Website API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Utility to serialize MongoDB documents

def serialize_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(doc, dict):
        return doc
    d = dict(doc)
    if "_id" in d:
        d["id"] = str(d.pop("_id"))
    return d


@app.get("/")
def read_root():
    return {"message": "Manufacturing API is running"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        from database import db

        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"

            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    # Check environment variables
    import os as _os
    response["database_url"] = "✅ Set" if _os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if _os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


# Schemas endpoint (useful for admin tooling/viewers)
@app.get("/schema")
def get_schema():
    return {
        "user": User.model_json_schema(),
        "product": Product.model_json_schema(),
        "capability": Capability.model_json_schema(),
        "inquiry": Inquiry.model_json_schema(),
    }


# Public content endpoints
@app.get("/api/capabilities", response_model=List[Capability])
def list_capabilities():
    """Return capabilities from DB. If none, seed a small default set once."""
    try:
        from database import db, get_documents, create_document
    except Exception:
        # Fallback static content if DB not configured
        return [
            Capability(name="CNC Machining", summary="Precision milling and turning for metals and plastics", icon="settings"),
            Capability(name="Sheet Metal Fabrication", summary="Laser cutting, bending, and assembly for prototypes to production", icon="square"),
            Capability(name="Welding", summary="Certified MIG/TIG welding for structural and aesthetic parts", icon="hammer"),
        ]

    if db is None:
        return [
            Capability(name="CNC Machining", summary="Precision milling and turning for metals and plastics", icon="settings"),
            Capability(name="Sheet Metal Fabrication", summary="Laser cutting, bending, and assembly for prototypes to production", icon="square"),
            Capability(name="Welding", summary="Certified MIG/TIG welding for structural and aesthetic parts", icon="hammer"),
        ]

    # Try to read from DB
    docs = get_documents("capability")
    items = [Capability(**serialize_doc(d)) for d in docs]

    if len(items) == 0:
        # Seed defaults once
        defaults = [
            {"name": "CNC Machining", "summary": "Precision milling and turning for metals and plastics", "icon": "settings"},
            {"name": "Sheet Metal Fabrication", "summary": "Laser cutting, bending, and assembly for prototypes to production", "icon": "square"},
            {"name": "Welding", "summary": "Certified MIG/TIG welding for structural and aesthetic parts", "icon": "hammer"},
            {"name": "Powder Coating", "summary": "Durable finishes with a wide range of colors and textures", "icon": "paintbrush"},
        ]
        for d in defaults:
            try:
                create_document("capability", d)
            except Exception:
                pass
        docs = get_documents("capability")
        items = [Capability(**serialize_doc(d)) for d in docs]

    return items


# Contact / quote endpoint
class InquiryResponse(BaseModel):
    id: str
    message: str


@app.post("/api/inquiries", response_model=InquiryResponse)
def create_inquiry(payload: Inquiry):
    try:
        from database import create_document, db
    except Exception:
        raise HTTPException(status_code=503, detail="Database not configured")

    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        inserted_id = create_document("inquiry", payload)
        return {"id": inserted_id, "message": "Inquiry received. Our team will contact you shortly."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save inquiry: {str(e)[:120]}")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
