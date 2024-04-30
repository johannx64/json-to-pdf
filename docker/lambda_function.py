import os
import boto3
import json
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.colors import black
from reportlab.lib.utils import ImageReader
from PIL import Image
import qrcode
import barcode
from barcode.writer import ImageWriter

s3 = boto3.client('s3')

def handler(event, context):
    try:
        items = event.get('items')
        order_id = event.get('orderId')

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []

        for i, item in enumerate(items):
            paragraph_style = getSampleStyleSheet()['BodyText']
            elements.append(Paragraph(f"Order Item ID: {item.get('orderItemId')}", paragraph_style))

            for option in item.get('options'):
                elements.append(Paragraph(f"{option.get('name')}: {option.get('value')}", paragraph_style))

            qr_img = generate_qr_code(order_id, 145, 145)
            elements.append(qr_img)

            barcode_img = generate_barcode(item.get('orderItemId'), 'code128', 245, 45)
            elements.append(barcode_img)

        doc.build(elements)

        # Replace 'printables-mfg-rep/item-qc-barcode-sticker' with your actual bucket name
        bucket_name = 'printables-mfg-rep'
        folder_name = 'item-qc-barcode-sticker'
        key = f"{folder_name}/{order_id}.pdf"

        # Initialize the S3 client
        s3_client = boto3.client('s3')

        # Upload the file object to S3
        s3_client.upload_fileobj(buffer, bucket_name, key)

        # Construct the output dictionary with the S3 URL
        output = {
            'status': 'success',
            'url': f"https://{bucket_name}.s3.amazonaws.com/{key}"
        }

        return output

    except Exception as e:
        output = {
            'status': 'error',
            'url': '',
            'error': str(e)
        }
        return output

def generate_qr_code(data, width, height):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img = img.resize((width, height), Image.ANTIALIAS)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return ImageReader(buffer)

def generate_barcode(data, code_type, width, height):
    barcode_writer = ImageWriter()
    barcode_img = barcode.get_barcode_class(code_type)(data, barcode_writer)
    barcode_img = barcode_img.resize((width, height), barcode.NEAREST)
    buffer = BytesIO()
    barcode_img.save(buffer, format="PNG")
    buffer.seek(0)
    return ImageReader(buffer)