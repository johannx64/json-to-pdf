import json
from xml.etree import ElementTree as ET
from pylibdmtx.pylibdmtx import encode as dmtx_encode
from PIL import Image
import svgwrite
from reportlab.graphics import renderPDF
from reportlab.pdfgen import canvas
from svglib.svglib import svg2rlg
import base64
import requests
import barcode
from barcode.writer import ImageWriter
from io import BytesIO

def read_json(json_path):
    with open(json_path, 'r') as file:
        data = json.load(file)
    return data

def load_svg_template(template_path):
    tree = ET.parse(template_path)
    root = tree.getroot()
    return tree, root

def replace_text_in_svg(root, variables):
    for group in root.iter('{http://www.w3.org/2000/svg}g'):
        group_id = group.get('id')
        if group_id and group_id in variables:
            for text_elem in group.findall('{http://www.w3.org/2000/svg}text'):
                text_elem.text = str(variables[group_id])
        for key, value in variables.items():
            if key.startswith("image_") and isinstance(value, str):
                image_url = value
                image_data = download_image_as_base64(image_url)
                insert_image_as_base64(root, group_id, image_data)

def download_image_as_base64(url):
    response = requests.get(url)
    image_data = base64.b64encode(response.content).decode('utf-8')
    return f'data:image/png;base64,{image_data}'

def insert_image_as_base64(parent, group_id, image_data):
    image_elem = ET.Element('{http://www.w3.org/2000/svg}image')
    image_elem.set('id', group_id)
    image_elem.set('width', "100")  # Adjust as needed
    image_elem.set('height', "100")  # Adjust as needed
    image_elem.set('{http://www.w3.org/1999/xlink}href', image_data)
    parent.append(image_elem)

def generate_data_matrix_svg(data):
    encoded = dmtx_encode(data.encode('utf-8'))
    image = Image.frombytes('RGB', (encoded.width, encoded.height), encoded.pixels)
    dwg = svgwrite.Drawing(size=(image.width, image.height))
    pixel_size = 1

    for y in range(image.height):
        for x in range(image.width):
            r, g, b = image.getpixel((x, y))
            if r == 0 and g == 0 and b == 0:
                dwg.add(dwg.rect(insert=(x * pixel_size, y * pixel_size), size=(pixel_size, pixel_size), fill='black'))

    return dwg.tostring()

def generate_barcode_png(barcode_data):
    # Generate barcode PNG
    png_buffer = BytesIO()
    barcode.generate('code128', barcode_data, writer=ImageWriter(), output=png_buffer, writer_options={'write_text': False})
    png_buffer.seek(0)  # Reset buffer position
    return png_buffer.getvalue()

def insert_svg_element_with_transform(parent, svg_content, width, height, transform):
    svg_element = ET.fromstring(svg_content)
    group = ET.Element('{http://www.w3.org/2000/svg}g')
    group.set('transform', transform)
    group.set('width', width)
    group.set('height', height)
    for element in svg_element:
        group.append(element)
    parent.append(group)

def insert_png_with_transform(parent, png_data, width, height, transform):
    # Insert PNG image into SVG
    png_data_encoded = base64.b64encode(png_data).decode('utf-8')
    image_elem = ET.Element('{http://www.w3.org/2000/svg}image')
    image_elem.set('width', str(width))
    image_elem.set('height', str(height))
    image_elem.set('transform', transform)
    image_elem.set('{http://www.w3.org/1999/xlink}href', f'data:image/png;base64,{png_data_encoded}')
    parent.append(image_elem)

def convert_svg_to_pdf(svg_tree, pdf_file_path):
    temp_svg_path = "temp_output.svg"
    svg_tree.write(temp_svg_path)
    drawing = svg2rlg(temp_svg_path)
    
    # Create a new canvas with dimensions 2 inches by 2 inches (144 points = 2 inches)
    c = canvas.Canvas(pdf_file_path, pagesize=(144, 144))
    
    # Get the dimensions of the drawing
    width, height = drawing.width, drawing.height
    
    # Draw the content at the top-left corner
    renderPDF.draw(drawing, c, 0, 0)
    
    c.showPage()
    c.save()

# Load the JSON data
json_path = "assets/clean_template.json"
data = read_json(json_path)

# Load the SVG template
template_path = data["template_path"]
svg_tree, svg_root = load_svg_template(template_path)

# Replace text placeholders in the SVG
replace_text_in_svg(svg_root, data["variables"])
replace_text_in_svg(svg_root, data["variables"]["item"])

# Generate the Data Matrix SVG from orderId
order_id = str(data["variables"]["item"]["orderItemId"])
data_matrix_svg = generate_data_matrix_svg(order_id)

# Generate the barcode PNG from barcodeData
barcode_data = str(data["variables"]["orderId"])
barcode_png = generate_barcode_png(barcode_data)

# Find the image tag with the datamatrix ID and replace its content
for parent in svg_root.findall(".//{http://www.w3.org/2000/svg}g"):
    for img_elem in parent.findall("{http://www.w3.org/2000/svg}image"):
        if img_elem.get("id") == "datamatrix":
            transform = img_elem.get("transform")
            width = img_elem.get("width")
            height = img_elem.get("height")
            parent.remove(img_elem)
            insert_svg_element_with_transform(parent, data_matrix_svg, width, height, transform)
        elif img_elem.get("id") == "barcode":
            transform = img_elem.get("transform")
            width = img_elem.get("width")
            height = img_elem.get("height")
            parent.remove(img_elem)
            insert_png_with_transform(parent, barcode_png, width, height, transform)

# Replace matrixcode attributes
matrixcode_attributes = data["variables"]["matrixcode"]["attributes"]
for key, value in matrixcode_attributes.items():
    svg_root.set(key, str(value))

# Convert the final SVG to PDF
pdf_file_path = "assets/2x2_QC_template_updated.pdf"
convert_svg_to_pdf(svg_tree, pdf_file_path)
