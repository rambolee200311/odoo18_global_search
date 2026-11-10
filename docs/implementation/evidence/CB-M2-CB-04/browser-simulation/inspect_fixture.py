from pathlib import Path
from office_core import inspect_document, ResourceBudget

if __name__ == "__main__":
    p = Path(__file__).with_name("cb04-browser-synthetic-v1-input.xlsx")
    budget = ResourceBudget(
        max_file_size=32*1024*1024, max_expanded_size=100*1024*1024,
        max_zip_entries=512, max_entry_size=20*1024*1024,
        max_xml_elements=1_000_000, max_cells=500_000,
        max_paragraphs=100_000, max_memory_bytes=4*1024*1024*1024,
        timeout_seconds=15,
    )
    info = inspect_document(p.read_bytes(), p.name,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", budget)
    print({"sha256": info.template_sha256, "format": info.format,
           "targets": [e.element_id for e in info.elements if e.element_id in {
               "xlsx:Inventory!E2", "xlsx:Inventory!A1", "xlsx:Inventory!B2"
           }]})
