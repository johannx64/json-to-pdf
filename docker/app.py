#!/usr/bin/env python3
import sys
import json
import os
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
import boto3
import re

def download_from_s3(s3_path, local_path):
    s3 = boto3.client('s3')
    bucket_name, key = s3_path.replace("s3://", "").split("/", 1)
    s3.download_file(bucket_name, key, local_path)

def load_svg_template(s3_path):
    local_path = "/tmp/template.svg"
    download_from_s3(s3_path, local_path)
    tree = ET.parse(local_path)
    root = tree.getroot()
    return tree, root

def read_json(json_path):
    with open(json_path, 'r') as file:
        data = json.load(file)
    return data

def get_value_from_json_path(data, path):
    keys = path.split('.')
    for key in keys:
        # Handle array indices like 'options.0.name'
        if re.match(r'^\d+$', key):  # if key is an integer, treat it as an array index
            key = int(key)
        if isinstance(data, list):  # If data is a list, we access by index
            data = data[key]
        else:  # If data is a dict, we access by key
            data = data.get(key)
        if data is None:
            return None
    return data

def replace_text_in_svg(root, variables):
    # This function will now support deep access like 'variables.items.options.0.name'
    for group in root.iter('{http://www.w3.org/2000/svg}text'):
        group_id = group.get('id')
        if group_id:
            # Handle deep nested IDs in the format 'variables.items.orderItemId' or 'variables.items.options.0.name'
            value = get_value_from_json_path(variables, group_id)
            if value:
                for text_elem in group.findall('{http://www.w3.org/2000/svg}tspan'):
                    text_elem.text = str(value)

def download_image_as_base64(url):
    response = requests.get(url)
    image_data = base64.b64encode(response.content).decode('utf-8')
    return f'data:image/png;base64,{image_data}'

def insert_image_as_base64(parent, group_id, image_data):
    for image_elem in parent.findall('{http://www.w3.org/2000/svg}image'):
        if image_elem.get('id') == group_id:
            image_elem.set('{http://www.w3.org/1999/xlink}href', image_data)
            return

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

def insert_svg_element_with_transform(parent, svg_content, width, height, transform, scale=1.0):
    svg_element = ET.fromstring(svg_content)
    group = ET.Element('{http://www.w3.org/2000/svg}g')
    
    # Ensure transform includes scaling
    if transform:
        transform += f" scale({scale})"
    else:
        transform = f"scale({scale})"
    
    group.set('transform', transform)
    
    # In SVG, width and height for groups (`g` elements) aren't directly used
    # Scaling should be done via the transform attribute
    
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
    temp_svg_path = "/tmp/temp_output.svg"
    svg_tree.write(temp_svg_path)
    drawing = svg2rlg(temp_svg_path)
    
    # Get the dimensions of the drawing from the SVG
    width, height = drawing.width, drawing.height
    
    # Create a new canvas with dimensions matching the SVG
    c = canvas.Canvas(pdf_file_path, pagesize=(width, height))
    
    # Draw the content at the bottom-left corner
    renderPDF.draw(drawing, c, 0, 0)
    
    c.showPage()
    c.save()

def replace_image(svg_root, data_image, target, item_id, image_url=None, obj=None):
    if obj is None:
        raise ValueError("Object 'obj' must be provided.")
    
    scale = obj.get("attributes", {}).get("scale", 1.0)
    offset = obj.get("attributes", {}).get("offset", {})
    offset_right = offset.get("right", 0)
    offset_down = offset.get("down", 0)
    offset_top = offset.get("top", 0)
    offset_bottom = offset.get("bottom", 0)

    for parent in svg_root.findall(".//{http://www.w3.org/2000/svg}g"):
        for img_elem in parent.findall("{http://www.w3.org/2000/svg}image"):
            img_id = img_elem.get("id")
            if img_id == item_id:
                transform = img_elem.get("transform")
                width = img_elem.get("width")
                height = img_elem.get("height")
                parent.remove(img_elem)
                
                # Adjust width and height based on scale
                adjusted_width = str(float(width) * scale)
                adjusted_height = str(float(height) * scale)

                # Adjust transform based on offset
                if transform:
                    transform += f" translate({offset_right}, {offset_down})"
                else:
                    transform = f"translate({offset_right}, {offset_down})"
                
                # Apply adjustments and insert the new image
                if target == "datamatrix":
                    insert_svg_element_with_transform(parent, data_image, adjusted_width, adjusted_height, transform, scale)
                elif target == "barcode":
                    insert_png_with_transform(parent, data_image, adjusted_width, adjusted_height, transform)
                elif target == "image":
                    if image_url.startswith("s3://"):
                        local_image_path = "/tmp/temp_image.png"
                        download_from_s3(image_url, local_image_path)
                        with open(local_image_path, "rb") as image_file:
                            png_data = image_file.read()
                    else:
                        response = requests.get(image_url)
                        png_data = response.content
                    
                    insert_png_with_transform(parent, png_data, adjusted_width, adjusted_height, transform)

