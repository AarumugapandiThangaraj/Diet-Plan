import os
import json
import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

# Define sleek premium color palette
PRIMARY_COLOR = colors.HexColor("#1B4332")     # Dark Forest Green
SECONDARY_COLOR = colors.HexColor("#40916C")   # Accent Sage Green
NEUTRAL_DARK = colors.HexColor("#2D3748")      # Deep Charcoal Text
NEUTRAL_LIGHT = colors.HexColor("#F7FAFC")     # Soft Background Light Grey
BORDER_COLOR = colors.HexColor("#E2E8F0")      # Light Slate Grey Border
ACCENT_RED = colors.HexColor("#E53E3E")        # Soft Coral Red for warnings

class NumberedCanvas(canvas.Canvas):
    """
    Canvas to perform two-pass rendering for accurate page numbers (Page X of Y)
    and professional headers/footers on every page.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        
        # We don't draw decorative header/footer on first page if it is a cover page,
        # but here we can draw it on all pages to ensure professional lookup.
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(PRIMARY_COLOR)
        
        # Draw Header
        self.drawString(36, 756, "NUTRIPLAN MASTER DATA REPORT")
        self.setStrokeColor(SECONDARY_COLOR)
        self.setLineWidth(1)
        self.line(36, 748, 576, 748)
        
        # Draw Footer
        self.line(36, 48, 576, 48)
        self.setFont("Helvetica", 8)
        self.setFillColor(NEUTRAL_DARK)
        self.drawString(36, 34, f"Generated: {datetime.date.today().strftime('%B %d, %Y')}")
        
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(576, 34, page_text)
        
        self.restoreState()


def xml_escape(text):
    """
    Escape text for safe ReportLab paragraph parsing (avoiding XML errors).
    """
    if text is None:
        return ""
    text = str(text)
    # Replace ampersand first!
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace('"', "&quot;")
    text = text.replace("'", "&apos;")
    return text


def to_para(val, style, is_html=False):
    """
    Safely converts lists, dicts, or strings to a ReportLab Paragraph.
    """
    if val is None:
        return Paragraph("", style)
    
    if isinstance(val, list):
        text = "<br/>".join(xml_escape(str(x)) for x in val)
    elif isinstance(val, dict):
        text = "<br/>".join(f"<b>{xml_escape(str(k))}:</b> {xml_escape(str(v))}" for k, v in val.items())
    else:
        text = str(val)
        if not is_html:
            text = xml_escape(text)
            
    text = text.replace('\n', '<br/>')
    return Paragraph(text, style)


def build_pdf_for_file(src_path, dest_path, file_type):
    print(f"Converting: {src_path} -> {dest_path}")
    
    with open(src_path, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
        except Exception as e:
            print(f"Error parsing JSON {src_path}: {e}")
            return

    # Extract clean list of items
    items = []
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        # Look for typical keys
        for key in ['foods', 'meals', 'ingredients', 'data']:
            if key in data and isinstance(data[key], list):
                items = data[key]
                break
        if not items:
            # Just treat the dict as a single-item list or format key-values
            items = [data]

    # Setup Document
    # Page size: Letter (612 x 792 pt). Margins: 0.5 in (36 pt)
    doc = SimpleDocTemplate(
        dest_path,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()
    
    # Custom Typography Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=PRIMARY_COLOR,
        spaceAfter=15
    )
    
    subtitle_style = ParagraphStyle(
        'DocSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=NEUTRAL_DARK,
        spaceAfter=25
    )

    section_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=PRIMARY_COLOR,
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=NEUTRAL_DARK
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=body_style,
        fontName='Helvetica-Bold',
        textColor=colors.white
    )

    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=body_style,
        fontSize=8.5,
        leading=11
    )

    story = []
    
    # Title & Metadata
    filename = os.path.basename(src_path)
    title_text = filename.replace('.json', '').replace('_', ' ').replace('-', ' ').title()
    story.append(Spacer(1, 10))
    story.append(Paragraph(xml_escape(title_text), title_style))
    
    metadata = f"<b>Source File:</b> {xml_escape(src_path)} | <b>Total Records:</b> {len(items)} | <b>Type:</b> {file_type.upper()}"
    story.append(Paragraph(metadata, subtitle_style))
    story.append(Spacer(1, 10))

    if not items:
        story.append(Paragraph("Empty dataset or unrecognized JSON format.", body_style))
        doc.build(story, canvasmaker=NumberedCanvas)
        return

    # Process based on data type
    if file_type == 'meals':
        # Beautiful card-like layout for each meal
        for idx, meal in enumerate(items):
            meal_elements = []
            
            # Header row
            name = meal.get('Name') or meal.get('meal_name') or 'Unnamed Meal'
            meal_id = meal.get('ID') or meal.get('meal_id') or 'N/A'
            session = meal.get('Session') or meal.get('meal_time') or 'N/A'
            time = meal.get('Time') or 'N/A'
            
            header_text = f"<b>{idx+1}. {xml_escape(name)}</b> ({xml_escape(meal_id)})"
            meal_elements.append(Paragraph(header_text, section_style))
            
            # Details Table
            desc = meal.get('Description') or meal.get('description') or 'No description.'
            goal = meal.get('Goal') or meal.get('goal') or 'N/A'
            diet = meal.get('Diet Type') or meal.get('diet_type') or 'N/A'
            cuisine = meal.get('Cuisine') or meal.get('cuisine') or 'N/A'
            allergens = meal.get('Allergens') or meal.get('allergies') or 'None'
            
            # Parse Foods
            foods_raw = meal.get('Foods') or meal.get('foods_struct') or []
            food_list_strs = []
            if isinstance(foods_raw, list):
                for f in foods_raw:
                    if isinstance(f, dict):
                        f_id = f.get('ID') or f.get('name') or 'Unknown'
                        f_qty = f.get('Quantity') or f.get('quantity') or ''
                        f_unit = f.get('Unit') or f.get('unit') or ''
                        food_list_strs.append(f"{f_id} ({f_qty} {f_unit})")
                    else:
                        food_list_strs.append(str(f))
            else:
                food_list_strs.append(str(foods_raw))
            foods_display = ", ".join(food_list_strs) if food_list_strs else "None"
            
            data_table = [
                [Paragraph("<b>Session / Time:</b>", body_style), to_para(f"{session} at {time}", body_style)],
                [Paragraph("<b>Goal / Diet / Cuisine:</b>", body_style), to_para(f"{goal} | {diet} | {cuisine}", body_style)],
                [Paragraph("<b>Allergens:</b>", body_style), to_para(allergens, body_style)],
                [Paragraph("<b>Included Foods:</b>", body_style), to_para(foods_display, body_style)],
                [Paragraph("<b>Description:</b>", body_style), to_para(desc, body_style)]
            ]
            
            t = Table(data_table, colWidths=[130, 410])
            t.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('BACKGROUND', (0,0), (-1,-1), NEUTRAL_LIGHT),
                ('TOPPADDING', (0,0), (-1,-1), 4),
                ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                ('LEFTPADDING', (0,0), (-1,-1), 8),
                ('RIGHTPADDING', (0,0), (-1,-1), 8),
                ('LINEBELOW', (0,0), (-1,-1), 0.5, BORDER_COLOR),
                ('BOX', (0,0), (-1,-1), 1, SECONDARY_COLOR),
            ]))
            
            meal_elements.append(t)
            meal_elements.append(Spacer(1, 12))
            
            # Keep each meal block together so it doesn't get awkwardly split across pages
            story.append(KeepTogether(meal_elements))

    elif file_type == 'foods':
        # Beautiful card-like layout for each food
        for idx, food in enumerate(items):
            food_elements = []
            
            name = food.get('Name') or 'Unnamed Food'
            food_id = food.get('ID') or 'N/A'
            cuisine = food.get('Cuisine') or 'N/A'
            
            header_text = f"<b>{idx+1}. {xml_escape(name)}</b> ({xml_escape(food_id)}) — {xml_escape(cuisine)}"
            food_elements.append(Paragraph(header_text, section_style))
            
            desc = food.get('Description') or 'No description.'
            diet = food.get('Diet Type') or 'N/A'
            supports = food.get('Supports') or 'N/A'
            notes = food.get('Notes') or 'N/A'
            prep = food.get('Preparation') or 'N/A'
            
            # Nutritional Info
            nut_raw = food.get('Nutritional_Info') or food.get('Nutritional_Info_per_Serving') or {}
            nut_str = "N/A"
            if isinstance(nut_raw, dict):
                nut_str = f"Calories: {nut_raw.get('Calories_kcal', 'N/A')} kcal | Protein: {nut_raw.get('Protein_g', 'N/A')}g | Carbs: {nut_raw.get('Carbs_g', 'N/A')}g | Fat: {nut_raw.get('Fat_g', 'N/A')}g | Fiber: {nut_raw.get('Fiber_g', 'N/A')}g"
            
            # Parse Ingredients
            ing_raw = food.get('Ingredients') or []
            ing_list = []
            if isinstance(ing_raw, list):
                for ing in ing_raw:
                    if isinstance(ing, dict):
                        ing_id = ing.get('Ingredient_ID') or ing.get('name') or 'Unknown'
                        qty = ing.get('Quantity') or ''
                        unit = ing.get('Unit') or ''
                        ing_list.append(f"{ing_id} ({qty}{unit})")
                    else:
                        ing_list.append(str(ing))
            ing_display = ", ".join(ing_list) if ing_list else "None"
            
            data_table = [
                [Paragraph("<b>Diet Type:</b>", body_style), to_para(diet, body_style)],
                [Paragraph("<b>Nutritional Info:</b>", body_style), to_para(nut_str, body_style)],
                [Paragraph("<b>Supports:</b>", body_style), to_para(supports, body_style)],
                [Paragraph("<b>Ingredients:</b>", body_style), to_para(ing_display, body_style)],
                [Paragraph("<b>Preparation:</b>", body_style), to_para(prep, body_style)],
                [Paragraph("<b>Notes:</b>", body_style), to_para(notes, body_style)]
            ]
            
            t = Table(data_table, colWidths=[120, 420])
            t.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('BACKGROUND', (0,0), (-1,-1), NEUTRAL_LIGHT),
                ('TOPPADDING', (0,0), (-1,-1), 4),
                ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                ('LEFTPADDING', (0,0), (-1,-1), 8),
                ('RIGHTPADDING', (0,0), (-1,-1), 8),
                ('LINEBELOW', (0,0), (-1,-1), 0.5, BORDER_COLOR),
                ('BOX', (0,0), (-1,-1), 1, PRIMARY_COLOR),
            ]))
            
            food_elements.append(t)
            food_elements.append(Spacer(1, 12))
            story.append(KeepTogether(food_elements))

    elif file_type == 'ingredients':
        # Ingredients table format works better since there are many ingredients
        # and they contain standard nutritional columns
        headers = ["ID", "Name", "Group", "Macros (per 100g)", "Allergens / Cautions"]
        table_data = [[Paragraph(h, table_header_style) for h in headers]]
        
        for ing in items:
            ing_id = ing.get('ID') or ing.get('id') or 'N/A'
            name = ing.get('Name') or ing.get('name') or 'N/A'
            group = ing.get('grup') or ing.get('Category') or 'N/A'
            
            mac = ing.get('Macros') or {}
            mac_str = ""
            if isinstance(mac, dict):
                mac_str = f"Cal: {mac.get('Calories_kcal', 0)} kcal\nP: {mac.get('Protein_g', 0)}g | C: {mac.get('Carbs_g', 0)}g\nF: {mac.get('Fat_g', 0)}g | Fib: {mac.get('Fiber_g', 0)}g"
            
            allergens = ing.get('Allergens') or 'None'
            caution = ing.get('Caution') or ''
            warning_text = allergens
            if caution and caution != allergens:
                warning_text += f"\nCaution: {caution}"
            
            row = [
                to_para(ing_id, table_cell_style),
                to_para(name, table_cell_style),
                to_para(group, table_cell_style),
                to_para(mac_str, table_cell_style),
                to_para(warning_text, table_cell_style)
            ]
            table_data.append(row)
            
        t = Table(table_data, colWidths=[65, 110, 115, 110, 140])
        t.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BACKGROUND', (0,0), (-1,0), PRIMARY_COLOR),
            ('BOTTOMPADDING', (0,0), (-1,0), 6),
            ('TOPPADDING', (0,0), (-1,0), 6),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, NEUTRAL_LIGHT]),
            ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
            ('TOPPADDING', (0,1), (-1,-1), 6),
            ('BOTTOMPADDING', (0,1), (-1,-1), 6),
        ]))
        story.append(t)

    else:
        # Generic JSON table
        all_keys = set()
        for item in items[:100]:  # sample keys
            if isinstance(item, dict):
                all_keys.update(item.keys())
        all_keys = sorted(list(all_keys))
        if not all_keys:
            story.append(to_para(items, body_style))
        else:
            headers = [str(k).title() for k in all_keys]
            table_data = [[Paragraph(xml_escape(h), table_header_style) for h in headers]]
            
            # Limit to 500 rows for extremely massive generic files to avoid PDF memory issues
            for item in items[:500]:
                if isinstance(item, dict):
                    row = []
                    for k in all_keys:
                        val = item.get(k, "")
                        row.append(to_para(val, table_cell_style))
                    table_data.append(row)
            
            # Calculate column widths evenly
            col_width = 540 / len(all_keys)
            t = Table(table_data, colWidths=[col_width] * len(all_keys))
            t.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('BACKGROUND', (0,0), (-1,0), PRIMARY_COLOR),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, NEUTRAL_LIGHT]),
                ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
                ('TOPPADDING', (0,0), (-1,-1), 5),
                ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ]))
            story.append(t)

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated: {dest_path}")


def main():
    src_root = os.path.join(os.path.dirname(__file__), "Data new")
    dest_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Data New"))
    
    os.makedirs(dest_root, exist_ok=True)
    
    for root, dirs, files in os.walk(src_root):
        rel_path = os.path.relpath(root, src_root)
        if rel_path == ".":
            current_dest_dir = dest_root
        else:
            current_dest_dir = os.path.join(dest_root, rel_path)
            os.makedirs(current_dest_dir, exist_ok=True)
            
        for file in files:
            if not file.endswith('.json'):
                continue
                
            src_file_path = os.path.join(root, file)
            dest_file_path = os.path.join(current_dest_dir, file.replace('.json', '.pdf'))
            
            file_lower = file.lower()
            
            if 'meal' in file_lower:
                file_type = 'meals'
            elif 'food' in file_lower:
                file_type = 'foods'
            elif 'ingredient' in file_lower:
                file_type = 'ingredients'
            else:
                file_type = 'generic'
                
            build_pdf_for_file(src_file_path, dest_file_path, file_type)


if __name__ == '__main__':
    main()
