from nicegui import ui
import os
import json
import pymongo  
from pymongo import MongoClient, errors

# Load MongoDB URI from .env file for security
from dotenv import load_dotenv, find_dotenv

# Load .env explicitly from project (handles running from different working dirs)
dotenv_path = find_dotenv()
if dotenv_path:
    load_dotenv(dotenv_path)
else:
    load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
#print("MONGO_URI:", "[REDACTED]" if MONGO_URI else None, "loaded:", MONGO_URI is not None)

if not MONGO_URI:
    raise RuntimeError("MONGO_URI not found in environment. Ensure .env exists and defines MONGO_URI")

client = MongoClient(MONGO_URI)
db = client["yeast_db"]
collection = db["orthologs"]

def search_gene(query):
    query = query.strip()
    if not query: return []
    # build regex clauses (allow partial matches)
    regex_clauses = [
        {"sc_gene.id": {"$regex": query, "$options": "i"}},
        {"sc_gene.name": {"$regex": query, "$options": "i"}},
        {"km_gene.ids": {"$regex": query, "$options": "i"}},
    ]

    # Try combining text search with regexes; if MongoDB planner refuses (common when mixing TEXT and non-TEXT in $or),
    # fall back to a regex-only search to avoid crashing the app.
    try:
        return list(collection.find({"$or": regex_clauses + [{"$text": {"$search": query}}]}, {"_id": 0}))
    except errors.OperationFailure:
        return list(collection.find({"$or": regex_clauses}, {"_id": 0}))
    
# layout: top row with left search box and right results area
top_row = ui.row().classes("w-full items-start gap-6 p-4")
with top_row:
    left_col = ui.column().classes("w-1/4 items-start")
    results_container = ui.column().classes("w-3/4 items-start")

    with left_col:
        ui.label("Yeast Gene Search").classes("text-2xl font-bold")
        query_input = ui.input(label="Inserisci gene SC o KM").props("clearable")
        # persistent status label (shows searching/results/errors)
        status_label = ui.label("").classes("mt-2 text-sm")
        btn_search = ui.button("Search").classes("mt-4")


def on_search():
    results_container.clear()
    status_label.set_text("Searching...")
    query_val = query_input.value or ""
    print(f"[UI] Starting search for: '{query_val}'")
    try:
        results = search_gene(query_val)
    except Exception as e:
        print(f"[UI] search_gene raised: {e}")
        with results_container:
            ui.label("Error during search").classes("text-red-500")
        status_label.set_text(f"Error: {e}")
        return

    if not results:
        with results_container:
            ui.label("No results found").classes("text-red-500")
        status_label.set_text("No results found")
        print("[UI] No results found")
        return

    # prendiamo il primo risultato (migliore match)
    r = results[0]

    sc = r.get("sc_gene")
    km = r.get("km_gene")

    query = query_input.value.lower()

    # Determiniamo quale gene è quello cercato
    is_km_match = km and (
        query in str(km.get("ids", "")).lower()
    )

    main_gene = km if is_km_match else sc
    ortolog_gene = sc if is_km_match else km
    main_species = "K. marxianus" if is_km_match else "S. cerevisiae"
    ortolog_species = "S. cerevisiae" if is_km_match else "K. marxianus"

    with results_container:

        # --- MAIN GENE BOX ---
        with ui.card().classes("w-3/4 p-6 shadow-lg"):
            ui.label(main_species).classes("text-2xl font-bold")

            ui.label(f"ID: {main_gene.get('id', main_gene.get('ids', ''))}") \
                .classes("text-lg")

            if main_gene.get("name"):
                ui.label(f"Gene name: {main_gene.get('name')}")

            ui.label(f"Description: {main_gene.get('description', '')}")

            locus = main_gene.get("locus", {})
            ui.label(
                f"Locus: Chr {locus.get('chromosome')} | "
                f"{locus.get('start')} - {locus.get('end')} "
                f"({locus.get('strand')})"
            )

            links = main_gene.get("external_links", {})
            with ui.row():
                for label, link in links.items():
                    if link:
                        ui.link(label.upper(), link, new_tab=True)

        # --- ORTHOLOG SECTION ---
        if ortolog_gene:
            ui.separator().classes("w-3/4")

            with ui.card().classes("w-3/4 p-6 bg-gray-50"):
                ui.label(f"Ortholog: {ortolog_species}") \
                    .classes("text-xl font-semibold")

                ui.label(
                    f"ID: {ortolog_gene.get('id', ortolog_gene.get('ids', ''))}"
                )

                if ortolog_gene.get("name"):
                    ui.label(f"Gene name: {ortolog_gene.get('name')}")

                ui.label(
                    f"Description: {ortolog_gene.get('description', '')}"
                )

                locus = ortolog_gene.get("locus", {})
                ui.label(
                    f"Locus: Chr {locus.get('chromosome')} | "
                    f"{locus.get('start')} - {locus.get('end')} "
                    f"({locus.get('strand')})"
                )

                links = ortolog_gene.get("external_links", {})
                with ui.row():
                    for label, link in links.items():
                        if link:
                            ui.link(label.upper(), link, new_tab=True)

        # report counts
        print(f"[UI] Search returned {len(results)} documents")
        status_label.set_text(f"Found {len(results)} entries")
    # bind button callback after on_search is defined
btn_search.on("click", on_search)
query_input.on("keydown.enter", lambda e: on_search())
ui.run()