def find_svg_element(data, svg_root, barcode_list, datamatrix_list, images_list):
    # Find the image tag with the datamatrix ID and replace its content

    #generating Barcode images and replacing into the SVG template
    for barcode in barcode_list:
        # Resolve the actual data value from the JSON path in 'data'
        barcode_data = get_value_from_json_path(data, barcode["data"])
        if barcode_data:  # Ensure the resolved data is valid
            barcode_png = generate_barcode_png(str(barcode_data))
            replace_image(svg_root, barcode_png, "barcode", str(barcode["id"]), obj=barcode)

    #generating Data Matrix images and replacing into the SVG template
    for matrix in datamatrix_list:
        # Resolve the actual data value from the JSON path in 'data'
        matrix_data = get_value_from_json_path(data, matrix["data"])
        if matrix_data:  # Ensure the resolved data is valid
            matrix_svg = generate_data_matrix_svg(str(matrix_data))
            replace_image(svg_root, matrix_svg, "datamatrix", str(matrix["id"]), obj=matrix)


    #generating Image images and replacing into the SVG template
    for images in images_list:
        replace_image(svg_root, matrix_svg, "image", str(images["id"]), image_url=images["source"], obj=images)

def lambda_handler(event, context):
    # Load the JSON data
    json_path = "/tmp/clean_template.json"
    with open(json_path, 'w') as f:
        json.dump(event, f)
    data = read_json(json_path)

    # Load the SVG template
    template_path = data["template_path"]
    svg_tree, svg_root = load_svg_template(template_path)
    

    # Replace text placeholders in the SVG
    replace_text_in_svg(svg_root, data["variables"])
    #replace_text_in_svg(svg_root, data["variables"]["item"])
    
    """
    # Generate the Data Matrix SVG from orderId
    order_id = str(data["variables"]["item"]["orderItemId"])
    data_matrix_svg = generate_data_matrix_svg(order_id)
    
    # Generate the barcode PNG from barcodeData
    barcode_data = str(data["variables"]["orderId"])
    barcode_png = generate_barcode_png(barcode_data)
    """

    #Barcode image list
    barcode_list = data["barcodes"]
    #Barcode image list
    datamatrix_list = data["matrixcodes"]
    #Barcode image list
    images_list = data["images"]
    #Multiple barcodes/datamatrix images
    find_svg_element(data, svg_root, barcode_list, datamatrix_list, images_list)

    """
    # Replace matrixcode attributes
    matrixcode_attributes = data["variables"]["matrixcode"]["attributes"]
    for key, value in matrixcode_attributes.items():
        svg_root.set(key, str(value))
    """

    # Convert the final SVG to PDF using orderItemId as the filename
    order_item_id = str(data["variables"]["item"]["orderItemId"])
    pdf_file_path = f"/tmp/{order_item_id}.pdf"
    convert_svg_to_pdf(svg_tree, pdf_file_path)

    # Upload the PDF to S3 using the bucket name from the JSON data
    s3 = boto3.client('s3')
    s3_bucket_name = data["variables"]["bucket"]
    s3_key = data["output_path"]
    s3.upload_file(pdf_file_path, s3_bucket_name, f'{s3_key}/{order_item_id}.pdf')

    return {
        'statusCode': 200,
        'body': json.dumps(f'PDF created and uploaded successfully as {order_item_id}.pdf.')
    }

if __name__ == "__main__":
    # When the script is executed directly, it expects a JSON event string
    # from the command line arguments.
    print("JSON TO PDF START ###")
    event_str = sys.argv[1]
    event = json.loads(event_str)
    print("Recieved event:", event)

    response = lambda_handler(event, None)  # Context is set to None for simplicity
    print(response)
